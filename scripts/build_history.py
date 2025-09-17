import os
import re
import yaml
import pandas as pd
from datetime import datetime, timezone
import tempfile
from typing import Optional

from github_utils import get_repo_owner_and_name_or_default, list_issue_comments

# Pre-compiled regex for efficiency
# Matches " #123" in the bot's comment
PR_NUM_RE = re.compile(r"#(\d+)")
# Extracts the issue number from a filename like "2024-01-01-123.yml"
ISSUE_NUM_RE = re.compile(r"-(\d+)\.yml$")


def find_pr_number_from_comments(owner: str, repo: str, issue_number: int) -> int:
    """
    Find the PR number from the comments of an issue.
    The bot posts a comment with a link to the PR.
    """
    try:
        comments = list_issue_comments(owner, repo, issue_number)
        for comment in comments:
            # The bot's username is "github-actions[bot]"
            if comment["user"]["login"] == "github-actions[bot]":
                match = PR_NUM_RE.search(comment["body"])
                if match:
                    return int(match.group(1))
    except Exception:
        # Gracefully handle GitHub API errors (missing token, rate limits, etc.)
        pass
    return 0


def load_matches_from_directory(directory: str, match_type: str):
    """Load matches from a specific directory (singles-matches or doubles-matches)"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    directory = os.path.join(repo_root, directory)

    if not os.path.exists(directory):
        return []
    
    match_files = sorted(
        [f for f in os.listdir(directory) if f.endswith(".yml")], reverse=True
    )
    
    matches = []
    for match_file in match_files:
        match_path = os.path.join(directory, match_file)
        with open(match_path, 'r') as f:
            match_data = yaml.safe_load(f)

        issue_search = ISSUE_NUM_RE.search(match_file)
        if not issue_search:
            continue

        issue_number = int(issue_search.group(1))
        
        # Format score - handle both array format [6, 4] and object format
        sets_html = ""
        for s in match_data["sets"]:
            if isinstance(s, list) and len(s) == 2:
                # Array format: [6, 4]
                sets_html += f"<li>{s[0]}-{s[1]}</li>"
            elif isinstance(s, dict) and 'player1_games' in s and 'player2_games' in s:
                # Object format: {player1_games: 6, player2_games: 4}
                sets_html += f"<li>{s['player1_games']}-{s['player2_games']}</li>"
        score_html = f"<ul>{sets_html}</ul>"

        # Handle different match formats
        if match_type == "singles":
            # Singles: players: [player1, player2]
            if "players" in match_data and isinstance(match_data["players"], list):
                player1, player2 = match_data["players"][0], match_data["players"][1]
                player1_link = f'<a href="player_profile_{player1}.html">{player1}</a>'
                player2_link = f'<a href="player_profile_{player2}.html">{player2}</a>'
                players_display = f"{player1_link} vs {player2_link}"
            else:
                player1, player2 = match_data.get("player1", ""), match_data.get("player2", "")
                players_display = f"{player1} vs {player2}"
        else:
            # Doubles: team1: [p1, p2], team2: [p3, p4]
            if "team1" in match_data and "team2" in match_data:
                team1_links = ", ".join([f'<a href="player_profile_{p}.html">{p}</a>' for p in match_data["team1"]])
                team2_links = ", ".join([f'<a href="player_profile_{p}.html">{p}</a>' for p in match_data["team2"]])
                players_display = f"({team1_links}) vs ({team2_links})"
            else:
                players_display = "Unknown teams"

        matches.append({
            "date": match_data["date"],
            "players_display": players_display,
            "score": score_html,
            "issue_number": issue_number,
            "type": match_type.title()
        })
    
    return matches


def build_history_page(output_dir: Optional[str] = None):
    """
    Generates a static HTML page with both singles and doubles match history.

    If `output_dir` is provided, `history.html` is created there. Otherwise,
    a temporary directory is created.
    """
    owner, repo = get_repo_owner_and_name_or_default()

    # Load matches from both directories
    singles_matches = load_matches_from_directory("singles-matches", "singles")
    doubles_matches = load_matches_from_directory("doubles-matches", "doubles")
    
    # Combine and sort all matches by date (most recent first)
    all_matches = singles_matches + doubles_matches
    all_matches.sort(key=lambda x: x["date"], reverse=True)

    # Generate the HTML table rows
    table_rows = ""
    for match in all_matches:
        # Get PR number if needed
        pr_number = 0
        if os.environ.get("GITHUB_TOKEN"):
            pr_number = find_pr_number_from_comments(owner, repo, match["issue_number"])
        
        pr_link = f'<a href="https://github.com/{owner}/{repo}/pull/{pr_number}">PR</a>' if pr_number else "N/A"
        issue_link = f'<a href="https://github.com/{owner}/{repo}/issues/{match["issue_number"]}">Issue</a>'
        
        # Add type badge
        type_badge = f'<span class="badge bg-{"primary" if match["type"] == "Singles" else "success"}">{match["type"]}</span>'

        table_rows += f"""
        <tr>
            <td>{match["date"]}</td>
            <td>{type_badge}</td>
            <td>{match["players_display"]}</td>
            <td>{match["score"]}</td>
            <td>{issue_link}</td>
            <td>{pr_link}</td>
        </tr>
        """

    html_table = f"""
    <div class="table-responsive">
        <table class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Players/Teams</th>
                    <th>Score</th>
                    <th>Issue</th>
                    <th>PR</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    repo_url = f"https://github.com/{owner}/{repo}"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Match History</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ padding: 2rem; }}
            .container {{ max-width: 1000px; }}
            h1 {{ margin-bottom: 1.5rem; text-align: center; }}
            .footer {{ 
                margin-top: 2rem; 
                padding-top: 2rem;
                border-top: 1px solid #dee2e6;
                font-size: 0.9rem; 
                color: #6c757d; 
                text-align: center;
            }}
            ul {{ margin-bottom: 0; padding-left: 1.5rem; }}
            .table-responsive {{ 
                max-height: 600px; 
                overflow-y: auto; 
                border: 1px solid #dee2e6;
                border-radius: 0.375rem;
            }}
            .badge {{ font-size: 0.75em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎾 Match History</h1>
            {html_table}
            <div class="footer">
                <p>Last updated: {timestamp}</p>
                <p><a href="index.html">Back to Leaderboards</a> | <a href="{repo_url}">GitHub Repository</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    # If an output_dir is provided, use it; otherwise, create a temp dir
    if output_dir:
        # We are being called by another script; no need to return the dir
        output_file = os.path.join(output_dir, "history.html")
        with open(output_file, "w") as f:
            f.write(html_template)
        return None, output_file

    # Standalone execution for testing or other uses
    temp_dir = tempfile.mkdtemp(prefix="tennis_history_")
    output_file = os.path.join(temp_dir, "history.html")
    with open(output_file, "w") as f:
        f.write(html_template)
    return temp_dir, output_file


if __name__ == "__main__":
    temp_dir, _ = build_history_page()
    if temp_dir and os.environ.get("GITHUB_ACTIONS") == "true":
        with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
            f.write(f"history_temp_dir={temp_dir}")