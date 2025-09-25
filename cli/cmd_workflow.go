package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/google/go-github/v67/github"
	"github.com/spf13/cobra"
)

var workflowCmd = &cobra.Command{
	Use:   "workflow",
	Short: "Trigger GitHub Actions workflows",
	Long:  "Trigger GitHub Actions workflows in the tennis repository",
}

var triggerWorkflowCmd = &cobra.Command{
	Use:   "trigger [workflow-name]",
	Short: "Trigger a specific workflow",
	Long: `Trigger a specific workflow by name or filename.

Examples:
  tennis workflow trigger rebuild-rankings --env github-pages
  tennis workflow trigger rebuild-rankings.yml --environment production
  tennis workflow trigger "🏆 Rebuild Rankings" -e github-pages`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		workflowName := args[0]
		environment, _ := cmd.Flags().GetString("environment")

		ctx := context.Background()
		client := getGitHubClient()

		// First, list workflows to find the right one
		workflows, _, err := client.Actions.ListWorkflows(ctx, owner, repo, nil)
		if err != nil {
			return fmt.Errorf("failed to list workflows: %v", err)
		}

		var workflowID int64
		var foundWorkflow *github.Workflow

		// Try to match by name, filename, or ID
		for _, workflow := range workflows.Workflows {
			if workflow.Name != nil && strings.EqualFold(*workflow.Name, workflowName) {
				workflowID = *workflow.ID
				foundWorkflow = workflow
				break
			}
			if workflow.Path != nil && strings.HasSuffix(*workflow.Path, workflowName) {
				workflowID = *workflow.ID
				foundWorkflow = workflow
				break
			}
			// Also try matching the filename without extension
			if workflow.Path != nil {
				parts := strings.Split(*workflow.Path, "/")
				filename := parts[len(parts)-1]
				nameWithoutExt := strings.TrimSuffix(filename, ".yml")
				nameWithoutExt = strings.TrimSuffix(nameWithoutExt, ".yaml")
				if strings.EqualFold(nameWithoutExt, workflowName) {
					workflowID = *workflow.ID
					foundWorkflow = workflow
					break
				}
			}
		}

		if foundWorkflow == nil {
			fmt.Printf("Available workflows:\n")
			for _, workflow := range workflows.Workflows {
				fmt.Printf("  - %s (%s)\n", *workflow.Name, *workflow.Path)
			}
			return fmt.Errorf("workflow '%s' not found", workflowName)
		}

		// Get the default branch for the ref
		repoInfo, _, err := client.Repositories.Get(ctx, owner, repo)
		if err != nil {
			return fmt.Errorf("failed to get repository info: %v", err)
		}

		ref := *repoInfo.DefaultBranch

		// Prepare workflow inputs
		inputs := make(map[string]interface{})
		if environment != "" {
			inputs["environment"] = environment
		} else {
			// Default environment for rebuild-rankings workflow
			inputs["environment"] = "github-pages"
		}

		// Trigger the workflow
		dispatchOptions := &github.CreateWorkflowDispatchEventRequest{
			Ref:    ref,
			Inputs: inputs,
		}

		fmt.Printf("Triggering workflow: %s\n", *foundWorkflow.Name)
		fmt.Printf("Path: %s\n", *foundWorkflow.Path)
		fmt.Printf("Ref: %s\n", ref)
		if len(inputs) > 0 {
			fmt.Printf("Inputs: %+v\n", inputs)
		}

		_, err = client.Actions.CreateWorkflowDispatchEventByID(ctx, owner, repo, workflowID, *dispatchOptions)
		if err != nil {
			return fmt.Errorf("failed to trigger workflow: %v", err)
		}

		fmt.Printf("✅ Workflow triggered successfully!\n")
		fmt.Printf("View runs at: https://github.com/%s/%s/actions\n", owner, repo)

		return nil
	},
}

func init() {
	triggerWorkflowCmd.Flags().StringP("environment", "e", "", "Environment to run against (defaults to 'github-pages' for rebuild-rankings)")
	workflowCmd.AddCommand(triggerWorkflowCmd)
	rootCmd.AddCommand(workflowCmd)
}
