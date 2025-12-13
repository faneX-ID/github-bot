#!/usr/bin/env python3
"""
Workflow Manager - Handles GitHub Actions workflow operations.
"""
from typing import Dict, List, Optional
from github import Github
from github.GithubException import GithubException


class WorkflowManager:
    """Manages GitHub Actions workflows."""

    def __init__(self, github: Github, repo_name: str):
        """
        Initialize workflow manager.

        Args:
            github: GitHub API client
            repo_name: Repository name in format 'owner/repo'
        """
        self.github = github
        self.repo = github.get_repo(repo_name)

    def get_workflow_runs(self, sha: str) -> List[Dict]:
        """
        Get all workflow runs for a specific commit.

        Args:
            sha: Commit SHA

        Returns:
            List of workflow run information
        """
        runs = self.repo.get_workflow_runs(head_sha=sha)
        workflow_runs = []

        for run in runs:
            workflow_runs.append({
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "conclusion": run.conclusion,
                "workflow_id": run.workflow_id,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "url": run.html_url,
            })

        return workflow_runs

    def get_workflow_status(self, sha: str) -> Dict:
        """
        Get status summary of all workflows for a commit.

        Args:
            sha: Commit SHA

        Returns:
            Dictionary with workflow status information
        """
        runs = self.get_workflow_runs(sha)

        # Group by workflow name
        workflows = {}
        for run in runs:
            name = run["name"]
            if name not in workflows:
                workflows[name] = {
                    "name": name,
                    "status": run["status"],
                    "conclusion": run.get("conclusion"),
                    "url": run["url"],
                    "latest_run_id": run["id"],
                }
            else:
                # Keep the latest run
                if run["id"] > workflows[name]["latest_run_id"]:
                    workflows[name].update({
                        "status": run["status"],
                        "conclusion": run.get("conclusion"),
                        "url": run["url"],
                        "latest_run_id": run["id"],
                    })

        return {
            "sha": sha,
            "workflows": list(workflows.values()),
        }

    def retry_workflow(self, sha: str, workflow_name: str) -> bool:
        """
        Retry a specific workflow.

        Args:
            sha: Commit SHA
            workflow_name: Name of the workflow to retry

        Returns:
            True if workflow was found and retry was triggered
        """
        try:
            # Get workflow runs for this commit
            runs = self.repo.get_workflow_runs(head_sha=sha)

            # Find the workflow by name
            for run in runs:
                if run.name == workflow_name:
                    # Re-run the workflow
                    run.rerun()
                    return True

            return False
        except GithubException as e:
            print(f"Error retrying workflow: {e}")
            return False

    def retry_failed_workflows(self, sha: str) -> List[str]:
        """
        Retry all failed workflows for a commit.

        Args:
            sha: Commit SHA

        Returns:
            List of workflow names that were retried
        """
        runs = self.repo.get_workflow_runs(head_sha=sha)
        retried = []

        for run in runs:
            # Only retry failed workflows that are not currently running
            if run.conclusion == "failure" and run.status != "in_progress":
                try:
                    run.rerun()
                    retried.append(run.name)
                except GithubException as e:
                    print(f"Error retrying {run.name}: {e}")

        return retried

    def get_failed_workflows(self, sha: str) -> List[Dict]:
        """
        Get list of failed workflows.

        Args:
            sha: Commit SHA

        Returns:
            List of failed workflow information
        """
        runs = self.get_workflow_runs(sha)
        return [
            run for run in runs
            if run.get("conclusion") == "failure"
        ]
