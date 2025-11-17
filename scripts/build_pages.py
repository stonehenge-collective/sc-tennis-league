#!/usr/bin/env python3
import os
import tempfile
import pandas as pd
from datetime import datetime, timezone

from github_utils import get_repo_owner_and_name_or_default


"""
This page builder creates dual leaderboards from `temp-rankings/singles-ranking.csv`
and `temp-rankings/doubles-ranking.csv` for all aggregates (rating, set and game records).
"""


def load_ranking_data(file_path: str, columns: list[str]):
    """Load ranking data from CSV file with fallback to empty DataFrame"""
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        df = pd.DataFrame(columns=columns)

    # Ensure all required columns exist
    for col in columns:
        if col not in df.columns:
            df[col] = 0

    return df.sort_values(by="rating", ascending=False).reset_index(drop=True)


def generate_marquee_content():
    """Generate HTML for a marquee banner of recent Elo changes."""
    try:
        elo_changes_df = pd.read_csv("temp-rankings/elo_changes.csv")
        # Get the last 20 ELO changes
        recent_changes = elo_changes_df.tail(20)

        if recent_changes.empty:
            return "No recent ELO changes."

        parts = []
        for _, row in recent_changes.iterrows():
            player = row["player"]
            change = row["change"]

            if change > 0:
                arrow = f'<span style="color: green;">▲</span>'
                sign = "+"
            else:
                arrow = f'<span style="color: red;">▼</span>'
                sign = ""

            parts.append(f'{player} {arrow} {sign}{change:.1f}')

        return " • ".join(parts)

    except FileNotFoundError:
        return "🎾 No ball boys were harmed in the making of these statistics • Serving up fresh rankings daily! • Love means nothing in tennis, but these scores mean everything! • Deuce you believe these rankings? • Game, Set, Match... and GitHub Issues! 🎾"


def generate_singles_table(df: pd.DataFrame):
    """Generate HTML table for singles leaderboard"""
    df.index += 1
    df.index.name = "Rank"

    table_rows = ""
    for rank, row in df.iterrows():
        player = row["player"]
        player_link = f'<a href="player_profile_{player}.html">{player}</a>'
        games_record = f'{int(row.get("game_wins", 0))}-{int(row.get("game_losses", 0))}'
        sets_record = f'{int(row.get("set_wins", 0))}-{int(row.get("set_losses", 0))}'
        table_rows += f"""
        <tr>
            <td>{rank}</td>
            <td>{player_link}</td>
            <td>{int(row["rating"])}</td>
            <td>{sets_record}</td>
            <td>{games_record}</td>
        </tr>
        """

    return f"""
    <div class="leaderboard-container">
        <h2>🎾 Singles Leaderboard</h2>
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Player</th>
                        <th>Rating</th>
                        <th>Sets W-L</th>
                        <th>Games W-L</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    """


def generate_doubles_table(df: pd.DataFrame):
    """Generate HTML table for doubles leaderboard"""
    df.index += 1
    df.index.name = "Rank"

    table_rows = ""
    for rank, row in df.iterrows():
        team = row["team"]
        # Split team names for individual GitHub links
        players = team.split(", ")
        if len(players) == 2:
            team_links = f'<a href="player_profile_{players[0]}.html">{players[0]}</a>, <a href="player_profile_{players[1]}.html">{players[1]}</a>'
        else:
            team_links = team

        games_record = f'{int(row.get("game_wins", 0))}-{int(row.get("game_losses", 0))}'
        sets_record = f'{int(row.get("set_wins", 0))}-{int(row.get("set_losses", 0))}'
        table_rows += f"""
        <tr>
            <td>{rank}</td>
            <td>{team_links}</td>
            <td>{int(row["rating"])}</td>
            <td>{sets_record}</td>
            <td>{games_record}</td>
        </tr>
        """

    return f"""
    <div class="table-responsive">
        <table class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th>Rating</th>
                    <th>Sets W-L</th>
                    <th>Games W-L</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """

def generate_doubles_individual_table(df: pd.DataFrame):
    """Generate HTML table for doubles individual leaderboard"""
    df.index += 1
    df.index.name = "Rank"

    table_rows = ""
    for rank, row in df.iterrows():
        player = row["player"]
        player_link = f'<a href="player_profile_{player}.html">{player}</a>'
        games_record = f'{int(row.get("game_wins", 0))}-{int(row.get("game_losses", 0))}'
        sets_record = f'{int(row.get("set_wins", 0))}-{int(row.get("set_losses", 0))}'
        table_rows += f"""
        <tr>
            <td>{rank}</td>
            <td>{player_link}</td>
            <td>{int(row["rating"])}</td>
            <td>{sets_record}</td>
            <td>{games_record}</td>
        </tr>
        """

    return f"""
    <div class="table-responsive">
        <table class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Player</th>
                    <th>Rating</th>
                    <th>Sets W-L</th>
                    <th>Games W-L</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """


def build_site():
    from scripts.build_history import build_history_page
    from scripts.build_player_pages import build_player_pages

    # Create a single temporary directory for all pages
    temp_dir = tempfile.mkdtemp(prefix="tennis_site_")

    # --- Load ranking data ---
    singles_df = load_ranking_data(
        "temp-rankings/singles-ranking.csv",
        ["player", "rating", "set_wins", "set_losses", "game_wins", "game_losses"]
    )

    doubles_df = load_ranking_data(
        "temp-rankings/doubles-ranking.csv",
        ["team", "rating", "set_wins", "set_losses", "game_wins", "game_losses"]
    )

    doubles_individual_df = load_ranking_data(
        "temp-rankings/doubles-individual-ranking.csv",
        ["player", "rating", "set_wins", "set_losses", "game_wins", "game_losses"]
    )

    # --- Generate leaderboard tables ---
    singles_table = generate_singles_table(singles_df)
    doubles_team_table = generate_doubles_table(doubles_df)
    doubles_individual_table = generate_doubles_individual_table(doubles_individual_df)

    doubles_tab_content = f"""
    <div class="leaderboard-container">
        <h2>👥 Doubles Leaderboard</h2>
        <ul class="nav nav-tabs" id="doublesTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="teams-tab" data-bs-toggle="tab" data-bs-target="#teams" type="button" role="tab" aria-controls="teams" aria-selected="false">Teams</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="individuals-tab" data-bs-toggle="tab" data-bs-target="#individuals" type="button" role="tab" aria-controls="individuals" aria-selected="true">Individuals</button>
            </li>
        </ul>
        <div class="tab-content" id="doublesTabContent">
            <div class="tab-pane fade" id="teams" role="tabpanel" aria-labelledby="teams-tab">
                {doubles_team_table}
            </div>
            <div class="tab-pane fade show active" id="individuals" role="tabpanel" aria-labelledby="individuals-tab">
                {doubles_individual_table}
            </div>
        </div>
    </div>
    """

    # --- Build main leaderboard page (index.html) ---
    owner, repo = get_repo_owner_and_name_or_default()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    repo_url = f"https://github.com/{owner}/{repo}"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tennis Leaderboards</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <style>
            body {{ padding: 2rem; }}
            .container {{ max-width: 1200px; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .leaderboards-container {{
                display: flex;
                gap: 2rem;
                margin-bottom: 2rem;
            }}
            .leaderboard-container {{
                flex: 1;
                min-height: 400px;
            }}
            .table-responsive {{
                max-height: 500px;
                overflow-y: auto;
                border: 1px solid #dee2e6;
                border-radius: 0 0 0.375rem 0.375rem;
                border-top: none;
            }}
            .footer {{
                margin-top: 2rem;
                padding-top: 2rem;
                border-top: 1px solid #dee2e6;
                font-size: 0.9rem;
                color: #6c757d;
                text-align: center;
            }}
            h2 {{
                text-align: center;
                margin-bottom: 1rem;
                color: #495057;
            }}
            .nav-tabs .nav-link {{
                color: #495057;
            }}
            .nav-tabs .nav-link.active {{
                color: #000;
                background-color: #fff;
                border-color: #dee2e6 #dee2e6 #fff;
            }}
            @media (max-width: 768px) {{
                .leaderboards-container {{
                    flex-direction: column;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏆 Tennis Leaderboards</h1>

            <marquee behavior="scroll" direction="left" bgcolor="#f8f9fa" style="padding: 10px; margin-bottom: 2rem; border: 1px solid #dee2e6; border-radius: 0.375rem; font-weight: 500;">
                {generate_marquee_content()}
            </marquee>

            <div class="leaderboards-container">
                {singles_table}
                {doubles_tab_content}
            </div>

            <div class="footer">
                <p>Last updated: {timestamp}</p>
                <p><a href="history.html">Match History</a> | <a href="{repo_url}">GitHub Repository</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    index_output_file = os.path.join(temp_dir, "index.html")
    with open(index_output_file, "w") as f:
        f.write(html_template)

    # --- Build Match History Page (history.html) ---
    build_history_page(output_dir=temp_dir)

    # --- Build Player Pages ---
    build_player_pages(output_dir=temp_dir)

    return temp_dir, index_output_file


if __name__ == "__main__":
    temp_dir, _ = build_site()
    if temp_dir and os.environ.get("GITHUB_ACTIONS") == "true":
        with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
            f.write(f"temp_dir={temp_dir}")
