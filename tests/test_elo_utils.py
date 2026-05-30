"""Characterization tests for the shared ELO math.

These lock in the *current* behavior of scripts/elo_utils.py so future
refactors can't silently change ranking outcomes. They assert exact values
for the K=32, default-rating-1200 configuration the league runs today.
"""

import math

import pytest

from scripts.elo_utils import (
    K,
    expected,
    normalize_team,
    update_doubles_elo_ratings,
    update_elo_ratings,
)


def test_k_factor_is_32():
    assert K == 32


def test_expected_even_match_is_half():
    assert expected(1200, 1200) == 0.5


def test_expected_sums_to_one():
    a, b = 1350, 1180
    assert expected(a, b) + expected(b, a) == pytest.approx(1.0)


def test_expected_higher_rating_favored():
    assert expected(1400, 1200) > 0.5
    assert expected(1200, 1400) < 0.5


def test_expected_known_value_200_point_gap():
    # Classic Elo: a 200-point edge ~= 0.76 expected score.
    assert expected(1400, 1200) == pytest.approx(0.7597469, abs=1e-6)


def test_update_elo_even_match():
    ratings = {}
    new_w, new_l = update_elo_ratings(ratings, "winner", "loser")
    assert new_w == pytest.approx(1216.0)
    assert new_l == pytest.approx(1184.0)


def test_update_elo_is_zero_sum_for_equal_ratings():
    ratings = {}
    new_w, new_l = update_elo_ratings(ratings, "w", "l")
    assert (new_w - 1200) == pytest.approx(-(new_l - 1200))


def test_update_elo_does_not_mutate_input_dict():
    # Current behavior: update_elo_ratings only reads from `ratings`;
    # callers are responsible for writing the results back.
    ratings = {"w": 1300, "l": 1100}
    update_elo_ratings(ratings, "w", "l")
    assert ratings == {"w": 1300, "l": 1100}


def test_update_elo_uses_default_1200_for_unseen_players():
    ratings = {"w": 1200}  # loser unseen -> defaults to 1200
    new_w, new_l = update_elo_ratings(ratings, "w", "l")
    assert new_w == pytest.approx(1216.0)
    assert new_l == pytest.approx(1184.0)


def test_normalize_team_is_order_independent():
    assert normalize_team(["bob", "alice"]) == normalize_team(["alice", "bob"])


def test_normalize_team_format():
    assert normalize_team(["bob", "alice"]) == "alice, bob"


def test_normalize_team_requires_exactly_two_players():
    with pytest.raises(ValueError):
        normalize_team(["solo"])
    with pytest.raises(ValueError):
        normalize_team(["a", "b", "c"])


def test_doubles_elo_even_match():
    team_ratings = {}
    individual_ratings = {}
    (
        new_rw_team,
        new_rl_team,
        new_w1,
        new_w2,
        new_l1,
        new_l2,
    ) = update_doubles_elo_ratings(
        team_ratings, individual_ratings, ["a", "b"], ["c", "d"]
    )
    # Team ratings behave like a singles match between the two team keys.
    assert new_rw_team == pytest.approx(1216.0)
    assert new_rl_team == pytest.approx(1184.0)
    # Individuals each move by K*(1 - 0.5) = 16 in the current model.
    assert new_w1 == pytest.approx(1216.0)
    assert new_w2 == pytest.approx(1216.0)
    assert new_l1 == pytest.approx(1184.0)
    assert new_l2 == pytest.approx(1184.0)


def test_doubles_elo_individual_change_is_symmetric():
    # Winners gain exactly what losers lose, per player, in the current model.
    _, _, w1, w2, l1, l2 = update_doubles_elo_ratings({}, {}, ["a", "b"], ["c", "d"])
    assert (w1 - 1200) == pytest.approx(-(l1 - 1200))
    assert (w2 - 1200) == pytest.approx(-(l2 - 1200))


def test_doubles_elo_uses_average_of_individual_ratings():
    # Effective team rating is the mean of the two member ratings.
    individual_ratings = {"a": 1400, "b": 1200, "c": 1200, "d": 1200}
    _, _, w1, w2, l1, l2 = update_doubles_elo_ratings(
        {}, individual_ratings, ["a", "b"], ["c", "d"]
    )
    # winner effective = 1300, loser effective = 1200 -> e_winner = expected(1300,1200)
    expected_change = K * (1 - expected(1300, 1200))
    assert w1 == pytest.approx(1400 + expected_change)
    assert w2 == pytest.approx(1200 + expected_change)
    assert l1 == pytest.approx(1200 - expected_change)
    assert l2 == pytest.approx(1200 - expected_change)


def test_expected_is_finite_for_extreme_gaps():
    assert math.isfinite(expected(3000, 1))
    assert math.isfinite(expected(1, 3000))
