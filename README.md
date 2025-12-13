# faneX-ID Bot

A GitHub Actions bot that assists with PR management, workflow retries, and automated feedback.

## Features

- **PR Comment Commands**: Responds to commands in PR comments
- **Workflow Management**: Retry failed workflows and CI checks
- **Automated Feedback**: Provides helpful comments on PRs with status and next steps
- **CI Status Reports**: Summarizes CI/CD status in PR comments

## Supported Commands

The bot responds to the following commands in PR comments:

- `/retry` - Retry all failed workflows
- `/retry <workflow-name>` - Retry a specific workflow
- `/test` - Run tests again
- `/status` - Show current CI/CD status
- `/help` - Show available commands

## Usage

### Installation in faneX-ID Repository

The bot is already integrated! The workflow file `.github/workflows/fanex-id-bot.yml` is included in the main repository.

To activate the bot:

1. The workflow is already in place at `.github/workflows/fanex-id-bot.yml`
2. The bot will automatically respond to PR comments and events
3. No additional configuration needed (uses default GitHub token)

### Manual Installation

If you want to use this bot in another repository:

1. Copy the `fanex-id-bot` directory to your repository
2. Add the workflow file to `.github/workflows/fanex-id-bot.yml`:

```yaml
name: faneX-ID Bot

on:
  issue_comment:
    types: [created]
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  actions: write

jobs:
  bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install PyGithub requests
      - run: python demo_repos/fanex-id-bot/bot.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
```

### Installation

1. Copy the `fanex-id-bot` directory to your repository
2. Add the workflow file to `.github/workflows/`
3. The bot will automatically respond to PR comments

## Configuration

The bot can be configured via environment variables:

- `BOT_ENABLED`: Enable/disable the bot (default: `true`)
- `ADMIN_USERS`: Comma-separated list of admin usernames
- `AUTO_RETRY`: Automatically retry failed workflows (default: `false`)

## Commands Reference

### `/retry`
Retries all failed workflows for the current PR.

**Example:**
```
/retry
```

### `/retry <workflow-name>`
Retries a specific workflow by name.

**Example:**
```
/retry backend-ci
```

### `/test`
Runs the test suite again.

**Example:**
```
/test
```

### `/status`
Shows the current status of all CI/CD checks.

**Example:**
```
/status
```

### `/help`
Shows available commands and usage.

**Example:**
```
/help
```

## Architecture

The bot consists of:

- **`bot.py`**: Main bot logic and command processor
- **`workflow_manager.py`**: Handles workflow retries and status checks
- **`comment_handler.py`**: Processes PR comments and responds
- **`action.yml`**: GitHub Action definition

## Development

To test the bot locally:

```bash
python bot.py --test
```

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the [LICENSE](LICENSE) file for details.
