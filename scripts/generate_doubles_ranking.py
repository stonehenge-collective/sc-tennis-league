import glob
import sys
import yaml
import pandas as pd

K = 32

# --- Team-based data ---
team_ratings = {}
team_stats = {}

# --- Individual-based data ---
individual_ratings = {}
individual_stats = {}


def expected(rA, rB):
    return 1 / (1 + 10 ** ((rB - rA) / 400))


def normalize_team(team_players):
    """Normalize team representation so PlayerA,PlayerB == PlayerB,PlayerA"""
    if len(team_players) != 2:
        raise ValueError(f"Team must have exactly 2 players, got {len(team_players)}")
    
    sorted_players = sorted(team_players)
    return f"{sorted_players[0]}, {sorted_players[1]}"


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
        # 1. Team-based ELO
        rW_team = team_ratings.get(set_winner_key, 1200)
        rL_team = team_ratings.get(set_loser_key, 1200)
        eW_team = expected(rW_team, rL_team)
        team_ratings[set_winner_key] = rW_team + K * (1 - eW_team)
        team_ratings[set_loser_key] = rL_team + K * (0 - (1-eW_team))

        # 2. Individual-based ELO
        # Get individual ratings, default to 1200
        r_p1_t1 = individual_ratings.get(team1_players[0], 1200)
        r_p2_t1 = individual_ratings.get(team1_players[1], 1200)
        r_p1_t2 = individual_ratings.get(team2_players[0], 1200)
        r_p2_t2 = individual_ratings.get(team2_players[1], 1200)

        # Effective team rating is the average of individual ratings
        r_team1_eff = (r_p1_t1 + r_p2_t1) / 2
        r_team2_eff = (r_p1_t2 + r_p2_t2) / 2

        e_team1 = expected(r_team1_eff, r_team2_eff)

        # Determine winner and loser for this set
        (winner_p1, winner_p2) = (team1_players[0], team1_players[1]) if t1_games > t2_games else (team2_players[0], team2_players[1])
        (loser_p1, loser_p2) = (team2_players[0], team2_players[1]) if t1_games > t2_games else (team1_players[0], team1_players[1])

        (r_w1, r_w2) = (individual_ratings.get(winner_p1, 1200), individual_ratings.get(winner_p2, 1200))
        (r_l1, r_l2) = (individual_ratings.get(loser_p1, 1200), individual_ratings.get(loser_p2, 1200))

        # Calculate rating change based on effective team ratings
        rating_change = K * (1 - (e_team1 if set_winner_players == team1_players else (1 - e_team1)))

        # Apply rating change to each player
        individual_ratings[winner_p1] = r_w1 + rating_change
        individual_ratings[winner_p2] = r_w2 + rating_change
        individual_ratings[loser_p1] = r_l1 - rating_change
        individual_ratings[loser_p2] = r_l2 - rating_change


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