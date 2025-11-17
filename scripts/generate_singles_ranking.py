import glob
import sys
import yaml
import pandas as pd
from scripts.elo_utils import update_elo_ratings

ratings = {}
elo_changes = []
# Stats per player. We'll compute:
# - set_wins/set_losses: count of sets won/lost
# - game_wins/game_losses: total games won/lost across all recorded sets
# - wins/losses: kept for backward compatibility (mirror set stats)
stats = {}


def _ensure_player(player: str) -> None:
    if player not in stats:
        stats[player] = {
            "set_wins": 0,
            "set_losses": 0,
            "game_wins": 0,
            "game_losses": 0,
        }


def apply_match(match):
    """Update ratings and aggregates from a single match file.

    Elo is applied per set. Each set is an independent event that updates
    the players' ratings based solely on who won the set (score margin ignored).
    """
    player1, player2 = match["players"]

    # Ensure player entries exist for aggregation
    _ensure_player(player1)
    _ensure_player(player2)

    # Iterate sets: first number maps to player1's games, second to player2's
    sets = match.get("sets") or []
    for s in sets:
        try:
            p1_games = int(s[0])
            p2_games = int(s[1])
        except (ValueError, TypeError, IndexError):
            # Skip malformed set entries
            continue

        # Aggregate games
        stats[player1]["game_wins"] += p1_games
        stats[player1]["game_losses"] += p2_games
        stats[player2]["game_wins"] += p2_games
        stats[player2]["game_losses"] += p1_games

        # Determine set winner
        if p1_games == p2_games:
            # Ignore invalid/tied set
            continue

        set_winner = player1 if p1_games > p2_games else player2
        set_loser = player2 if set_winner == player1 else player1

        # Record set W/L
        stats[set_winner]["set_wins"] += 1
        stats[set_loser]["set_losses"] += 1

        # Elo update for this set (independent event)
        old_winner_rating = ratings.get(set_winner, 1200)
        old_loser_rating = ratings.get(set_loser, 1200)

        new_winner_rating, new_loser_rating = update_elo_ratings(ratings, set_winner, set_loser)

        ratings[set_winner] = new_winner_rating
        ratings[set_loser] = new_loser_rating

        elo_changes.append({
            "player": set_winner,
            "old_rating": old_winner_rating,
            "new_rating": new_winner_rating,
            "change": new_winner_rating - old_winner_rating
        })
        elo_changes.append({
            "player": set_loser,
            "old_rating": old_loser_rating,
            "new_rating": new_loser_rating,
            "change": new_loser_rating - old_loser_rating
        })


def main():
    """Main function to calculate and print rankings."""
    # All players start with default rating of 1200 - no CSV bootstrapping needed

    # Process matches
    for fn in sorted(glob.glob("singles-matches/*.yml")):
        with open(fn) as f:
            try:
                match_data = yaml.safe_load(f)
                if match_data and "players" in match_data:
                    apply_match(match_data)
            except yaml.YAMLError as e:
                print(f"Error reading {fn}: {e}", file=sys.stderr)

    # Create new DataFrame with updated ratings and stats
    new_players_data = []
    for p, r in sorted(ratings.items(), key=lambda item: -item[1]):
        player_stats = stats.get(
            p,
            {
                "set_wins": 0,
                "set_losses": 0,
                "game_wins": 0,
                "game_losses": 0,
            },
        )
        new_players_data.append(
            {
                "player": p,
                "rating": round(r, 1),
                # Primary stats
                "set_wins": player_stats["set_wins"],
                "set_losses": player_stats["set_losses"],
                "game_wins": player_stats["game_wins"],
                "game_losses": player_stats["game_losses"],
            }
        )

    if not new_players_data:
        # Handle case with no players
        df = pd.DataFrame(
            columns=[
                "player",
                "rating",
                "set_wins",
                "set_losses",
                "game_wins",
                "game_losses",
            ]
        )
        df.to_csv(sys.stdout, index=False)
        return

    df = pd.DataFrame(new_players_data)
    df = df.sort_values(by="rating", ascending=False).reset_index(drop=True)

    # Select and order columns for the output
    desired_columns = [
        "player",
        "rating",
        "set_wins",
        "set_losses",
        "game_wins",
        "game_losses",
    ]

    # Ensure all desired columns exist (defensive in case of missing keys)
    for col in desired_columns:
        if col not in df.columns:
            df[col] = 0
    output_df = df[desired_columns]

    output_df.to_csv(sys.stdout, index=False)

    # Save ELO changes to a file
    elo_changes_df = pd.DataFrame(elo_changes)
    elo_changes_df.to_csv("temp-rankings/elo_changes.csv", index=False)


if __name__ == "__main__":
    main()
