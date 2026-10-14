import io
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import init_db, AsyncSessionLocal
from app.models.project import (
    Project,
    CodeEntity,
    APIEndpoint,
    DatabaseModel,
    DatabaseField,
    DependencyRelationship,
    Diagram,
)


@pytest.mark.asyncio
async def test_phase16_generate_full_technical_report():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "DocPilot Core Microservice",
                "description": "Production technical report test service",
                "source_type": "git",
                "source_url": "https://github.com/docpilot/microservice",
                "branch": "main",
            },
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # Populate sample entities in DB
        async with AsyncSessionLocal() as session:
            p = await session.get(Project, project_id)
            p.stats = {"total_files": 45, "total_lines": 8200}
            p.languages = {"Python": {"files": 35, "lines": 6500, "percent": 79}, "TypeScript": {"files": 10, "lines": 1700, "percent": 21}}
            p.frameworks = ["FastAPI", "SQLAlchemy", "Pydantic"]
            p.infrastructure = ["Docker", "Docker Compose"]
            p.last_commit_sha = "abcdef1234567890"

            # Add Code Entities
            e1 = CodeEntity(
                project_id=project_id,
                file_path="app/services/user_service.py",
                name="UserService",
                entity_type="CLASS",
                start_line=10,
                end_line=95,
                signature="class UserService",
            )
            e2 = CodeEntity(
                project_id=project_id,
                file_path="app/api/auth.py",
                name="login_user",
                entity_type="FUNCTION",
                start_line=20,
                end_line=45,
                signature="async def login_user(creds: LoginRequest)",
            )
            session.add_all([e1, e2])

            # Add API Endpoints
            api1 = APIEndpoint(
                project_id=project_id,
                path="/api/v1/auth/login",
                http_method="POST",
                handler_function="login_user",
                file_path="app/api/auth.py",
                authentication_required=False,
            )
            api2 = APIEndpoint(
                project_id=project_id,
                path="/api/v1/users/profile",
                http_method="GET",
                handler_function="get_profile",
                file_path="app/api/users.py",
                authentication_required=True,
            )
            session.add_all([api1, api2])

            # Add Database Models
            m1 = DatabaseModel(
                project_id=project_id,
                name="User",
                table_name="users",
                file_path="app/models/user.py",
                orm_type="SQLAlchemy",
                start_line=12,
            )
            session.add(m1)
            await session.flush()

            f1 = DatabaseField(
                model_id=m1.id,
                name="id",
                data_type="String(36)",
                is_primary_key=True,
                is_nullable=False,
            )
            f2 = DatabaseField(
                model_id=m1.id,
                name="email",
                data_type="String(255)",
                is_primary_key=False,
                is_nullable=False,
            )
            session.add_all([f1, f2])

            # Add Dependency Relationship
            dep1 = DependencyRelationship(
                project_id=project_id,
                source="app/api/auth.py",
                target="app/services/user_service.py",
                source_type="file",
                target_type="file",
                relationship_type="IMPORTS",
                confidence=0.95,
            )
            session.add(dep1)

            # Add Architecture Diagram
            diag = Diagram(
                project_id=project_id,
                diagram_type="SYSTEM_ARCHITECTURE",
                title="System Architecture Overview",
                mermaid_code="graph TD\n  Client --> API\n  API --> UserService\n  UserService --> DB[(PostgreSQL)]",
            )
            session.add(diag)

            await session.commit()

        # 2. Generate Full Technical Report
        gen_resp = await client.post(
            f"/api/v1/projects/{project_id}/reports/generate",
            json={"report_type": "FULL_TECHNICAL_REPORT"},
        )
        assert gen_resp.status_code == 201
        report_data = gen_resp.json()

        assert report_data["project_id"] == project_id
        assert report_data["report_type"] == "FULL_TECHNICAL_REPORT"
        assert "Full Technical Report" in report_data["title"]
        assert len(report_data["sections"]) == 12

        # Verify all 12 required sections exist
        expected_sections = [
            "1. Executive Summary",
            "2. Project Overview",
            "3. Technology Stack",
            "4. Repository Statistics",
            "5. Architecture",
            "6. Major Components",
            "7. API Summary",
            "8. Database Structure",
            "9. Dependency Analysis",
            "10. Important Flows",
            "11. Setup and Deployment",
            "12. Risks and Limitations",
        ]
        actual_titles = [s["title"] for s in report_data["sections"]]
        for exp in expected_sections:
            assert exp in actual_titles, f"Missing expected section: {exp}"

        # Verify information classification distinctions
        categories = {s["category"] for s in report_data["sections"]}
        assert "detected" in categories
        assert "ai_generated" in categories
        assert "inferred" in categories

        # Verify Markdown contains distinction tags
        md = report_data["markdown_content"]
        assert "Detected from Repository Evidence" in md
        assert "AI-Generated Architecture Explanation" in md
        assert "Inferred Relationship & Dependency Graph" in md

        # Verify evidence citations in markdown
        assert "UserService" in md
        assert "/api/v1/auth/login" in md
        assert "User (`users`)" in md or "`users`" in md


@pytest.mark.asyncio
async def test_phase16_generate_all_report_types():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        create_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "Multi-Report Test Project",
                "source_type": "local",
            },
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        report_types = ["README", "API_DOCUMENTATION", "ARCHITECTURE", "DATABASE", "ONBOARDING"]
        for r_type in report_types:
            resp = await client.post(
                f"/api/v1/projects/{project_id}/reports/generate",
                json={"report_type": r_type},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["report_type"] == r_type
            assert len(data["sections"]) >= 1
            assert len(data["markdown_content"]) > 50


@pytest.mark.asyncio
async def test_phase16_list_and_export_reports():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        create_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "Export Test Suite",
                "source_type": "git",
                "source_url": "https://github.com/docpilot/export-test",
            },
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # Generate a report
        gen_resp = await client.post(
            f"/api/v1/projects/{project_id}/reports/generate",
            json={"report_type": "FULL_TECHNICAL_REPORT", "title": "Enterprise Architecture Audit"},
        )
        assert gen_resp.status_code == 201
        report_id = gen_resp.json()["id"]

        # 1. Test GET /api/v1/projects/{project_id}/reports
        list_resp = await client.get(f"/api/v1/projects/{project_id}/reports")
        assert list_resp.status_code == 200
        reports = list_resp.json()
        assert len(reports) >= 1
        assert any(r["id"] == report_id for r in reports)

        # 2. Test Export Markdown
        exp_md = await client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=markdown")
        assert exp_md.status_code == 200
        assert "text/markdown" in exp_md.headers["content-type"]
        assert 'attachment; filename="' in exp_md.headers["content-disposition"]
        assert exp_md.headers["content-disposition"].endswith('.md"')
        assert exp_md.text.startswith("# Enterprise Architecture Audit")

        # 3. Test Export HTML
        exp_html = await client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=html")
        assert exp_html.status_code == 200
        assert "text/html" in exp_html.headers["content-type"]
        assert 'attachment; filename="' in exp_html.headers["content-disposition"]
        assert exp_html.headers["content-disposition"].endswith('.html"')
        assert "<!DOCTYPE html>" in exp_html.text
        assert "mermaid" in exp_html.text.lower()

        # 4. Test Export PDF
        exp_pdf = await client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=pdf")
        assert exp_pdf.status_code == 200
        assert "application/pdf" in exp_pdf.headers["content-type"]
        assert 'attachment; filename="' in exp_pdf.headers["content-disposition"]
        assert exp_pdf.headers["content-disposition"].endswith('.pdf"')
        # Validate PDF magic header
        assert exp_pdf.content.startswith(b"%PDF-")

        # 5. Test Error Handling
        bad_format = await client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=docx")
        assert bad_format.status_code == 400
        assert "Unsupported export format" in bad_format.json()["error"]["message"]

        not_found_report = await client.get(f"/api/v1/projects/{project_id}/reports/nonexistent-id-999/export")
        assert not_found_report.status_code == 404
