import json
import os
import sys
import time
from collections.abc import Iterable

import requests


"""
Shared GitHub API helpers used by multiple scripts.

Goals
- Centralize env handling (repo, token)
- Provide simple HTTP helpers with retries and consistent headers
- Offer common GitHub operations with minimal, readable interfaces

Token env precedence
- GITHUB_TOKEN
- GH_TOKEN
- GITHUB_BEARER_TOKEN

All functions prefer explicit parameters, but will fall back to env where
appropriate for convenience. Functions exit with code 1 on unrecoverable API
errors to maintain existing behavior in calling scripts.
"""

GITHUB_API: str = "https://api.github.com"
API_VERSION: str = "2022-11-28"
DEFAULT_TIMEOUT_SECONDS: int = 30


def get_repo_owner_and_name() -> tuple[str, str]:
    """Read `GITHUB_REPOSITORY` ("owner/repo") and return `(owner, repo)`.

    Exits the process if env is missing or malformed to match existing scripts.
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo or "/" not in repo:
        print("GITHUB_REPOSITORY is not set", file=sys.stderr)
        sys.exit(1)
    owner, name = repo.split("/", 1)
    return owner, name


def get_repo_owner_and_name_or_default(
    default_owner: str = "your-org", default_repo: str = "your-repo"
) -> tuple[str, str]:
    """Best-effort repo resolution with safe defaults for local usage."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo and "/" in repo:
        owner, name = repo.split("/", 1)
        return owner, name
    return default_owner, default_repo


def get_bearer_token() -> str:
    """Return a GitHub bearer token from env using a permissive precedence.

    Precedence: GITHUB_TOKEN, GH_TOKEN, GITHUB_BEARER_TOKEN
    Exits the process if no token is available.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_BEARER_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not available", file=sys.stderr)
        sys.exit(1)
    return token


def _default_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }


def gh_get(
    url: str,
    token: str | None = None,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 2,
    backoff_seconds: float = 1.5,
) -> requests.Response:
    """GET with uniform headers and simple retry on transient errors."""
    auth_token = token or get_bearer_token()
    headers = _default_headers(auth_token)
    attempt = 0
    while True:
        resp = requests.get(url, headers=headers, timeout=timeout_seconds)
        if resp.status_code in (502, 503, 504):
            if attempt < retries:
                time.sleep(backoff_seconds * (2**attempt))
                attempt += 1
                continue
        # Simple handling for secondary rate limiting
        if resp.status_code == 403 and "Retry-After" in resp.headers and attempt < retries:
            try:
                retry_after = float(resp.headers.get("Retry-After", "1"))
            except ValueError:
                retry_after = backoff_seconds
            time.sleep(retry_after)
            attempt += 1
            continue
        return resp


def gh_post(
    url: str,
    body: dict,
    token: str | None = None,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 2,
    backoff_seconds: float = 1.5,
) -> requests.Response:
    """POST with uniform headers and simple retry on transient errors."""
    auth_token = token or get_bearer_token()
    headers = {**_default_headers(auth_token), "Content-Type": "application/json"}
    attempt = 0
    data = json.dumps(body)
    while True:
        resp = requests.post(url, headers=headers, data=data, timeout=timeout_seconds)
        if resp.status_code in (502, 503, 504):
            if attempt < retries:
                time.sleep(backoff_seconds * (2**attempt))
                attempt += 1
                continue
        if resp.status_code == 403 and "Retry-After" in resp.headers and attempt < retries:
            try:
                retry_after = float(resp.headers.get("Retry-After", "1"))
            except ValueError:
                retry_after = backoff_seconds
            time.sleep(retry_after)
            attempt += 1
            continue
        return resp


def _extract_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    # Parse very simply: look for rel="next"
    parts = [p.strip() for p in link_header.split(",")]
    for p in parts:
        if 'rel="next"' in p:
            # Format: <url>; rel="next"
            start = p.find("<")
            end = p.find(">", start + 1)
            if start != -1 and end != -1:
                return p[start + 1 : end]
    return None


def gh_get_paginated(url: str, token: str | None = None) -> list[dict]:
    """Return all pages for a list endpoint using Link headers."""
    results: list[dict] = []
    next_url: str | None = url
    while next_url:
        resp = gh_get(next_url, token)
        if resp.status_code != 200:
            print(f"Error fetching {next_url}: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        page_items = resp.json()
        if isinstance(page_items, list):
            results.extend(page_items)
        else:
            # Some endpoints can return non-list; surface as-is
            return page_items  # type: ignore[return-value]
        next_url = _extract_next_link(resp.headers.get("Link"))
    return results


def get_pull_request(owner: str, repo: str, number: int, token: str | None = None) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}"
    resp = gh_get(url, token)
    if resp.status_code != 200:
        print(f"Error fetching PR: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def list_pull_request_reviews(owner: str, repo: str, number: int, token: str | None = None) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}/reviews"
    return gh_get_paginated(url, token)


def check_collaborator(owner: str, repo: str, username: str, token: str | None = None) -> bool:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/collaborators/{username}"
    resp = gh_get(url, token)
    if resp.status_code == 204:
        return True
    if resp.status_code == 404:
        return False
    print(f"Warn: collaborator check for {username} -> {resp.status_code} {resp.text}")
    return False


def list_issue_comments(owner: str, repo: str, issue_number: int, token: str | None = None) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments"
    return gh_get_paginated(url, token)


def comment_once(
    owner: str,
    repo: str,
    issue_number: int,
    body_text: str,
    dedupe_hint: str,
    token: str | None = None,
) -> None:
    comments = list_issue_comments(owner, repo, issue_number, token)
    if any(dedupe_hint in (c.get("body") or "") for c in comments):
        return
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments"
    resp = gh_post(url, {"body": body_text}, token)
    if resp.status_code not in (200, 201):
        print(f"Warn: failed to post comment: {resp.status_code} {resp.text}")


def request_reviewers(
    owner: str,
    repo: str,
    pr_number: int,
    reviewers: Iterable[str],
    token: str | None = None,
) -> None:
    reviewers_list = [r for r in reviewers if r]
    if not reviewers_list:
        return
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers"
    resp = gh_post(url, {"reviewers": reviewers_list}, token)
    if resp.status_code not in (200, 201):
        print(f"Warn: failed to request reviewers: {resp.status_code} {resp.text}")
