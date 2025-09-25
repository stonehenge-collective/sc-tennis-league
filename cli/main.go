package main

import (
	"context"
	"fmt"
	"os"

	"github.com/google/go-github/v67/github"
	"github.com/spf13/cobra"
	"golang.org/x/oauth2"
)

const version = "1.0.0"

var (
	token string
	owner string
	repo  string
)

var rootCmd = &cobra.Command{
	Use:     "tennis",
	Version: version,
	Short:   "Tennis repository CLI tool",
	Long:    "A CLI tool to interact with the tennis repository - trigger workflows and create match issues",
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		// Skip token validation for version and help commands
		if cmd.Name() == "version" || cmd.Name() == "help" {
			return nil
		}

		// Get token from environment if not provided
		if token == "" {
			token = os.Getenv("GITHUB_TOKEN")
			if token == "" {
				token = os.Getenv("GH_TOKEN")
			}
			if token == "" {
				return fmt.Errorf("GitHub token required. Set GITHUB_TOKEN environment variable or use --token flag")
			}
		}

		// Get owner/repo from environment if not provided
		if owner == "" || repo == "" {
			githubRepo := os.Getenv("GITHUB_REPOSITORY")
			if githubRepo != "" {
				parts := splitRepoString(githubRepo)
				if len(parts) == 2 {
					owner = parts[0]
					repo = parts[1]
				}
			}
		}

		// Default fallback
		if owner == "" {
			owner = "stonehenge-collective"
		}
		if repo == "" {
			repo = "tennis"
		}

		return nil
	},
}

func splitRepoString(repoString string) []string {
	for i, char := range repoString {
		if char == '/' {
			return []string{repoString[:i], repoString[i+1:]}
		}
	}
	return []string{repoString}
}

func getGitHubClient() *github.Client {
	ctx := context.Background()
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: token},
	)
	tc := oauth2.NewClient(ctx, ts)
	return github.NewClient(tc)
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number",
	Long:  "Print the version number of the tennis CLI",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("tennis CLI v%s\n", version)
	},
}

func init() {
	rootCmd.PersistentFlags().StringVar(&token, "token", "", "GitHub token")
	rootCmd.PersistentFlags().StringVar(&owner, "owner", "", "Repository owner")
	rootCmd.PersistentFlags().StringVar(&repo, "repo", "", "Repository name")

	rootCmd.AddCommand(versionCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
