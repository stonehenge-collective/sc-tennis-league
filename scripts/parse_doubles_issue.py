import os
import re
import sys
import yaml


def parse_issue_body(body):
    """Parses the issue body to extract doubles match details."""
    if body is None:
        return {}
    details = {}

    date_match = re.search(r"### Match date \(YYYY-MM-DD\)\s*\n\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", body)
    if date_match:
        details["date"] = date_match.group(1).strip()

    # Parse teams: @github_handle1, @github_handle2 || @github_handle3, @github_handle4
    teams_match = re.search(r"### Teams.*?\n\s*([^\n]+)", body)
    if teams_match:
        teams_str = teams_match.group(1).strip()
        if "||" in teams_str:
            team1_str, team2_str = teams_str.split("||")
            team1_players = [p.strip().replace("@", "") for p in team1_str.split(",")]
            team2_players = [p.strip().replace("@", "") for p in team2_str.split(",")]
            details["team1"] = team1_players
            details["team2"] = team2_players
            # Flatten for individual player access
            details["players"] = team1_players + team2_players

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
    """Validates the parsed doubles match data."""
    errors = []
    if not data.get("date"):
        errors.append("Match date is missing or not in the correct YYYY-MM-DD format.")

    if not data.get("team1") or len(data["team1"]) != 2:
        errors.append("Team 1 must have exactly two players (e.g., '@player_one, @player_two').")

    if not data.get("team2") or len(data["team2"]) != 2:
        errors.append("Team 2 must have exactly two players (e.g., '@player_three, @player_four').")

    if not data.get("sets"):
        errors.append("At least one set must be recorded in the 'Sets' section.")
    else:
        for i, s in enumerate(data["sets"]):
            if not (isinstance(s, list) and len(s) == 2 and all(isinstance(x, int) for x in s)):
                errors.append(
                    f"Set #{i+1} has an invalid format. It must be `<Team1Games>-<Team2Games>` (e.g., '6-3')."
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
                "team1": parsed_data["team1"],
                "team2": parsed_data["team2"],
                "sets": parsed_data["sets"],
                "source_issue": int(issue_number),
            }
            yaml_string = yaml.dump(match_file_content, default_flow_style=False, sort_keys=False)

            f.write("validation_failed=false\n")
            f.write(f"date={parsed_data['date']}\n")
            # Individual players for tagging
            f.write(f"player1={parsed_data['team1'][0]}\n")
            f.write(f"player2={parsed_data['team1'][1]}\n")
            f.write(f"player3={parsed_data['team2'][0]}\n")
            f.write(f"player4={parsed_data['team2'][1]}\n")
            f.write("match_yaml<<EOF\n")
            f.write(yaml_string)
            f.write("\nEOF\n")


if __name__ == "__main__":
    main()
