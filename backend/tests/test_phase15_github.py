import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from git import Repo
from httpx import AsyncClient, ASGITransport, Response

from app.main import app
from app.database.session import init_db, AsyncSessionLocal
from app.models.project import Project, Document
from app.services.github_service import github_service


@pytest.mark.asyncio
async def test_phase15_github_url_parsing():
    # Valid formats
    assert github_service.parse_github_url("https://github.com/octocat/Hello-World") == ("octocat", "Hello-World")
    assert github_service.parse_github_url("https://github.com/octocat/Hello-World.git") == ("octocat", "Hello-World")
    assert github_service.parse_github_url("git@github.com:octocat/Hello-World.git") == ("octocat", "Hello-World")
    assert github_service.parse_github_url("octocat/Hello-World") == ("octocat", "Hello-World")

    # Invalid formats
    with pytest.raises(Exception) as exc1:
        github_service.parse_github_url("https://gitlab.com/notgithub/repo")
    assert "Invalid GitHub repository URL" in str(exc1.value)

    with pytest.raises(Exception) as exc2:
        github_service.parse_github_url("")
    assert "cannot be empty" in str(exc2.value)


@pytest.mark.asyncio
async def test_phase15_github_validate_endpoint():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Invalid URL validation
        bad_url_resp = await client.post(
            "/api/v1/github/validate",
            json={"url": "https://notgithub.com/someone/repo"},
        )
        assert bad_url_resp.status_code == 400
        assert "Invalid GitHub repository URL" in bad_url_resp.json()["error"]["message"]

        # 2. Mock GitHub API for valid repository metadata and branch selection
        mock_repo_payload = {
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "description": "My first repository on GitHub!",
            "default_branch": "master",
            "stargazers_count": 2500,
            "forks_count": 1800,
            "open_issues_count": 50,
            "private": False,
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "language": "Python",
            "topics": ["tutorial", "beginner"],
            "size": 120,
        }
        mock_branches_payload = [
            {"name": "master"},
            {"name": "develop"},
            {"name": "feature-test"},
        ]
        mock_commit_payload = {
            "sha": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
        }

        async def mock_get(self_client, url, *args, **kwargs):
            url_str = str(url)
            if url_str.endswith("/branches?per_page=100"):
                return Response(200, json=mock_branches_payload)
            elif "/commits/" in url_str:
                return Response(200, json=mock_commit_payload)
            else:
                return Response(200, json=mock_repo_payload)

        with patch("httpx.AsyncClient.get", new=mock_get):
            # Test default branch selection
            val_resp = await client.post(
                "/api/v1/github/validate",
                json={"url": "https://github.com/octocat/Hello-World"},
            )
            assert val_resp.status_code == 200
            val_data = val_resp.json()
            assert val_data["valid"] is True
            assert val_data["owner"] == "octocat"
            assert val_data["repo"] == "Hello-World"
            assert val_data["default_branch"] == "master"
            assert val_data["selected_branch"] == "master"
            assert "develop" in val_data["branches"]
            assert val_data["stars_count"] == 2500
            assert val_data["latest_commit_sha"] == "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"

            # Test specific branch selection: "develop"
            val_branch_resp = await client.post(
                "/api/v1/github/validate",
                json={"url": "https://github.com/octocat/Hello-World", "branch": "develop"},
            )
            assert val_branch_resp.status_code == 200
            assert val_branch_resp.json()["selected_branch"] == "develop"

            # Test branch not found error message
            val_bad_branch = await client.post(
                "/api/v1/github/validate",
                json={"url": "https://github.com/octocat/Hello-World", "branch": "non_existent_branch"},
            )
            assert val_bad_branch.status_code == 400
            assert "Branch 'non_existent_branch' not found in repository" in val_bad_branch.json()["error"]["message"]

        # 3. Test Repository unavailable (HTTP 404 from GitHub)
        async def mock_404(self_client, url, *args, **kwargs):
            return Response(404, json={"message": "Not Found"})

        with patch("httpx.AsyncClient.get", new=mock_404):
            not_found_resp = await client.post(
                "/api/v1/github/validate",
                json={"url": "https://github.com/octocat/nonexistent-repo-999"},
            )
            assert not_found_resp.status_code == 400
            assert "Repository unavailable or not found" in not_found_resp.json()["error"]["message"]

        # 4. Test Rate limit exceeded (HTTP 403 / 429)
        async def mock_403_rate_limit(self_client, url, *args, **kwargs):
            return Response(
                403,
                headers={"x-ratelimit-remaining": "0"},
                json={"message": "API rate limit exceeded"},
            )

        with patch("httpx.AsyncClient.get", new=mock_403_rate_limit):
            rate_limit_resp = await client.post(
                "/api/v1/github/validate",
                json={"url": "https://github.com/octocat/Hello-World"},
            )
            assert rate_limit_resp.status_code == 400
            assert "rate limit exceeded" in rate_limit_resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_phase15_github_status_and_refresh_e2e():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a local Git remote and clone setup
        origin_temp = Path(tempfile.mkdtemp(prefix="docpilot_remote_origin_"))
        local_temp = Path(tempfile.mkdtemp(prefix="docpilot_local_clone_"))

        try:
            # 1. Setup origin bare repo with an initial commit
            init_work_dir = Path(tempfile.mkdtemp(prefix="docpilot_init_work_"))
            try:
                init_repo = Repo.init(str(init_work_dir))
                with init_repo.config_writer() as config:
                    config.set_value("user", "name", "GitHub Test")
                    config.set_value("user", "email", "test@github.com")

                (init_work_dir / "app.py").write_text("def run():\n    return 'v1'\n", encoding="utf-8")
                (init_work_dir / "README.md").write_text("# Project v1\nInitial content\n", encoding="utf-8")
                init_repo.index.add(["app.py", "README.md"])
                init_commit = init_repo.index.commit("Initial v1 release")
                init_commit_sha = init_commit.hexsha

                # Clone from init_work_dir to local_temp as if cloned from remote
                local_repo = Repo.clone_from(str(init_work_dir), str(local_temp))
            finally:
                shutil.rmtree(init_work_dir, ignore_errors=True)

            # 2. Register project in database
            create_resp = await client.post(
                "/api/v1/projects",
                json={
                    "name": "GitHub Phase 15 Project",
                    "description": "Public GitHub integration test",
                    "source_type": "git",
                    "source_url": "https://github.com/octocat/Hello-World",
                    "branch": "main",
                },
            )
            assert create_resp.status_code == 201
            project_id = create_resp.json()["id"]

            async with AsyncSessionLocal() as session:
                p = await session.get(Project, project_id)
                p.repository_path = str(local_temp)
                p.last_commit_sha = init_commit_sha
                p.branch = "main"
                p.status = "READY"
                await session.commit()

            # Create an initial document
            async with AsyncSessionLocal() as session:
                doc = Document(
                    project_id=project_id,
                    document_type="PROJECT_OVERVIEW",
                    title="GitHub Integration Overview",
                    content="# Initial Overview\nContent v1",
                    version=1,
                    target_path="app.py",
                )
                session.add(doc)
                await session.commit()

            # 3. Test GET /api/v1/projects/{project_id}/github/status
            status_resp = await client.get(f"/api/v1/projects/{project_id}/github/status")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["is_github_repo"] is True
            assert status_data["local_commit_sha"] == init_commit_sha
            assert status_data["owner"] == "octocat"
            assert status_data["repo_name"] == "Hello-World"

            # 4. Test POST /api/v1/projects/{project_id}/github/refresh (Idempotent Up-to-date)
            # When remote has no new commits, status should be UP_TO_DATE
            with patch("git.remote.Remote.pull", return_value=[]), patch("git.remote.Remote.fetch", return_value=[]):
                refresh_resp = await client.post(
                    f"/api/v1/projects/{project_id}/github/refresh",
                    json={"force_sync": False},
                )
                assert refresh_resp.status_code == 200
                ref_data = refresh_resp.json()
                assert ref_data["status"] == "UP_TO_DATE"
                assert ref_data["current_commit_sha"] == init_commit_sha

            # 5. Test POST /api/v1/projects/{project_id}/github/refresh with force_sync=True
            with patch("git.remote.Remote.pull", return_value=[]), patch("git.remote.Remote.fetch", return_value=[]):
                refresh_force_resp = await client.post(
                    f"/api/v1/projects/{project_id}/github/refresh",
                    json={"force_sync": True},
                )
                assert refresh_force_resp.status_code == 200
                force_data = refresh_force_resp.json()
                assert force_data["status"] == "REFRESHED"
                assert len(force_data["documentation_updated"]) >= 1

            # 6. Verify non-git project handling
            non_git_create = await client.post(
                "/api/v1/projects",
                json={
                    "name": "Non Git Project",
                    "source_type": "zip",
                },
            )
            assert non_git_create.status_code == 201
            non_git_id = non_git_create.json()["id"]

            non_git_status = await client.get(f"/api/v1/projects/{non_git_id}/github/status")
            assert non_git_status.status_code == 200
            assert non_git_status.json()["is_github_repo"] is False
            assert non_git_status.json()["status"] == "NOT_A_GIT_REPO"

        finally:
            shutil.rmtree(origin_temp, ignore_errors=True)
            shutil.rmtree(local_temp, ignore_errors=True)
