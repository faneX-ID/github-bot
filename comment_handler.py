#!/usr/bin/env python3
"""
Comment Handler - Creates formatted PR comments and summaries.
"""
from typing import Dict
from github import Repository
from github.PullRequest import PullRequest


class CommentHandler:
    """Handles creation of PR comments and summaries."""

    def __init__(self, repo: Repository):
        """
        Initialize comment handler.

        Args:
            repo: GitHub repository object
        """
        self.repo = repo

    def create_pr_summary(self, pr: PullRequest, status: Dict) -> str:
        """
        Create a summary comment for a PR.

        Args:
            pr: Pull request object
            status: Workflow status dictionary

        Returns:
            Formatted markdown comment
        """
        lines = [
            "## 🤖 faneX-ID Bot - PR Summary\n",
            f"**PR:** #{pr.number} - {pr.title}\n",
            f"**Author:** @{pr.user.login}\n",
            f"**Branch:** `{pr.head.ref}` → `{pr.base.ref}`\n",
        ]

        # Add CI/CD status
        if status.get("workflows"):
            lines.append("\n### 📊 CI/CD Status\n\n")
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
                workflow_url = workflow.get("url", "")
                if workflow_url:
                    lines.append(f"| [`{name}`]({workflow_url}) | {status_text} |\n")
                else:
                    lines.append(f"| `{name}` | {status_text} |\n")

            # Summary
            total = len(status["workflows"])
            success = sum(1 for w in status["workflows"] if w.get("conclusion") == "success")
            failed = sum(1 for w in status["workflows"] if w.get("conclusion") == "failure")
            in_progress = sum(1 for w in status["workflows"] if w.get("status") == "in_progress")

            lines.append(f"\n**Summary:** {success}/{total} passed, {failed} failed, {in_progress} in progress\n")

            # Add helpful commands if there are failures
            if failed > 0:
                lines.append("\n### 🔧 Quick Actions\n\n")
                lines.append("If workflows failed, you can retry them:\n\n")
                lines.append("- `/retry` - Retry all failed workflows\n")
                lines.append("- `/retry <workflow-name>` - Retry a specific workflow\n")
                lines.append("- `/status` - Check current status\n")
        else:
            lines.append("\n⏳ CI/CD checks are running...\n")

        # Add helpful links
        lines.append("\n### 📚 Useful Commands\n\n")
        lines.append("- `/help` - Show all available commands\n")
        lines.append("- `/status` - Get current CI/CD status\n")
        lines.append("- `/retry` - Retry failed workflows\n")

        return "".join(lines)

    def create_error_comment(self, error_message: str, context: str = "") -> str:
        """
        Create an error comment.

        Args:
            error_message: Error message
            context: Additional context

        Returns:
            Formatted error comment
        """
        lines = [
            "## ❌ Error\n\n",
            f"**Message:** {error_message}\n",
        ]

        if context:
            lines.append(f"\n**Context:** {context}\n")

        lines.append("\nPlease check the logs and try again.\n")

        return "".join(lines)

    def create_success_comment(self, message: str) -> str:
        """
        Create a success comment.

        Args:
            message: Success message

        Returns:
            Formatted success comment
        """
        return f"## ✅ Success\n\n{message}\n"
