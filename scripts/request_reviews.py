import os
import sys


from github_utils import (
    get_bearer_token,
    get_repo_owner_and_name,
    check_collaborator,
    comment_once,
    request_reviewers,
)


def main() -> None:
    token = get_bearer_token()
    owner, repo = get_repo_owner_and_name()

    pr_number_raw = os.environ.get("PR_NUMBER")
    player1 = os.environ.get("PLAYER_1")
    player2 = os.environ.get("PLAYER_2")
    player3 = os.environ.get("PLAYER_3")
    player4 = os.environ.get("PLAYER_4")

    if not pr_number_raw:
        print("PR_NUMBER is required", file=sys.stderr)
        sys.exit(1)

    pr_number = int(pr_number_raw)
    players = [p for p in [player1, player2, player3, player4] if p]

    collaborators: list[str] = []
    non_collaborators: list[str] = []
    for login in players:
        if check_collaborator(owner, repo, login, token):
            collaborators.append(login)
        else:
            non_collaborators.append(login)

    # Request reviews from collaborators only
    request_reviewers(owner, repo, pr_number, collaborators, token)

    # Comment guidance for non-collaborators
    if non_collaborators:
        guidance_hint = "cannot be requested as reviewers"
        guidance = (
            f"Heads up: {', '.join('@' + u for u in non_collaborators)} {guidance_hint} because they are not collaborators. "
            "Please add them as collaborators if you want them to provide Approve reviews on future PRs."
        )
        comment_once(owner, repo, pr_number, guidance, dedupe_hint=guidance_hint, token=token)


if __name__ == "__main__":
    main()
