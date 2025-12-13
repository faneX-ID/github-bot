#!/usr/bin/env python3
"""
Workflow Manager - Handles GitHub Actions workflow operations.
"""
from typing import Dict, List, Optional, Tuple
from github import Github
from github.GithubException import GithubException


class WorkflowManager:
    """Manages GitHub Actions workflows."""

    def __init__(self, github: Github, repo_name: str, retryable_workflows: List[str] = None):
        """
        Initialize workflow manager.

        Args:
            github: GitHub API client
            repo_name: Repository name in format 'owner/repo'
            retryable_workflows: List of workflow names that can be retried
        """
        self.github = github
        self.repo = github.get_repo(repo_name)
        self.retryable_workflows = retryable_workflows or []

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

    def get_workflow_status(self, sha: str, branch: str = None) -> Dict:
        """
        Get status summary of all workflows for a commit and optionally branch.

        Args:
            sha: Commit SHA
            branch: Optional branch name to also check workflows for the branch

        Returns:
            Dictionary with workflow status information
        """
        # Get runs for the specific SHA
        runs = self.get_workflow_runs(sha)

        # Also get runs for the branch if provided
        # This is important because auto-fix commits might not trigger all workflows,
        # but workflows from earlier commits in the PR might still be running
        if branch:
            try:
                branch_runs = self.repo.get_workflow_runs(branch=branch)
                branch_workflow_runs = []
                for run in branch_runs:
                    branch_workflow_runs.append({
                        "id": run.id,
                        "name": run.name,
                        "status": run.status,
                        "conclusion": run.conclusion,
                        "workflow_id": run.workflow_id,
                        "created_at": run.created_at.isoformat() if run.created_at else None,
                        "url": run.html_url,
                    })
                # Combine and deduplicate by run ID
                all_runs = {run["id"]: run for run in runs}
                for run in branch_workflow_runs:
                    if run["id"] not in all_runs:
                        all_runs[run["id"]] = run
                runs = list(all_runs.values())
            except Exception as e:
                print(f"Warning: Could not get branch workflows: {e}")

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

    def are_all_checks_passed(self, sha: str, branch: str = None) -> Tuple[bool, Dict]:
        """
        Check if all checks and workflows have passed for a commit and branch.

        This method checks:
        1. All checks for the HEAD SHA
        2. All workflow runs for the HEAD SHA
        3. All workflow runs for the branch (if provided)

        Args:
            sha: Commit SHA
            branch: Optional branch name to also check workflows for the branch

        Returns:
            Tuple of (all_passed: bool, details: Dict)
        """
        import requests

        # Get checks for the SHA
        try:
            checks_url = f"https://api.github.com/repos/{self.repo.full_name}/commits/{sha}/check-runs"
            headers = {"Accept": "application/vnd.github.v3+json"}
            auth = self.github._Github__requester._Requester__authorizationHeader
            if auth:
                headers["Authorization"] = auth

            response = requests.get(checks_url, headers=headers, params={"per_page": 100})
            checks_data = response.json() if response.status_code == 200 else {}
            check_runs = checks_data.get("check_runs", [])
        except Exception as e:
            print(f"Warning: Could not get checks: {e}")
            check_runs = []

        # Get status for the SHA
        try:
            status_url = f"https://api.github.com/repos/{self.repo.full_name}/commits/{sha}/status"
            response = requests.get(status_url, headers=headers)
            status_data = response.json() if response.status_code == 200 else {}
            combined_status = status_data.get("state", "unknown")
        except Exception as e:
            print(f"Warning: Could not get status: {e}")
            combined_status = "unknown"

        # Get workflow status (includes branch workflows if branch is provided)
        workflow_status = self.get_workflow_status(sha, branch)

        # Check if all checks passed
        all_checks_passed = (
            len(check_runs) > 0 and
            all(check["status"] == "completed" and check["conclusion"] == "success"
                for check in check_runs if check.get("conclusion") != "skipped") and
            combined_status == "success"
        )

        # Check if all workflows passed
        workflows = workflow_status.get("workflows", [])
        all_workflows_passed = (
            len(workflows) > 0 and
            all(w.get("status") == "completed" and w.get("conclusion") == "success"
                for w in workflows)
        )

        # Check for running workflows
        running_workflows = [
            w for w in workflows
            if w.get("status") in ["in_progress", "queued", "waiting"]
        ]

        # Check for failed workflows
        failed_workflows = [
            w for w in workflows
            if w.get("status") == "completed" and w.get("conclusion") == "failure"
        ]

        # Check for pending checks
        pending_checks = [
            check for check in check_runs
            if check.get("status") != "completed"
        ]

        # Check for failed checks
        failed_checks = [
            check for check in check_runs
            if check.get("status") == "completed" and
            check.get("conclusion") not in ["success", "skipped"]
        ]

        truly_all_passed = (
            all_checks_passed and
            all_workflows_passed and
            len(running_workflows) == 0 and
            len(failed_workflows) == 0 and
            len(pending_checks) == 0 and
            len(failed_checks) == 0
        )

        details = {
            "all_checks_passed": all_checks_passed,
            "all_workflows_passed": all_workflows_passed,
            "truly_all_passed": truly_all_passed,
            "running_workflows": running_workflows,
            "failed_workflows": failed_workflows,
            "pending_checks": pending_checks,
            "failed_checks": failed_checks,
            "total_checks": len(check_runs),
            "total_workflows": len(workflows),
            "combined_status": combined_status,
        }

        return (truly_all_passed, details)

    def retry_workflow(self, sha: str, workflow_name: str) -> bool:
        """
        Retry a specific workflow.

        Args:
            sha: Commit SHA
            workflow_name: Name of the workflow to retry

        Returns:
            True if workflow was found and retry was triggered
        """
        # Check if workflow is retryable
        if self.retryable_workflows and workflow_name not in self.retryable_workflows:
            return False

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
            # and are in the retryable list (if list is provided)
            if run.conclusion == "failure" and run.status != "in_progress":
                # Check if workflow is retryable
                if self.retryable_workflows and run.name not in self.retryable_workflows:
                    continue

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
