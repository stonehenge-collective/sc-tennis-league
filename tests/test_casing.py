"""Tests for case-insensitive player handle normalization.

GitHub usernames are unique and case-insensitive, so "Johnor12" and
"johnor12" must resolve to one player. These cover the shared helper and
its effect through the parsers and ranking aggregation.
"""

import pytest

import scripts.generate_doubles_ranking as doubles
import scripts.generate_singles_ranking as singles
from scripts.build_history import load_matches_from_directory
from scripts.elo_utils import normalize_player
from scripts.parse_doubles_issue import parse_issue_body as parse_doubles
from scripts.parse_singles_issue import parse_issue_body as parse_singles


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


# --- normalize_player ------------------------------------------------------


def test_normalize_lowercases():
    assert normalize_player("Johnor12") == "johnor12"


def test_normalize_strips_whitespace_and_at_sign():
    assert normalize_player("  @HunterJSB ") == "hunterjsb"


def test_normalize_is_idempotent():
    assert normalize_player(normalize_player("MixedCase")) == "mixedcase"


def test_normalize_already_canonical_unchanged():
    assert normalize_player("jeffson66") == "jeffson66"


# --- parsers store canonical handles --------------------------------------


def test_singles_parser_lowercases_handles():
    body = """### Match date (YYYY-MM-DD)
2026-01-01
### Players
@HunterJSB, @Johnor12
### Sets
6-3
"""
    assert parse_singles(body)["players"] == ["hunterjsb", "johnor12"]


def test_doubles_parser_lowercases_handles():
    body = """### Match date (YYYY-MM-DD)
2026-01-01
### Teams
@Alice, @Bob || @Carol, @Dave
### Sets
6-3
"""
    parsed = parse_doubles(body)
    assert parsed["team1"] == ["alice", "bob"]
    assert parsed["team2"] == ["carol", "dave"]


# --- aggregation dedupes across casing ------------------------------------


def test_singles_mixed_casing_aggregates_to_one_player():
    # Same player entered two ways across two matches must not split.
    singles.apply_match({"players": ["HunterJSB", "bob"], "sets": [[6, 3]]})
    singles.apply_match({"players": ["hunterjsb", "carol"], "sets": [[6, 4]]})
    assert "HunterJSB" not in singles.stats
    assert singles.stats["hunterjsb"]["set_wins"] == 2


def test_doubles_mixed_casing_aggregates_to_one_team_and_player():
    doubles.apply_match(
        {"team1": ["Alice", "Bob"], "team2": ["c", "d"], "sets": [[6, 3]]}
    )
    doubles.apply_match(
        {"team1": ["alice", "bob"], "team2": ["e", "f"], "sets": [[6, 4]]}
    )
    # One canonical team key and one canonical player entry.
    assert "alice, bob" in doubles.team_ratings
    assert doubles.team_stats["alice, bob"]["set_wins"] == 2
    assert doubles.individual_stats["alice"]["set_wins"] == 2


# --- match history page links match the (lowercase) profile pages ----------


def test_history_profile_links_are_normalized(tmp_path):
    # A match recorded with a capital handle must link to the lowercase
    # profile page that build_player_pages actually generates.
    (tmp_path / "2026-01-01-1.yml").write_text(
        "date: '2026-01-01'\n"
        "players:\n- HunterJSB\n- Johnor12\n"
        "sets:\n- - 6\n  - 3\nsource_issue: 1\n"
    )
    matches = load_matches_from_directory(str(tmp_path), "singles", {})
    display = matches[0]["players_display"]
    assert "player_profile_hunterjsb.html" in display
    assert "player_profile_johnor12.html" in display
    assert "Johnor12" not in display and "HunterJSB" not in display
