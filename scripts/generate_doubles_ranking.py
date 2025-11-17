import glob
import sys
import yaml
import pandas as pd
from scripts.elo_utils import update_doubles_elo_ratings, normalize_team

# --- Team-based data ---
team_ratings = {}
team_stats = {}

# --- Individual-based data ---
individual_ratings = {}
individual_stats = {}


def _ensure_team_stats(team: str) -> None:
    if team not in team_stats:
        team_stats[team] = {
            "set_wins": 0,
            "set_losses": 0,
            "game_wins": 0,
            "game_losses": 0,
        }


def _ensure_player_stats(player: str) -> None:
    if player not in individual_stats:
        individual_stats[player] = {
            "set_wins": 0,
            "set_losses": 0,
            "game_wins": 0,
            "game_losses": 0,
        }


def apply_match(match):
    """Update ratings and aggregates from a single doubles match file."""
    team1_players = match["team1"]
    team2_players = match["team2"]

    # Normalize team names for team-based stats
    team1_key = normalize_team(team1_players)
    team2_key = normalize_team(team2_players)
    _ensure_team_stats(team1_key)
    _ensure_team_stats(team2_key)

    # Ensure individual player stats entries exist
    for p in team1_players + team2_players:
        _ensure_player_stats(p)

    # --- Process sets ---
    sets = match.get("sets") or []
    for s in sets:
        try:
            t1_games = int(s[0])
            t2_games = int(s[1])
        except (ValueError, TypeError, IndexError):
            continue

        if t1_games == t2_games:
            continue

        # --- Aggregate stats (both team and individual) ---
        set_winner_players = team1_players if t1_games > t2_games else team2_players
        set_loser_players = team2_players if t1_games > t2_games else team1_players
        set_winner_key = normalize_team(set_winner_players)
        set_loser_key = normalize_team(set_loser_players)

        # Team stats
        team_stats[set_winner_key]["set_wins"] += 1
        team_stats[set_loser_key]["set_losses"] += 1
        team_stats[team1_key]["game_wins"] += t1_games
        team_stats[team1_key]["game_losses"] += t2_games
        team_stats[team2_key]["game_wins"] += t2_games
        team_stats[team2_key]["game_losses"] += t1_games

        # Individual stats
        for p in team1_players:
            individual_stats[p]["game_wins"] += t1_games
            individual_stats[p]["game_losses"] += t2_games
        for p in team2_players:
            individual_stats[p]["game_wins"] += t2_games
            individual_stats[p]["game_losses"] += t1_games

        if t1_games > t2_games:
            for p in team1_players:
                individual_stats[p]["set_wins"] += 1
            for p in team2_players:
                individual_stats[p]["set_losses"] += 1
        else:
            for p in team2_players:
                individual_stats[p]["set_wins"] += 1
            for p in team1_players:
                individual_stats[p]["set_losses"] += 1


        # --- ELO Updates ---
        new_rW_team, new_rL_team, new_r_w1, new_r_w2, new_r_l1, new_r_l2 = update_doubles_elo_ratings(team_ratings, individual_ratings, set_winner_players, set_loser_players)

        team_ratings[set_winner_key] = new_rW_team
        team_ratings[set_loser_key] = new_rL_team

        individual_ratings[set_winner_players[0]] = new_r_w1
        individual_ratings[set_winner_players[1]] = new_r_w2
        individual_ratings[set_loser_players[0]] = new_r_l1
        individual_ratings[set_loser_players[1]] = new_r_l2


def main():
    """Main function to calculate and print doubles rankings."""
    # Process doubles matches
    for fn in sorted(glob.glob("doubles-matches/*.yml")):
        with open(fn) as f:
            try:
                match_data = yaml.safe_load(f)
                if match_data and "team1" in match_data and "team2" in match_data:
                    apply_match(match_data)
            except yaml.YAMLError as e:
                print(f"Error reading {fn}: {e}", file=sys.stderr)

    # --- Generate and save team rankings ---
    team_data = []
    for team, rating in sorted(team_ratings.items(), key=lambda item: -item[1]):
        stats = team_stats.get(team, {"set_wins": 0, "set_losses": 0, "game_wins": 0, "game_losses": 0})
        team_data.append({
            "team": team, "rating": round(rating, 1),
            "set_wins": stats["set_wins"], "set_losses": stats["set_losses"],
            "game_wins": stats["game_wins"], "game_losses": stats["game_losses"]
        })

    team_df = pd.DataFrame(team_data)
    if not team_df.empty:
        team_df = team_df.sort_values(by="rating", ascending=False).reset_index(drop=True)
        team_df.to_csv("doubles-ranking.csv", index=False)
    else:
        # Create empty file if no data
        pd.DataFrame(columns=["team", "rating", "set_wins", "set_losses", "game_wins", "game_losses"]).to_csv("doubles-ranking.csv", index=False)

    # --- Generate and save individual rankings ---
    individual_data = []
    for player, rating in sorted(individual_ratings.items(), key=lambda item: -item[1]):
        stats = individual_stats.get(player, {"set_wins": 0, "set_losses": 0, "game_wins": 0, "game_losses": 0})
        individual_data.append({
            "player": player, "rating": round(rating, 1),
            "set_wins": stats["set_wins"], "set_losses": stats["set_losses"],
            "game_wins": stats["game_wins"], "game_losses": stats["game_losses"]
        })

    individual_df = pd.DataFrame(individual_data)
    if not individual_df.empty:
        individual_df = individual_df.sort_values(by="rating", ascending=False).reset_index(drop=True)
        individual_df.to_csv("doubles-individual-ranking.csv", index=False)
    else:
        pd.DataFrame(columns=["player", "rating", "set_wins", "set_losses", "game_wins", "game_losses"]).to_csv("doubles-individual-ranking.csv", index=False)


if __name__ == "__main__":
    main()