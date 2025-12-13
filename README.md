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
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install PyGithub requests PyYAML PyJWT cryptography

      # Optional: Generate GitHub App Token (if secrets are configured)
      # This allows the bot to post as "faneX-ID Bot" instead of "github-actions[bot]"
      - name: Generate GitHub App Token
        id: app_token
        if: ${{ secrets.FANEX_BOT_APP_ID != '' && secrets.FANEX_BOT_PRIVATE_KEY != '' }}
        run: |
          # Create a temporary script to generate the token
          cat > generate_token.py << 'EOF'
          import jwt
          import time
          import sys
          import os

          app_id = os.environ['APP_ID']
          private_key = os.environ['PRIVATE_KEY']

          # Generate JWT
          now = int(time.time())
          payload = {
              'iat': now - 60,
              'exp': now + (10 * 60),
              'iss': app_id
          }

          token = jwt.encode(payload, private_key, algorithm='RS256')
          print(f"::set-output name=token::{token}")
          EOF

          python generate_token.py
        env:
          APP_ID: ${{ secrets.FANEX_BOT_APP_ID }}
          PRIVATE_KEY: ${{ secrets.FANEX_BOT_PRIVATE_KEY }}

      - name: Run bot
        env:
          # Use GitHub App token if available, otherwise fall back to GITHUB_TOKEN
          FANEX_BOT_TOKEN: ${{ steps.app_token.outputs.token }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
        run: |
          # Determine which token to use
          if [ -n "$FANEX_BOT_TOKEN" ]; then
            echo "✅ Using GitHub App token - comments will appear as faneX-ID Bot"
            export GITHUB_TOKEN="$FANEX_BOT_TOKEN"
          else
            echo "ℹ️ Using GITHUB_TOKEN - comments will appear as github-actions[bot]"
            echo "   To use faneX-ID Bot identity, set secrets: FANEX_BOT_APP_ID and FANEX_BOT_PRIVATE_KEY"
          fi

          python demo_repos/fanex-id-bot/bot.py
```

### Token Configuration in Workflow

The workflow supports two authentication methods:

#### Method 1: GitHub App Token (Recommended)

**Required Secrets:**
- `FANEX_BOT_APP_ID`: Your GitHub App ID
- `FANEX_BOT_PRIVATE_KEY`: Your GitHub App private key (full PEM content)

**Benefits:**
- Comments appear as "faneX-ID Bot" instead of "github-actions[bot]"
- Better user experience and clearer bot identity
- More professional appearance

**Setup:** See [Token Configuration](#token-configuration) section above.

#### Method 2: GitHub Actions Token (Default)

**No configuration needed** - uses the automatically provided `GITHUB_TOKEN`.

**Limitations:**
- Comments appear as "github-actions[bot]"
- Less personalized bot identity

**Token Priority:**
1. If `FANEX_BOT_APP_ID` and `FANEX_BOT_PRIVATE_KEY` secrets are set, the workflow will generate a GitHub App token
2. Otherwise, it falls back to the default `GITHUB_TOKEN`

### Installation

1. Copy the `fanex-id-bot` directory to your repository
2. Add the workflow file to `.github/workflows/`
3. The bot will automatically respond to PR comments

## Token Configuration

The bot supports two authentication methods:

### Option 1: GitHub App Token (Recommended)

Using a GitHub App token allows the bot to post comments as "faneX-ID Bot" instead of "github-actions[bot]". This provides a better user experience and clearer bot identity.

#### Step 1: Create a GitHub App

1. Go to your organization or user settings
2. Navigate to **Developer settings** → **GitHub Apps**
3. Click **New GitHub App**
4. Configure the app:
   - **Name**: `faneX-ID Bot` (or your preferred name)
   - **Homepage URL**: Your repository URL
   - **Webhook**: Optional (not needed for this bot)
   - **Permissions**:
     - **Repository permissions**:
       - Contents: `Read`
       - Pull requests: `Write`
       - Actions: `Write`
       - Issues: `Write` (for comments)
   - **Where can this GitHub App be installed?**: Choose your organization or account
5. Click **Create GitHub App**

#### Step 2: Generate Private Key

1. After creating the app, scroll down to **Private keys**
2. Click **Generate a private key**
3. Save the downloaded `.pem` file securely (you'll need this for the secret)

#### Step 3: Install the App

1. Click **Install App** in the app settings
2. Select the organization or account where you want to install it
3. Select the repositories (or all repositories)
4. Click **Install**

#### Step 4: Get App ID

1. In the app settings, note the **App ID** (you'll need this for the secret)

#### Step 5: Configure Repository Secrets

Add the following secrets to your repository (Settings → Secrets and variables → Actions):

- **`FANEX_BOT_APP_ID`**: The App ID from step 4 (e.g., `123456`)
- **`FANEX_BOT_PRIVATE_KEY`**: The entire contents of the `.pem` file from step 2

**Example of private key format:**
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
(multiple lines)
...
-----END RSA PRIVATE KEY-----
```

#### Step 6: Update Workflow

The workflow will automatically detect these secrets and generate a token. No additional changes needed if using the provided workflow template.

### Option 2: GitHub Actions Token (Default)

If you don't configure a GitHub App, the bot will use the default `GITHUB_TOKEN` provided by GitHub Actions. This works out of the box but comments will appear as "github-actions[bot]".

**No configuration needed** - the `GITHUB_TOKEN` is automatically available in GitHub Actions workflows.

### Token Priority

The bot uses tokens in this order:
1. `FANEX_BOT_TOKEN` (if GitHub App is configured)
2. `GITHUB_TOKEN` (fallback, always available)

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

## Token Setup Checklist

Use this checklist to set up the bot with a GitHub App token:

- [ ] Create GitHub App in organization/user settings
- [ ] Configure app permissions (Contents: Read, Pull requests: Write, Actions: Write, Issues: Write)
- [ ] Generate and download private key (.pem file)
- [ ] Install the app to your organization/account
- [ ] Note the App ID from app settings
- [ ] Add `FANEX_BOT_APP_ID` secret to repository (Settings → Secrets → Actions)
- [ ] Add `FANEX_BOT_PRIVATE_KEY` secret to repository (full PEM content, including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`)
- [ ] Test the workflow - bot comments should appear as "faneX-ID Bot"

## Troubleshooting

### Bot comments appear as "github-actions[bot]"

**Cause:** GitHub App token is not configured or not being generated.

**Solutions:**
1. Verify secrets are set correctly:
   - Go to repository Settings → Secrets and variables → Actions
   - Check that `FANEX_BOT_APP_ID` and `FANEX_BOT_PRIVATE_KEY` exist
2. Verify private key format:
   - Must include `-----BEGIN RSA PRIVATE KEY-----` at the start
   - Must include `-----END RSA PRIVATE KEY-----` at the end
   - Must include all lines in between (no truncation)
3. Check workflow logs:
   - Look for "Generate GitHub App Token" step
   - Verify it runs (should show "✅ Using GitHub App token" if successful)

### Token generation fails

**Common issues:**
- **Invalid App ID**: Ensure `FANEX_BOT_APP_ID` is a numeric value (e.g., `123456`)
- **Invalid private key**: Ensure the entire PEM file content is copied, including headers
- **App not installed**: Install the GitHub App to your organization/account
- **Insufficient permissions**: Verify app has required permissions (Pull requests: Write, Actions: Write)

### Bot doesn't respond to commands

**Check:**
1. Workflow is enabled and running
2. Bot has write permissions to pull requests
3. Commands are formatted correctly (e.g., `/retry` on its own line)
4. Comment is on a PR (not an issue)

## Development

To test the bot locally:

```bash
# Set environment variables
export GITHUB_TOKEN="your_token_here"
export GITHUB_REPOSITORY="owner/repo"
export GITHUB_EVENT_PATH="path/to/event.json"

# Run bot
python bot.py
```

For testing with GitHub App token:

```bash
# Generate token first (requires APP_ID and PRIVATE_KEY)
export APP_ID="your_app_id"
export PRIVATE_KEY="$(cat path/to/private-key.pem)"
python scripts/generate_app_token.py

# Then use the generated token
export FANEX_BOT_TOKEN="generated_token"
export GITHUB_REPOSITORY="owner/repo"
python bot.py
```

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the [LICENSE](LICENSE) file for details.
