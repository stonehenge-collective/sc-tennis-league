"""
This module provides shared ELO rating calculation functions.
"""

K = 32

def expected(rA, rB):
    """
    Calculate the expected score of player A in a match against player B.
    """
    return 1 / (1 + 10 ** ((rB - rA) / 400))

def update_elo_ratings(ratings, winner, loser):
    """
    Updates the ELO ratings for a winner and loser.

    Args:
        ratings (dict): A dictionary of player ratings.
        winner (str): The name of the winner.
        loser (str): The name of the loser.

    Returns:
        tuple: A tuple containing the new rating for the winner and loser.
    """
    rW = ratings.get(winner, 1200)
    rL = ratings.get(loser, 1200)
    eW = expected(rW, rL)
    eL = expected(rL, rW)

    new_rW = rW + K * (1 - eW)
    new_rL = rL + K * (0 - eL)

    return new_rW, new_rL

def normalize_team(team_players):
    """Normalize team representation so PlayerA,PlayerB == PlayerB,PlayerA"""
    if len(team_players) != 2:
        raise ValueError(f"Team must have exactly 2 players, got {len(team_players)}")

    sorted_players = sorted(team_players)
    return f"{sorted_players[0]}, {sorted_players[1]}"

def update_doubles_elo_ratings(team_ratings, individual_ratings, winner_team, loser_team):
    """
    Updates the ELO ratings for a doubles match.
    """
    # 1. Team-based ELO
    winner_team_key = f"{sorted(winner_team)[0]}, {sorted(winner_team)[1]}"
    loser_team_key = f"{sorted(loser_team)[0]}, {sorted(loser_team)[1]}"

    rW_team = team_ratings.get(winner_team_key, 1200)
    rL_team = team_ratings.get(loser_team_key, 1200)
    eW_team = expected(rW_team, rL_team)

    new_rW_team = rW_team + K * (1 - eW_team)
    new_rL_team = rL_team + K * (0 - (1-eW_team))

    # 2. Individual-based ELO
    r_w1 = individual_ratings.get(winner_team[0], 1200)
    r_w2 = individual_ratings.get(winner_team[1], 1200)
    r_l1 = individual_ratings.get(loser_team[0], 1200)
    r_l2 = individual_ratings.get(loser_team[1], 1200)

    r_winner_eff = (r_w1 + r_w2) / 2
    r_loser_eff = (r_l1 + r_l2) / 2

    e_winner = expected(r_winner_eff, r_loser_eff)

    rating_change = K * (1 - e_winner)

    new_r_w1 = r_w1 + rating_change
    new_r_w2 = r_w2 + rating_change
    new_r_l1 = r_l1 - rating_change
    new_r_l2 = r_l2 - rating_change

    return new_rW_team, new_rL_team, new_r_w1, new_r_w2, new_r_l1, new_r_l2
