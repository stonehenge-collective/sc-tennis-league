package main

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/google/go-github/v67/github"
	"github.com/spf13/cobra"
)

var matchCmd = &cobra.Command{
	Use:   "match",
	Short: "Create match issues",
	Long:  "Create GitHub issues for recording tennis matches",
}

var singlesMatchCmd = &cobra.Command{
	Use:   "singles",
	Short: "Create a singles match issue",
	Long: `Create a GitHub issue for a singles match.

Examples:
  tennis match singles --players "@player_one,@player_two" --sets "6-3,4-6,6-4" --date "2025-01-15"
  tennis match singles -p "@player_one,@player_two" -s "6-3,4-6,6-4" -d "2025-01-15"

If date is not provided, today's date will be used.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		players, _ := cmd.Flags().GetString("players")
		sets, _ := cmd.Flags().GetString("sets")
		date, _ := cmd.Flags().GetString("date")

		if players == "" {
			return fmt.Errorf("players are required (use --players)")
		}
		if sets == "" {
			return fmt.Errorf("sets are required (use --sets)")
		}

		// Default to today if no date provided
		if date == "" {
			date = time.Now().Format("2006-01-02")
		}

		// Validate date format
		if !isValidDate(date) {
			return fmt.Errorf("invalid date format. Use YYYY-MM-DD")
		}

		// Parse players
		playerList := strings.Split(players, ",")
		if len(playerList) != 2 {
			return fmt.Errorf("exactly 2 players required for singles match")
		}
		for i, p := range playerList {
			playerList[i] = strings.TrimSpace(p)
		}

		// Parse and validate sets
		setsList, err := parseSets(sets)
		if err != nil {
			return fmt.Errorf("invalid sets format: %v", err)
		}

		// Create issue
		return createSinglesIssue(playerList, setsList, date)
	},
}

var doublesMatchCmd = &cobra.Command{
	Use:   "doubles",
	Short: "Create a doubles match issue",
	Long: `Create a GitHub issue for a doubles match.

Examples:
  tennis match doubles --teams "@player_one,@player_two||@player_three,@player_four" --sets "6-3,4-6,6-4" --date "2025-01-15"
  tennis match doubles -t "@player_one,@player_two||@player_three,@player_four" -s "6-3,4-6,6-4" -d "2025-01-15"

If date is not provided, today's date will be used.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		teams, _ := cmd.Flags().GetString("teams")
		sets, _ := cmd.Flags().GetString("sets")
		date, _ := cmd.Flags().GetString("date")

		if teams == "" {
			return fmt.Errorf("teams are required (use --teams)")
		}
		if sets == "" {
			return fmt.Errorf("sets are required (use --sets)")
		}

		// Default to today if no date provided
		if date == "" {
			date = time.Now().Format("2006-01-02")
		}

		// Validate date format
		if !isValidDate(date) {
			return fmt.Errorf("invalid date format. Use YYYY-MM-DD")
		}

		// Parse teams
		teamParts := strings.Split(teams, "||")
		if len(teamParts) != 2 {
			return fmt.Errorf("exactly 2 teams required for doubles match (separated by ||)")
		}

		var teamList [][]string
		for _, team := range teamParts {
			players := strings.Split(strings.TrimSpace(team), ",")
			if len(players) != 2 {
				return fmt.Errorf("each team must have exactly 2 players")
			}
			for i, p := range players {
				players[i] = strings.TrimSpace(p)
			}
			teamList = append(teamList, players)
		}

		// Parse and validate sets
		setsList, err := parseSets(sets)
		if err != nil {
			return fmt.Errorf("invalid sets format: %v", err)
		}

		// Create issue
		return createDoublesIssue(teamList, setsList, date)
	},
}

func isValidDate(date string) bool {
	dateRegex := regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`)
	if !dateRegex.MatchString(date) {
		return false
	}

	// Try to parse the date to ensure it's valid
	_, err := time.Parse("2006-01-02", date)
	return err == nil
}

func parseSets(sets string) ([]string, error) {
	setsList := strings.Split(sets, ",")
	setRegex := regexp.MustCompile(`^\d+-\d+$`)

	for i, set := range setsList {
		set = strings.TrimSpace(set)
		if !setRegex.MatchString(set) {
			return nil, fmt.Errorf("invalid set format '%s'. Use format like '6-3'", set)
		}
		setsList[i] = set
	}

	if len(setsList) == 0 {
		return nil, fmt.Errorf("at least one set is required")
	}

	return setsList, nil
}

func createSinglesIssue(players []string, sets []string, date string) error {
	ctx := context.Background()
	client := getGitHubClient()

	

	title := fmt.Sprintf("Singles Match: %s vs %s (%s)", players[0], players[1], date)

	body := fmt.Sprintf(`### Match date (YYYY-MM-DD)
%s

### Players (winner first, comma-separated @handles)
%s, %s

### Sets (one line per set, winner’s games first)
%s`, date, players[0], players[1], strings.Join(sets, "\n"))

	issueRequest := &github.IssueRequest{
		Title:  &title,
		Body:   &body,
		Labels: &[]string{"new-singles-match"},
	}

	fmt.Printf("Creating singles match issue...\n")
	fmt.Printf("Title: %s\n", title)

	issue, _, err := client.Issues.Create(ctx, owner, repo, issueRequest)
	if err != nil {
		return fmt.Errorf("failed to create issue: %v", err)
	}

	fmt.Printf("✅ Singles match issue created successfully!\n")
	fmt.Printf("Issue #%d: %s\n", *issue.Number, *issue.HTMLURL)

	return nil
}

func createDoublesIssue(teams [][]string, sets []string, date string) error {
	ctx := context.Background()
	client := getGitHubClient()

	// Format teams for display
	team1Str := fmt.Sprintf("%s, %s", teams[0][0], teams[0][1])
	team2Str := fmt.Sprintf("%s, %s", teams[1][0], teams[1][1])

	title := fmt.Sprintf("Doubles Match: (%s) vs (%s) (%s)", team1Str, team2Str, date)

	body := fmt.Sprintf(`### Match date (YYYY-MM-DD)
%s

### Teams (winner first, comma-separated @handles)
%s || %s

### Sets (one line per set, winner’s games first)
%s`, date, team1Str, team2Str, strings.Join(sets, "\n"))

	issueRequest := &github.IssueRequest{
		Title:  &title,
		Body:   &body,
		Labels: &[]string{"new-doubles-match"},
	}

	fmt.Printf("Creating doubles match issue...\n")
	fmt.Printf("Title: %s\n", title)

	issue, _, err := client.Issues.Create(ctx, owner, repo, issueRequest)
	if err != nil {
		return fmt.Errorf("failed to create issue: %v", err)
	}

	fmt.Printf("✅ Doubles match issue created successfully!\n")
	fmt.Printf("Issue #%d: %s\n", *issue.Number, *issue.HTMLURL)

	return nil
}

func init() {
	// Singles command flags
	singlesMatchCmd.Flags().StringP("players", "p", "", "Players separated by comma (winner first): @player_one,@player_two")
	singlesMatchCmd.Flags().StringP("sets", "s", "", "Sets separated by comma: 6-3,4-6,6-4")
	singlesMatchCmd.Flags().StringP("date", "d", "", "Match date (YYYY-MM-DD), defaults to today")

	// Doubles command flags
	doublesMatchCmd.Flags().StringP("teams", "t", "", "Teams separated by || : @player_one,@player_two||@player_three,@player_four")
	doublesMatchCmd.Flags().StringP("sets", "s", "", "Sets separated by comma: 6-3,4-6,6-4")
	doublesMatchCmd.Flags().StringP("date", "d", "", "Match date (YYYY-MM-DD), defaults to today")

	matchCmd.AddCommand(singlesMatchCmd)
	matchCmd.AddCommand(doublesMatchCmd)
	rootCmd.AddCommand(matchCmd)
}
