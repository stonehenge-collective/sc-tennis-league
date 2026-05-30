"""Characterization tests for scripts/parse_doubles_issue.py."""

from scripts.parse_doubles_issue import parse_issue_body, validate_data

VALID_BODY = """### Match date (YYYY-MM-DD)
2025-08-05
### Teams (winning team first: @a, @b || @c, @d)
@alice, @bob || @carol, @dave
### Sets (one line per set, winning team's games first)
6-3
6-4
"""


def test_parse_extracts_date():
    assert parse_issue_body(VALID_BODY)["date"] == "2025-08-05"


def test_parse_splits_teams_on_double_pipe():
    parsed = parse_issue_body(VALID_BODY)
    assert parsed["team1"] == ["alice", "bob"]
    assert parsed["team2"] == ["carol", "dave"]


def test_parse_flattens_players_for_individual_access():
    assert parse_issue_body(VALID_BODY)["players"] == [
        "alice",
        "bob",
        "carol",
        "dave",
    ]


def test_parse_sets_into_int_pairs():
    assert parse_issue_body(VALID_BODY)["sets"] == [[6, 3], [6, 4]]


def test_parse_none_body_returns_empty_dict():
    assert parse_issue_body(None) == {}


def test_parse_without_double_pipe_omits_teams():
    # Current behavior: no "||" separator -> team keys are simply absent.
    body = """### Match date (YYYY-MM-DD)
2025-01-01
### Teams
@alice, @bob
### Sets
6-3
"""
    parsed = parse_issue_body(body)
    assert "team1" not in parsed
    assert "team2" not in parsed


def test_validate_accepts_valid_data():
    assert validate_data(parse_issue_body(VALID_BODY)) == []


def test_validate_flags_missing_team():
    errors = validate_data(
        {"date": "2025-01-01", "team1": ["a", "b"], "sets": [[6, 3]]}
    )
    assert any("team 2" in e.lower() for e in errors)


def test_validate_flags_wrong_team_size():
    errors = validate_data(
        {
            "date": "2025-01-01",
            "team1": ["a"],
            "team2": ["c", "d"],
            "sets": [[6, 3]],
        }
    )
    assert any("team 1" in e.lower() for e in errors)
