"""
GitHub Integration Service (Phase 15).

Provides enterprise-grade GitHub repository integration:
1. Validates repository URLs and retrieves rich metadata (owner, repo, stars, forks, visibility, language).
2. Discovers and verifies branches for branch selection workflows.
3. Tracks commit status and checks if local analysis is up to date or behind remote commits.
4. Performs remote repository refresh by pulling latest commits and triggering incremental sync.
5. Security:
   - Does not store tokens in plain text.
   - Supports unauthenticated access for public repositories.
   - Clear, actionable error messages for unavailable repos, invalid URLs, missing branches, clone failures, and rate limits.
"""

import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from git import Repo, GitCommandError
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    EntityNotFoundException,
    ValidationException,
    GitCloneException,
)
from app.models.project import Project, utc_now
from app.schemas.project import (
    GitHubValidateResponse,
    GitHubStatusResponse,
    GitHubRefreshResponse,
)
from app.services.sync_service import sync_service

logger = logging.getLogger("docpilot.github")


class GitHubService:
    """Service handling GitHub repository validation, metadata extraction, branch tracking, and refresh."""

    GITHUB_API_BASE = "https://api.github.com"

    def parse_github_url(self, url: str) -> Tuple[str, str]:
        """
        Parses GitHub repository owner and repository name from URL or shorthand.
        Supports:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - owner/repo
        """
        raw_url = (url or "").strip()
        if not raw_url:
            raise ValidationException(
                message="GitHub repository URL cannot be empty.",
                details={"provided_url": url},
            )

        # 1. Shorthand "owner/repo"
        shorthand_match = re.match(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$", raw_url)
        if shorthand_match:
            owner, repo = shorthand_match.groups()
            repo = repo.removesuffix(".git")
            return owner, repo

        # 2. HTTP/HTTPS or SSH format
        url_match = re.search(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", raw_url)
        if url_match:
            owner, repo = url_match.groups()
            return owner, repo

        raise ValidationException(
            message=f"Invalid GitHub repository URL: '{url}'. Format must be https://github.com/owner/repository or owner/repository.",
            details={"provided_url": url},
        )

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Builds HTTP headers with secure token resolution (without logging or exposing tokens)."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DocPilot-AI/1.0",
        }
        effective_token = token or settings.GITHUB_TOKEN
        if effective_token and effective_token.strip():
            headers["Authorization"] = f"Bearer {effective_token.strip()}"
        return headers

    async def validate_repository(
        self,
        url: str,
        token: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> GitHubValidateResponse:
        """
        Validates GitHub repository accessibility, fetches metadata, and lists branches.
        Works without authentication for public repositories.
        """
        owner, repo = self.parse_github_url(url)
        headers = self._get_headers(token)
        repo_api_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"

        repo_data: Dict[str, Any] = {}
        branches: List[str] = []
        rate_limit_remaining: Optional[int] = None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(repo_api_url, headers=headers)
                rate_limit_header = res.headers.get("x-ratelimit-remaining")
                if rate_limit_header is not None:
                    try:
                        rate_limit_remaining = int(rate_limit_header)
                    except ValueError:
                        pass

                if res.status_code == 404:
                    raise ValidationException(
                        message=f"Repository unavailable or not found: '{owner}/{repo}'. Please ensure the repository is public or provide an authorized GitHub access token in Settings.",
                        details={"owner": owner, "repo": repo, "http_status": 404},
                    )

                if res.status_code in (403, 429):
                    if rate_limit_remaining == 0 or "rate limit" in res.text.lower():
                        raise ValidationException(
                            message="GitHub API rate limit exceeded. Please configure a GitHub personal access token in Settings or try again later.",
                            details={"http_status": res.status_code},
                        )
                    raise ValidationException(
                        message=f"GitHub access forbidden for '{owner}/{repo}'. Ensure permissions or token configuration.",
                        details={"http_status": res.status_code},
                    )

                if res.status_code != 200:
                    raise ValidationException(
                        message=f"GitHub repository unavailable: Received HTTP {res.status_code} from GitHub API.",
                        details={"http_status": res.status_code},
                    )

                repo_data = res.json()

                # Fetch branches
                branch_res = await client.get(
                    f"{repo_api_url}/branches?per_page=100", headers=headers
                )
                if branch_res.status_code == 200:
                    branch_items = branch_res.json()
                    branches = [b["name"] for b in branch_items if isinstance(b, dict) and "name" in b]

        except httpx.RequestError as req_err:
            logger.warning(f"Direct GitHub API request failed ({req_err}). Attempting git ls-remote fallback...")
            # Fallback to Git CLI ls-remote (works when API rate limits hit or in restricted environments)
            try:
                git_url = f"https://github.com/{owner}/{repo}.git"
                cmd_out = Repo.init().git.ls_remote("--heads", git_url)
                for line in cmd_out.splitlines():
                    parts = line.strip().split("refs/heads/")
                    if len(parts) == 2:
                        branches.append(parts[1])
                repo_data = {
                    "name": repo,
                    "full_name": f"{owner}/{repo}",
                    "description": "Public GitHub Repository",
                    "default_branch": "main" if "main" in branches else (branches[0] if branches else "master"),
                    "stargazers_count": 0,
                    "forks_count": 0,
                    "open_issues_count": 0,
                    "private": False,
                    "clone_url": git_url,
                }
            except Exception as git_fallback_err:
                raise ValidationException(
                    message=f"Repository unavailable: Could not connect to GitHub repository '{owner}/{repo}'. Check network or repository availability.",
                    details={"error": str(git_fallback_err)},
                )

        default_branch = repo_data.get("default_branch", "main")
        if not branches:
            branches = [default_branch]

        selected_branch = (branch or default_branch).strip()

        # Check if requested branch exists
        if selected_branch not in branches:
            raise ValidationException(
                message=f"Branch '{selected_branch}' not found in repository '{owner}/{repo}'. Available branches: {', '.join(branches[:5])}{'...' if len(branches) > 5 else ''}",
                details={"requested_branch": selected_branch, "available_branches": branches},
            )

        # Get latest commit SHA for selected branch
        latest_commit_sha: Optional[str] = None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                commit_res = await client.get(
                    f"{repo_api_url}/commits/{selected_branch}", headers=headers
                )
                if commit_res.status_code == 200:
                    latest_commit_sha = commit_res.json().get("sha")
        except Exception:
            pass

        return GitHubValidateResponse(
            valid=True,
            owner=owner,
            repo=repo,
            full_name=repo_data.get("full_name", f"{owner}/{repo}"),
            default_branch=default_branch,
            branches=branches,
            selected_branch=selected_branch,
            description=repo_data.get("description"),
            stars_count=repo_data.get("stargazers_count", 0),
            forks_count=repo_data.get("forks_count", 0),
            open_issues_count=repo_data.get("open_issues_count", 0),
            is_private=repo_data.get("private", False),
            clone_url=repo_data.get("clone_url", f"https://github.com/{owner}/{repo}.git"),
            language=repo_data.get("language"),
            topics=repo_data.get("topics", []),
            size_kb=repo_data.get("size", 0),
            latest_commit_sha=latest_commit_sha,
            rate_limit_remaining=rate_limit_remaining,
            message=f"Repository '{owner}/{repo}' is valid and ready for cloning/analysis on branch '{selected_branch}'.",
        )

    async def get_repository_status(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> GitHubStatusResponse:
        """
        Inspects local git repository against remote GitHub branch status.
        Detects if local workspace is up to date, behind remote commits, or diverged.
        """
        res = await db.execute(select(Project).where(Project.id == project_id))
        project = res.scalars().first()
        if not project:
            raise EntityNotFoundException(
                entity_type="Project",
                entity_id=project_id,
                message=f"Project with ID '{project_id}' not found",
            )

        if project.source_type != "git":
            return GitHubStatusResponse(
                project_id=project_id,
                is_github_repo=False,
                status="NOT_A_GIT_REPO",
                message="Project was not created from a Git repository.",
            )

        repo_path = Path(project.repository_path)
        if not (repo_path / ".git").exists():
            return GitHubStatusResponse(
                project_id=project_id,
                is_github_repo=True,
                status="UNAVAILABLE",
                error_message="Local Git repository metadata is missing or corrupted.",
                message="Repository unavailable on local disk.",
            )

        try:
            owner, repo_name = self.parse_github_url(project.source_url or "")
        except Exception:
            owner, repo_name = "unknown", "unknown"

        local_commit: str = ""
        current_branch: str = project.branch or "main"
        available_branches: List[str] = []

        try:
            git_repo = Repo(str(repo_path))
            local_commit = git_repo.head.commit.hexsha
            if not git_repo.head.is_detached:
                current_branch = git_repo.active_branch.name

            # Read local and tracking branches
            available_branches = [h.name for h in git_repo.heads]
        except Exception as e:
            return GitHubStatusResponse(
                project_id=project_id,
                is_github_repo=True,
                status="ERROR",
                error_message=f"Could not read local repository: {str(e)}",
            )

        # Check remote commit SHA
        remote_commit: Optional[str] = None
        status = "UP_TO_DATE"
        commits_behind = 0
        message = f"Local workspace is up to date with branch '{current_branch}' at commit {local_commit[:8]}."

        try:
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                c_res = await client.get(
                    f"{self.GITHUB_API_BASE}/repos/{owner}/{repo_name}/commits/{current_branch}",
                    headers=headers,
                )
                if c_res.status_code == 200:
                    remote_commit = c_res.json().get("sha")
        except Exception:
            pass

        # Fallback to git ls-remote if API not reached
        if not remote_commit:
            try:
                ls_out = git_repo.git.ls_remote("origin", f"refs/heads/{current_branch}")
                if ls_out and len(ls_out.split()) > 0:
                    remote_commit = ls_out.split()[0]
            except Exception:
                pass

        if remote_commit and remote_commit != local_commit:
            status = "BEHIND"
            commits_behind = 1
            message = (
                f"Remote branch '{current_branch}' has newer commits (Remote: {remote_commit[:8]}, Local: {local_commit[:8]}). "
                "Use 'Refresh Repository' to pull changes and synchronize documentation."
            )

        return GitHubStatusResponse(
            project_id=project_id,
            is_github_repo=True,
            repository_url=project.source_url,
            owner=owner,
            repo_name=repo_name,
            current_branch=current_branch,
            available_branches=available_branches,
            local_commit_sha=local_commit,
            remote_commit_sha=remote_commit or local_commit,
            status=status,
            commits_behind=commits_behind,
            last_checked_at=datetime.now(timezone.utc),
            message=message,
        )

    async def refresh_repository(
        self,
        project_id: str,
        db: AsyncSession,
        branch: Optional[str] = None,
        force_sync: bool = False,
    ) -> GitHubRefreshResponse:
        """
        Refreshes a GitHub repository by:
        1. Pulling latest commits from remote origin.
        2. Checking out the selected branch if requested.
        3. Detecting commit differences.
        4. Triggering Phase 14 incremental documentation & diagram synchronization.
        """
        res = await db.execute(select(Project).where(Project.id == project_id))
        project = res.scalars().first()
        if not project:
            raise EntityNotFoundException(
                entity_type="Project",
                entity_id=project_id,
                message=f"Project with ID '{project_id}' not found",
            )

        repo_path = Path(project.repository_path)
        if not (repo_path / ".git").exists():
            raise GitCloneException(
                message=f"Project '{project.name}' does not have a valid Git repository on disk.",
                details={"path": str(repo_path)},
            )

        git_repo = Repo(str(repo_path))
        previous_commit_sha = project.last_commit_sha or git_repo.head.commit.hexsha
        target_branch = (branch or project.branch or "main").strip()

        try:
            origin = git_repo.remotes.origin
        except Exception:
            raise GitCloneException(
                message="Remote 'origin' is not configured for this repository.",
                details={"path": str(repo_path)},
            )

        try:
            # Fetch remote heads
            logger.info(f"Fetching latest changes from origin for project {project_id}")
            origin.fetch()

            # Checkout target branch if different
            if not git_repo.head.is_detached and git_repo.active_branch.name != target_branch:
                try:
                    git_repo.git.checkout(target_branch)
                except GitCommandError:
                    # If local branch doesn't exist, checkout from origin tracking branch
                    git_repo.git.checkout("-b", target_branch, f"origin/{target_branch}")

            # Pull latest commits
            try:
                origin.pull(target_branch)
            except GitCommandError as pull_err:
                logger.warning(f"Pull with branch failed, trying default pull: {pull_err}")
                origin.pull()

        except Exception as pull_exc:
            project.sync_status = "FAILED"
            await db.commit()
            raise GitCloneException(
                message=f"Failed to refresh repository from GitHub: {str(pull_exc)}. Manual merge or conflict resolution may be required.",
                details={"error": str(pull_exc)},
            )

        new_commit_sha = git_repo.head.commit.hexsha
        has_new_commits = (new_commit_sha != previous_commit_sha)

        # Trigger Phase 14 Incremental Synchronization
        sync_report = await sync_service.update_documentation_and_sync(
            project_id=project_id,
            db=db,
            force_all=force_sync or has_new_commits,
            regenerate_diagrams=True,
        )

        project.last_commit_sha = new_commit_sha
        project.branch = target_branch
        project.last_analyzed_at = utc_now()
        project.sync_status = "SYNCED"
        await db.commit()
        await db.refresh(project)

        msg = (
            f"Repository refreshed to commit {new_commit_sha[:8]} on branch '{target_branch}'. "
            f"Synchronized {len(sync_report.documentation_updated)} documents and {len(sync_report.diagrams_updated)} diagrams."
            if has_new_commits or force_sync
            else f"Repository '{project.name}' is already up to date at commit {new_commit_sha[:8]}."
        )

        return GitHubRefreshResponse(
            project_id=project_id,
            status="REFRESHED" if (has_new_commits or force_sync) else "UP_TO_DATE",
            previous_commit_sha=previous_commit_sha,
            current_commit_sha=new_commit_sha,
            branch=target_branch,
            new_commits_pulled=1 if has_new_commits else 0,
            files_changed=sync_report.files_changed,
            documentation_updated=[d.model_dump() for d in sync_report.documentation_updated],
            diagrams_updated=[d.model_dump() for d in sync_report.diagrams_updated],
            refreshed_at=datetime.now(timezone.utc),
            message=msg,
        )


github_service = GitHubService()
