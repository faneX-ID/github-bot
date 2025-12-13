#!/usr/bin/env python3
"""
faneX-ID Bot - GitHub Actions Bot for PR Management

This bot responds to commands in PR comments and manages workflows.
"""
import os
import sys
import re
import json
from typing import Dict, List, Optional, Tuple
from github import Github
from workflow_manager import WorkflowManager
from comment_handler import CommentHandler
import yaml
import requests
from pathlib import Path


class FanexIDBot:
    """Main bot class that processes commands and manages workflows."""

    def __init__(self, github_token: str, repo_name: str):
        """
        Initialize the bot.

        Args:
            github_token: GitHub personal access token
            repo_name: Repository name in format 'owner/repo'
        """
        self.github = Github(github_token)
        self.repo = self.github.get_repo(repo_name)
        self.repo_name = repo_name
        
        # Load configuration
        self.config = self._load_config()
        
        # Get retryable workflows for this repository
        self.retryable_workflows = self.config.get('retryable_workflows', {}).get(
            repo_name, 
            self.config.get('retryable_workflows', {}).get('default', [])
        )
        
        self.workflow_manager = WorkflowManager(self.github, repo_name, self.retryable_workflows)
        self.comment_handler = CommentHandler(self.repo)
    
    def _load_config(self) -> dict:
        """Load bot configuration from config.yaml or fetch from main repo."""
        # Try to load local config first
        config_path = Path("config.yaml")
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}
                    if config:
                        return config
            except Exception:
                pass
        
        # Fallback: fetch from main repository
        main_repo = 'faneX-ID/core'
        main_branch = 'main'
        
        try:
            config_url = f"https://raw.githubusercontent.com/{main_repo}/{main_branch}/github-bot/config.yaml"
            response = requests.get(config_url, timeout=10)
            if response.status_code == 200:
                config = yaml.safe_load(response.text) or {}
                if config:
                    return config
        except Exception as e:
            print(f"Could not fetch config from main repo: {e}")
        
        # Default config
        return {
            'enabled': True,
            'admin_users': ['FaserF', 'fabia'],
            'retryable_workflows': {},
            'main_repository': 'faneX-ID/core',
            'main_branch': 'main'
        }

    def process_comment(self, comment_body: str, pr_number: int, commenter: str) -> Optional[str]:
        """
        Process a PR comment and execute commands.

        Args:
            comment_body: The comment text
            pr_number: PR number
            commenter: Username of the commenter

        Returns:
            Response message or None
        """
        # Check if comment contains a bot command
        commands = self._extract_commands(comment_body)
        if not commands:
            return None

        # Get PR
        pr = self.repo.get_pull(pr_number)

        responses = []
        for command, args in commands:
            try:
                response = self._execute_command(command, args, pr, commenter)
                if response:
                    responses.append(response)
            except Exception as e:
                responses.append(f"❌ Error executing `{command}`: {str(e)}")

        return "\n\n".join(responses) if responses else None

    def _extract_commands(self, text: str) -> List[Tuple[str, List[str]]]:
        """
        Extract bot commands from text.

        Commands start with / and are on their own line or at the start of a line.

        Returns:
            List of (command, args) tuples
        """
        commands = []
        # Match commands like /retry, /retry workflow-name, /test, etc.
        pattern = r'^/(\w+)(?:\s+(.+))?$'
        for line in text.split('\n'):
            line = line.strip()
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                cmd = match.group(1).lower()
                args_str = match.group(2) or ""
                args = args_str.split() if args_str else []
                commands.append((cmd, args))
        return commands

    def _execute_command(
        self,
        command: str,
        args: List[str],
        pr,
        commenter: str
    ) -> Optional[str]:
        """
        Execute a bot command.

        Args:
            command: Command name
            args: Command arguments
            pr: Pull request object
            commenter: Username of the command issuer

        Returns:
            Response message
        """
        if command == "help":
            return self._help_command()

        elif command == "retry":
            return self._retry_command(args, pr, commenter)

        elif command == "test":
            return self._test_command(pr, commenter)

        elif command == "status":
            return self._status_command(pr)

        else:
            return f"❓ Unknown command: `/{command}`. Use `/help` for available commands."

    def _help_command(self) -> str:
        """Show help message."""
        return """🤖 **faneX-ID Bot Commands**

Available commands:

- `/retry` - Retry all failed workflows
- `/retry <workflow-name>` - Retry a specific workflow (e.g., `/retry backend-ci`)
- `/test` - Run tests again
- `/status` - Show current CI/CD status
- `/help` - Show this help message

**Examples:**
- `/retry` - Retries all failed checks
- `/retry frontend-ci` - Retries only the frontend-ci workflow
- `/status` - Shows summary of all CI checks"""

    def _retry_command(self, args: List[str], pr, commenter: str) -> str:
        """
        Retry failed workflows.

        Args:
            args: Command arguments (optional workflow name)
            pr: Pull request object
            commenter: Username
        """
        # Check permissions (for now, allow anyone - can be restricted)
        workflow_name = args[0] if args else None

        try:
            if workflow_name:
                result = self.workflow_manager.retry_workflow(
                    pr.head.sha,
                    workflow_name
                )
                if result:
                    return f"✅ Retrying workflow `{workflow_name}`..."
                else:
                    return f"❌ Could not find or retry workflow `{workflow_name}`"
            else:
                # Retry all failed workflows
                results = self.workflow_manager.retry_failed_workflows(pr.head.sha)
                if results:
                    workflows = ", ".join(f"`{w}`" for w in results)
                    return f"✅ Retrying {len(results)} failed workflow(s): {workflows}"
                else:
                    return "ℹ️ No failed workflows to retry, or all workflows are already running."
        except Exception as e:
            return f"❌ Error retrying workflows: {str(e)}"

    def _test_command(self, pr, commenter: str) -> str:
        """
        Trigger test workflows.

        Args:
            pr: Pull request object
            commenter: Username
        """
        # Check permissions
        admin_users = self.config.get('admin_users', [])
        admin_only_commands = self.config.get('admin_only_commands', [])
        
        if 'test' in admin_only_commands and commenter not in admin_users:
            return f"❌ Only admins can use `/test`. Admins: {', '.join(admin_users)}"
        
        try:
            # Get available workflows from config or use defaults
            workflows_to_trigger = self.retryable_workflows[:5] if self.retryable_workflows else []
            triggered = []

            for workflow_name in workflows_to_trigger:
                if self.workflow_manager.retry_workflow(pr.head.sha, workflow_name):
                    triggered.append(workflow_name)

            if triggered:
                workflows = ", ".join(f"`{w}`" for w in triggered)
                return f"✅ Triggered test workflows: {workflows}"
            else:
                available = ", ".join(f"`{w}`" for w in self.retryable_workflows[:5]) if self.retryable_workflows else "none configured"
                return f"❌ Could not trigger test workflows. Available workflows: {available}"
        except Exception as e:
            return f"❌ Error triggering tests: {str(e)}"

    def _status_command(self, pr) -> str:
        """
        Get CI/CD status summary.

        Args:
            pr: Pull request object
        """
        try:
            status = self.workflow_manager.get_workflow_status(pr.head.sha)
            return self._format_status(status)
        except Exception as e:
            return f"❌ Error getting status: {str(e)}"

    def _format_status(self, status: Dict) -> str:
        """Format workflow status as a markdown table."""
        if not status.get("workflows"):
            return "ℹ️ No workflow runs found for this commit."

        lines = ["## 📊 CI/CD Status\n"]
        lines.append("| Workflow | Status |\n")
        lines.append("|----------|--------|\n")

        for workflow in status["workflows"]:
            name = workflow["name"]
            state = workflow["status"]
            conclusion = workflow.get("conclusion", "unknown")

            # Emoji based on status
            if conclusion == "success":
                emoji = "✅"
            elif conclusion == "failure":
                emoji = "❌"
            elif conclusion == "cancelled":
                emoji = "⚠️"
            elif state == "in_progress":
                emoji = "🔄"
            else:
                emoji = "⏳"

            status_text = f"{emoji} {conclusion.upper()}" if conclusion != "unknown" else f"{emoji} {state.upper()}"
            lines.append(f"| `{name}` | {status_text} |\n")

        # Summary
        total = len(status["workflows"])
        success = sum(1 for w in status["workflows"] if w.get("conclusion") == "success")
        failed = sum(1 for w in status["workflows"] if w.get("conclusion") == "failure")
        in_progress = sum(1 for w in status["workflows"] if w.get("status") == "in_progress")

        lines.append(f"\n**Summary:** {success}/{total} passed, {failed} failed, {in_progress} in progress")

        return "".join(lines)

    def post_pr_summary(self, pr_number: int) -> None:
        """
        Post a summary comment on PR with CI status and helpful information.

        Args:
            pr_number: PR number
        """
        pr = self.repo.get_pull(pr_number)
        status = self.workflow_manager.get_workflow_status(pr.head.sha)

        # Check if we already posted a summary
        comments = pr.get_issue_comments()
        bot_comments = [c for c in comments if c.user.login.endswith("[bot]") and "faneX-ID Bot" in c.body]

        # Format summary
        summary = self.comment_handler.create_pr_summary(pr, status)

        if bot_comments:
            # Update existing comment
            bot_comments[0].edit(summary)
        else:
            # Create new comment
            pr.create_issue_comment(summary)


def main():
    """Main entry point for the bot."""
    # Get environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    event_path = os.getenv("GITHUB_EVENT_PATH")

    if not github_token or not repo_name:
        print("Error: GITHUB_TOKEN and GITHUB_REPOSITORY must be set")
        sys.exit(1)

    # Add current directory to path for imports
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    if bot_dir not in sys.path:
        sys.path.insert(0, bot_dir)

    # Read GitHub event
    if event_path and os.path.exists(event_path):
        with open(event_path) as f:
            event = json.load(f)
    else:
        event = {}

    bot = FanexIDBot(github_token, repo_name)

    # Handle different event types
    if event.get("action") == "created" and "comment" in event:
        # Issue comment event
        comment = event["comment"]
        issue = event["issue"]

        # Check if it's a PR (issues and PRs use the same API)
        if "pull_request" in issue:
            pr_number = issue["number"]
            commenter = comment["user"]["login"]
            comment_body = comment["body"]

            response = bot.process_comment(comment_body, pr_number, commenter)
            if response:
                # Post response as comment
                pr = bot.repo.get_pull(pr_number)
                pr.create_issue_comment(response)

    elif event.get("action") in ["opened", "synchronize"] and "pull_request" in event:
        # PR opened or updated
        pr_number = event["pull_request"]["number"]
        bot.post_pr_summary(pr_number)


if __name__ == "__main__":
    main()
