import os
import shutil
import tempfile
from pathlib import Path
import pytest
from git import Repo
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.session import init_db, AsyncSessionLocal
from app.models.project import Project, Document, DocumentVersion, ChangeRecord


@pytest.mark.asyncio
async def test_phase14_change_detection_and_documentation_sync_e2e():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup a real local Git repository in a temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="docpilot_git_test_"))
        try:
            repo = Repo.init(str(temp_dir))
            # Configure git author for commits
            with repo.config_writer() as config:
                config.set_value("user", "name", "DocPilot Test")
                config.set_value("user", "email", "test@docpilot.ai")

            # Create initial source files
            main_py = temp_dir / "main.py"
            main_py.write_text(
                'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/health")\ndef health():\n    return {"status": "ok"}\n',
                encoding="utf-8",
            )
            models_py = temp_dir / "models.py"
            models_py.write_text(
                'from sqlalchemy import Column, String\nfrom sqlalchemy.orm import declarative_base\nBase = declarative_base()\n\nclass User(Base):\n    __tablename__ = "users"\n    id = Column(String, primary_key=True)\n',
                encoding="utf-8",
            )
            old_tool_py = temp_dir / "temp_util.py"
            old_tool_py.write_text('def temp_helper():\n    return 42\n', encoding="utf-8")
            readme_md = temp_dir / "README.md"
            readme_md.write_text("# Test Repo\nInitial readme documentation.\n", encoding="utf-8")

            # Initial git commit
            repo.index.add(["main.py", "models.py", "temp_util.py", "README.md"])
            initial_commit = repo.index.commit("Initial commit")
            initial_commit_sha = initial_commit.hexsha

            # 2. Register project in DocPilot API
            create_resp = await client.post(
                "/api/v1/projects",
                json={
                    "name": "Phase 14 Git Sync Project",
                    "description": "Git repository tracking commit changes",
                    "source_type": "git",
                },
            )
            assert create_resp.status_code == 201
            project_id = create_resp.json()["id"]

            # Set repository path and initial commit SHA in DB
            async with AsyncSessionLocal() as session:
                p = await session.get(Project, project_id)
                p.repository_path = str(temp_dir)
                p.last_commit_sha = initial_commit_sha
                p.status = "READY"
                await session.commit()

            # Run initial scan, parse, api discovery, and docs generation
            scan_resp = await client.post(f"/api/v1/projects/{project_id}/scan")
            assert scan_resp.status_code == 200

            parse_resp = await client.post(f"/api/v1/projects/{project_id}/parse")
            assert parse_resp.status_code == 200

            api_resp = await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
            assert api_resp.status_code == 200

            db_resp = await client.post(f"/api/v1/projects/{project_id}/database/analyze")
            assert db_resp.status_code == 200

            diag_resp = await client.post(f"/api/v1/projects/{project_id}/diagrams/generate")
            assert diag_resp.status_code == 200

            # Create initial documentation records
            async with AsyncSessionLocal() as session:
                init_doc = Document(
                    project_id=project_id,
                    document_type="PROJECT_OVERVIEW",
                    title="Phase 14 Project Overview",
                    content="# Project Overview\nBaseline documentation content before changes.",
                    version=1,
                    target_path="main.py",
                )
                session.add(init_doc)
                await session.commit()

            # -------------------------------------------------------------
            # TEST A: Verify NO CHANGES initially
            # -------------------------------------------------------------
            check_initial = await client.post(f"/api/v1/projects/{project_id}/changes/check")
            assert check_initial.status_code == 200
            check_init_data = check_initial.json()
            assert check_init_data["has_changes"] is False
            assert check_init_data["total_files_changed"] == 0

            # -------------------------------------------------------------
            # TEST B: Introduce Repository Changes (Add, Modify, Delete)
            # -------------------------------------------------------------
            # 1. Modify main.py (add a new endpoint)
            main_py.write_text(
                'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/health")\ndef health():\n    return {"status": "ok"}\n\n@app.post("/users")\ndef create_user():\n    return {"id": "new"}\n',
                encoding="utf-8",
            )
            # 2. Add new file service.py
            service_py = temp_dir / "service.py"
            service_py.write_text(
                "class UserService:\n    def get_user(self, user_id: str):\n        return {'user_id': user_id}\n",
                encoding="utf-8",
            )
            # 3. Delete temp_util.py
            if old_tool_py.exists():
                old_tool_py.unlink()

            # Commit to git to create second commit SHA
            repo.index.add(["main.py", "service.py"])
            repo.index.remove(["temp_util.py"])
            second_commit = repo.index.commit("Add UserService, new endpoint, delete temp_util")
            second_commit_sha = second_commit.hexsha
            assert second_commit_sha != initial_commit_sha

            # -------------------------------------------------------------
            # TEST C: Call POST /api/v1/projects/{project_id}/changes/check
            # -------------------------------------------------------------
            check_resp = await client.post(f"/api/v1/projects/{project_id}/changes/check")
            assert check_resp.status_code == 200
            check_data = check_resp.json()

            assert check_data["has_changes"] is True
            assert check_data["previous_commit_sha"] == initial_commit_sha
            assert check_data["current_commit_sha"] == second_commit_sha
            assert "main.py" in check_data["files_modified"]
            assert "service.py" in check_data["files_added"]
            assert "temp_util.py" in check_data["files_deleted"]
            assert check_data["total_files_changed"] >= 3

            # -------------------------------------------------------------
            # TEST D: Call POST /api/v1/projects/{project_id}/documentation/update
            # -------------------------------------------------------------
            update_resp = await client.post(
                f"/api/v1/projects/{project_id}/documentation/update",
                json={"force_all": False, "regenerate_diagrams": True},
            )
            assert update_resp.status_code == 200
            update_data = update_resp.json()

            assert update_data["status"] == "SYNCED"
            assert update_data["previous_commit_sha"] == initial_commit_sha
            assert update_data["current_commit_sha"] == second_commit_sha
            assert "service.py" in update_data["files_changed"]["added"]
            assert "main.py" in update_data["files_changed"]["modified"]
            assert "temp_util.py" in update_data["files_changed"]["deleted"]

            # Verify documentation was updated and version incremented
            docs_updated = update_data["documentation_updated"]
            assert len(docs_updated) >= 1
            overview_update = next((d for d in docs_updated if d["document_type"] == "PROJECT_OVERVIEW"), None)
            assert overview_update is not None
            assert overview_update["version"] == 2
            assert overview_update["previous_version"] == 1

            # -------------------------------------------------------------
            # TEST E: Verify Database State & Version History Archiving
            # -------------------------------------------------------------
            async with AsyncSessionLocal() as session:
                # 1. Project commit SHA updated
                p_check = await session.get(Project, project_id)
                assert p_check.last_commit_sha == second_commit_sha
                assert p_check.sync_status == "SYNCED"

                # 2. Document record is at version 2
                doc_check = (
                    await session.execute(
                        select(Document).where(
                            Document.project_id == project_id,
                            Document.document_type == "PROJECT_OVERVIEW",
                        )
                    )
                ).scalars().first()
                assert doc_check.version == 2

                # 3. DocumentVersion archive has version 1 preserved
                v_archive = (
                    await session.execute(
                        select(DocumentVersion).where(
                            DocumentVersion.document_id == doc_check.id,
                            DocumentVersion.version == 1,
                        )
                    )
                ).scalars().first()
                assert v_archive is not None
                assert v_archive.version == 1
                assert "Baseline documentation content" in v_archive.content
                assert v_archive.commit_sha == initial_commit_sha

                # 4. ChangeRecord stored
                record_check = (
                    await session.execute(
                        select(ChangeRecord).where(ChangeRecord.project_id == project_id)
                    )
                ).scalars().first()
                assert record_check is not None
                assert record_check.status == "SYNCED"
                assert record_check.previous_commit_sha == initial_commit_sha
                assert record_check.current_commit_sha == second_commit_sha

            # -------------------------------------------------------------
            # TEST F: Call GET /api/v1/projects/{project_id}/changes
            # -------------------------------------------------------------
            changes_list_resp = await client.get(f"/api/v1/projects/{project_id}/changes")
            assert changes_list_resp.status_code == 200
            history = changes_list_resp.json()
            assert isinstance(history, list)
            assert len(history) >= 1
            latest_record = history[0]
            assert latest_record["status"] == "SYNCED"
            assert latest_record["current_commit_sha"] == second_commit_sha
            assert "main.py" in latest_record["files_changed"]["modified"]

            # -------------------------------------------------------------
            # TEST G: Subsequent check is clean (idempotency)
            # -------------------------------------------------------------
            clean_check = await client.post(f"/api/v1/projects/{project_id}/changes/check")
            assert clean_check.status_code == 200
            clean_data = clean_check.json()
            assert clean_data["has_changes"] is False

            no_op_sync = await client.post(
                f"/api/v1/projects/{project_id}/documentation/update",
                json={"force_all": False},
            )
            assert no_op_sync.status_code == 200
            assert no_op_sync.json()["status"] == "NO_CHANGES"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
