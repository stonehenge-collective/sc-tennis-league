import os
import re
import sys
import yaml


def parse_issue_body(body):
    """Parses the issue body to extract match details."""
    if body is None:
        return {}
    details = {}

    date_match = re.search(r"### Match date \(YYYY-MM-DD\)\s*\n\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", body)
    if date_match:
        details["date"] = date_match.group(1).strip()

    # Support both old and new headings (winner first vs player 1 first)
    players_match = re.search(r"### Players.*?\n\s*([^\n]+)", body)
    if players_match:
        players_str = players_match.group(1).strip()
        details["players"] = [p.strip().replace("@", "") for p in players_str.split(",")]

    sets_match = re.search(r"### Sets.*?\n(.*?)(?=\n###|\Z)", body, re.DOTALL)
    if sets_match:
        sets_str = sets_match.group(1).strip()
        sets = []
        for line in sets_str.splitlines():
            line = line.strip()
            if line:
                try:
                    score = [int(s.strip()) for s in line.split("-")]
                    sets.append(score)
                except ValueError:
                    sets.append(line)
        details["sets"] = sets

    return details


def validate_data(data):
    """Validates the parsed match data."""
    errors = []
    if not data.get("date"):
        errors.append("Match date is missing or not in the correct YYYY-MM-DD format.")

    if not data.get("players") or len(data["players"]) != 2:
        errors.append("Exactly two players must be specified (e.g., '@player_one, @player_two'). The first listed is Player 1.")

    if not data.get("sets"):
        errors.append("At least one set must be recorded in the 'Sets' section.")
    else:
        for i, s in enumerate(data["sets"]):
            if not (isinstance(s, list) and len(s) == 2 and all(isinstance(x, int) for x in s)):
                errors.append(
                    f"Set #{i+1} has an invalid format. It must be `<Player1Games>-<Player2Games>` (e.g., '6-3')."
                )

    return errors


def main():
    issue_body = os.getenv("ISSUE_BODY", "")
    issue_number = os.getenv("ISSUE_NUMBER")
    output_path = os.getenv("GITHUB_OUTPUT")

    if not issue_number or not output_path:
        print("Error: Required environment variables not set.", file=sys.stderr)
        sys.exit(1)

    parsed_data = parse_issue_body(issue_body)
    errors = validate_data(parsed_data)

    with open(output_path, "a") as f:
        if errors:
            f.write("validation_failed=true\n")
            f.write("error_message<<EOF\n")
            f.write("\n".join(f"- {e}" for e in errors))
            f.write("\nEOF\n")
        else:
            match_file_content = {
                "date": parsed_data["date"],
                "players": parsed_data["players"],
                "sets": parsed_data["sets"],
                "source_issue": int(issue_number),
            }
            yaml_string = yaml.dump(match_file_content, default_flow_style=False, sort_keys=False)

            f.write("validation_failed=false\n")
            f.write(f"date={parsed_data['date']}\n")
            # Do not emit winner/loser; sets determine winners per the new convention
            f.write(f"player1={parsed_data['players'][0]}\n")
            f.write(f"player2={parsed_data['players'][1]}\n")
            f.write("match_yaml<<EOF\n")
            f.write(yaml_string)
            f.write("\nEOF\n")


if __name__ == "__main__":
    main()
    # body = """
    # ### Match date (YYYY-MM-DD)
    # 2025-08-05
    # ### Players (winner first, comma-separated @handles)
    # @dev-jeb , @hunterjsb
    # ### Sets (one line per set, winner’s games first)
    # 3-2
    # 4-2
    # 2-2
    # """
    # parsed_data = parse_issue_body(body)
