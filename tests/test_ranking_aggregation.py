"""Characterization tests for stat/rating aggregation in the ranking generators.

Both generators accumulate into module-level globals, so each test resets
that state first. These tests pin down the *current* aggregation behavior,
including a known inconsistency: singles counts games on tied sets while
doubles does not (see test_tied_set_*).
"""

import pytest

import scripts.generate_doubles_ranking as doubles
import scripts.generate_singles_ranking as singles


@pytest.fixture(autouse=True)
def reset_module_state():
    singles.ratings.clear()
    singles.stats.clear()
    singles.elo_changes.clear()
    doubles.team_ratings.clear()
    doubles.team_stats.clear()
    doubles.individual_ratings.clear()
    doubles.individual_stats.clear()
    yield


# --- Singles ---------------------------------------------------------------


def test_singles_single_set_updates_ratings():
    singles.apply_match({"players": ["alice", "bob"], "sets": [[6, 3]]})
    assert singles.ratings["alice"] == pytest.approx(1216.0)
    assert singles.ratings["bob"] == pytest.approx(1184.0)


def test_singles_single_set_aggregates_stats():
    singles.apply_match({"players": ["alice", "bob"], "sets": [[6, 3]]})
    assert singles.stats["alice"] == {
        "set_wins": 1,
        "set_losses": 0,
        "game_wins": 6,
        "game_losses": 3,
    }
    assert singles.stats["bob"] == {
        "set_wins": 0,
        "set_losses": 1,
        "game_wins": 3,
        "game_losses": 6,
    }


def test_singles_records_two_elo_changes_per_set():
    singles.apply_match({"players": ["alice", "bob"], "sets": [[6, 3], [6, 4]]})
    assert len(singles.elo_changes) == 4


def test_singles_multiple_sets_apply_independently():
    # alice wins both sets; her rating compounds across the two updates.
    singles.apply_match({"players": ["alice", "bob"], "sets": [[6, 3], [6, 4]]})
    assert singles.stats["alice"]["set_wins"] == 2
    assert singles.ratings["alice"] > 1216.0


def test_singles_tied_set_counts_games_but_not_set_or_elo():
    # Current (quirky) behavior: a tied set still aggregates games but
    # produces no set W/L and no rating change.
    singles.apply_match({"players": ["alice", "bob"], "sets": [[4, 4]]})
    assert singles.stats["alice"]["game_wins"] == 4
    assert singles.stats["alice"]["game_losses"] == 4
    assert singles.stats["alice"]["set_wins"] == 0
    assert singles.stats["alice"]["set_losses"] == 0
    assert singles.ratings == {}


def test_singles_malformed_set_entry_is_skipped():
    singles.apply_match({"players": ["alice", "bob"], "sets": ["6-x"]})
    assert singles.stats["alice"]["game_wins"] == 0
    assert singles.ratings == {}


# --- Doubles ---------------------------------------------------------------


def test_doubles_single_set_updates_team_ratings():
    doubles.apply_match({"team1": ["a", "b"], "team2": ["c", "d"], "sets": [[6, 3]]})
    assert doubles.team_ratings["a, b"] == pytest.approx(1216.0)
    assert doubles.team_ratings["c, d"] == pytest.approx(1184.0)


def test_doubles_single_set_updates_individual_ratings():
    doubles.apply_match({"team1": ["a", "b"], "team2": ["c", "d"], "sets": [[6, 3]]})
    assert doubles.individual_ratings["a"] == pytest.approx(1216.0)
    assert doubles.individual_ratings["b"] == pytest.approx(1216.0)
    assert doubles.individual_ratings["c"] == pytest.approx(1184.0)
    assert doubles.individual_ratings["d"] == pytest.approx(1184.0)


def test_doubles_individual_stats_aggregate_per_player():
    doubles.apply_match({"team1": ["a", "b"], "team2": ["c", "d"], "sets": [[6, 3]]})
    assert doubles.individual_stats["a"] == {
        "set_wins": 1,
        "set_losses": 0,
        "game_wins": 6,
        "game_losses": 3,
    }
    assert doubles.individual_stats["c"] == {
        "set_wins": 0,
        "set_losses": 1,
        "game_wins": 3,
        "game_losses": 6,
    }


def test_doubles_team_key_is_order_independent():
    doubles.apply_match(
        {"team1": ["bob", "alice"], "team2": ["c", "d"], "sets": [[6, 3]]}
    )
    assert "alice, bob" in doubles.team_ratings


def test_doubles_tied_set_aggregates_nothing():
    # Contrast with singles: doubles skips a tied set entirely (no games
    # counted). This documents the cross-script inconsistency.
    doubles.apply_match({"team1": ["a", "b"], "team2": ["c", "d"], "sets": [[4, 4]]})
    assert doubles.individual_stats["a"]["game_wins"] == 0
    assert doubles.team_ratings == {}
