"""Characterization tests for scripts/parse_singles_issue.py.

Locks in how the issue-form markdown is parsed and validated today,
including the lenient fallbacks (malformed set lines kept as raw strings).
"""

from scripts.parse_singles_issue import parse_issue_body, validate_data

VALID_BODY = """### Match date (YYYY-MM-DD)
2025-08-05
### Players (winner first, comma-separated @handles)
@alice , @bob
### Sets (one line per set, winner's games first)
6-3
4-6
6-4
"""


def test_parse_extracts_date():
    assert parse_issue_body(VALID_BODY)["date"] == "2025-08-05"


def test_parse_strips_at_signs_and_whitespace_from_players():
    assert parse_issue_body(VALID_BODY)["players"] == ["alice", "bob"]


def test_parse_sets_into_int_pairs():
    assert parse_issue_body(VALID_BODY)["sets"] == [[6, 3], [4, 6], [6, 4]]


def test_parse_none_body_returns_empty_dict():
    assert parse_issue_body(None) == {}


def test_parse_malformed_set_line_kept_as_raw_string():
    body = """### Match date (YYYY-MM-DD)
2025-01-01
### Players
@a, @b
### Sets
6-x
"""
    # Current behavior: a line that can't be int-parsed is appended verbatim.
    assert parse_issue_body(body)["sets"] == ["6-x"]


def test_parse_three_number_set_line_is_not_rejected_here():
    # "6-3-2" splits into three ints; parsing keeps it, validation rejects it.
    body = """### Match date (YYYY-MM-DD)
2025-01-01
### Players
@a, @b
### Sets
6-3-2
"""
    assert parse_issue_body(body)["sets"] == [[6, 3, 2]]


def test_validate_accepts_valid_data():
    assert validate_data(parse_issue_body(VALID_BODY)) == []


def test_validate_flags_missing_date():
    errors = validate_data({"players": ["a", "b"], "sets": [[6, 3]]})
    assert any("date" in e.lower() for e in errors)


def test_validate_flags_wrong_player_count():
    errors = validate_data({"date": "2025-01-01", "players": ["a"], "sets": [[6, 3]]})
    assert any("two players" in e.lower() for e in errors)


def test_validate_flags_missing_sets():
    errors = validate_data({"date": "2025-01-01", "players": ["a", "b"]})
    assert any("set" in e.lower() for e in errors)


def test_validate_flags_three_number_set():
    errors = validate_data(
        {"date": "2025-01-01", "players": ["a", "b"], "sets": [[6, 3, 2]]}
    )
    assert any("invalid format" in e.lower() for e in errors)
