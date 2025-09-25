# Tennis CLI

A command-line tool to interact with the tennis repository - trigger workflows and create match issues.

## Installation

```bash
cd cli
go build -o tennis
```

## Configuration

The CLI requires a GitHub token to interact with the repository. You can provide it in several ways:

1. Environment variable: `GITHUB_TOKEN=your_token_here`
2. Environment variable: `GH_TOKEN=your_token_here`  
3. Command line flag: `--token your_token_here`

The repository owner/name can be set via:

1. Environment variable: `GITHUB_REPOSITORY=owner/repo`
2. Command line flags: `--owner owner --repo repo`
3. Defaults to `stonehenge-collective/tennis`

## Usage

### Trigger Workflows

Trigger the rebuild rankings workflow:

```bash
./tennis workflow trigger rebuild-rankings
```

You can also use the full workflow name or filename:

```bash
./tennis workflow trigger "🏆 Rebuild Rankings"
./tennis workflow trigger rebuild-rankings.yml
```

### Create Match Issues

#### Singles Match

Create a singles match issue:

```bash
./tennis match singles --players "@alice,@bob" --sets "6-3,4-6,6-4" --date "2025-01-15"
```

Short form:

```bash
./tennis match singles -p "@alice,@bob" -s "6-3,4-6,6-4" -d "2025-01-15"
```

If no date is provided, today's date will be used:

```bash
./tennis match singles -p "@alice,@bob" -s "6-3,4-6,6-4"
```

#### Doubles Match

Create a doubles match issue:

```bash
./tennis match doubles --teams "@alice,@bob||@charlie,@dave" --sets "6-3,4-6,6-4" --date "2025-01-15"
```

Short form:

```bash
./tennis match doubles -t "@alice,@bob||@charlie,@dave" -s "6-3,4-6,6-4" -d "2025-01-15"
```

## Examples

```bash
# Set up environment
export GITHUB_TOKEN=your_token_here
export GITHUB_REPOSITORY=stonehenge-collective/tennis

# Trigger rebuild rankings workflow
./tennis workflow trigger rebuild-rankings

# Create a singles match (Alice beats Bob)
./tennis match singles -p "@alice,@bob" -s "6-3,4-6,6-4"

# Create a doubles match (Alice & Bob beat Charlie & Dave)
./tennis match doubles -t "@alice,@bob||@charlie,@dave" -s "6-3,4-6,10-8"

# Use specific date
./tennis match singles -p "@alice,@bob" -s "6-2,6-1" -d "2025-01-15"
```

## Notes

- Players should be listed with the winner first
- Teams in doubles matches should be listed with the winning team first
- Sets should be in the format `games-games` (e.g., `6-3`, `7-5`, `10-8`)
- Dates must be in YYYY-MM-DD format
- GitHub handles should include the @ symbol