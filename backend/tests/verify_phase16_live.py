import sys
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    print("=== Testing Phase 16: Technical Reports & Documentation Export End-to-End ===")
    
    with httpx.Client(timeout=30.0) as client:
        # 1. Fetch system status
        r = client.get(f"{BASE_URL}/system/status")
        assert r.status_code == 200, f"Status check failed: {r.text}"
        print("[OK] System status OK")

        # 2. List projects to find a target project
        r = client.get(f"{BASE_URL}/projects")
        assert r.status_code == 200
        projects = r.json().get("projects", [])
        if not projects:
            print("No project found. Creating a test project...")
            r = client.post(f"{BASE_URL}/projects", json={
                "name": "Phase16 Test Suite Project",
                "description": "Integration testing for technical reports",
                "source_type": "git"
            })
            assert r.status_code == 201, f"Failed to create project: {r.text}"
            project = r.json()
            project_id = project["id"]
        else:
            project_id = projects[0]["id"]
            print(f"Using existing project: {project_id} ({projects[0].get('name')})")

        # 3. Generate FULL_TECHNICAL_REPORT
        print("\n--- Testing POST /reports/generate (FULL_TECHNICAL_REPORT) ---")
        gen_payload = {
            "report_type": "FULL_TECHNICAL_REPORT",
            "title": "Comprehensive Architecture & Engineering Whitepaper",
            "description": "Complete 12-section technical specification",
            "include_diagrams": True
        }
        r = client.post(f"{BASE_URL}/projects/{project_id}/reports/generate", json=gen_payload)
        assert r.status_code in [200, 201], f"Generate failed: {r.status_code} {r.text}"
        report_data = r.json()
        report_id = report_data["id"]
        print(f"[OK] Generated Full Technical Report ID: {report_id}")
        print(f"  Title: {report_data['title']}")
        print(f"  Sections count: {len(report_data['sections'])}")
        
        # Check all 12 sections
        expected_sections = [
            "Executive Summary",
            "Project Overview",
            "Technology Stack",
            "Repository Statistics",
            "Architecture",
            "Major Components",
            "API Summary",
            "Database Structure",
            "Dependency Analysis",
            "Important Flows",
            "Setup and Deployment",
            "Risks and Limitations",
        ]
        actual_titles = [s["title"] for s in report_data["sections"]]
        print(f"  Section titles in report:\n    - " + "\n    - ".join(actual_titles))
        for exp in expected_sections:
            assert any(exp.lower() in t.lower() for t in actual_titles), f"Missing section: {exp}"
        print("[OK] All 12 required sections verified present!")

        # Verify distinction types
        distinction_types = {s["distinction"] for s in report_data["sections"]}
        print(f"  Distinction types present: {distinction_types}")
        assert "detected" in distinction_types, "Missing 'detected' distinction"
        assert "ai_generated" in distinction_types, "Missing 'ai_generated' distinction"
        assert "inferred" in distinction_types, "Missing 'inferred' distinction"
        print("[OK] Detected, AI-generated, and Inferred tags clearly distinguished!")

        # 4. List reports
        print("\n--- Testing GET /reports ---")
        r = client.get(f"{BASE_URL}/projects/{project_id}/reports")
        assert r.status_code == 200
        reports_list = r.json()
        assert len(reports_list) >= 1
        print(f"[OK] Found {len(reports_list)} report(s) in catalog")

        # 5. Export Markdown
        print("\n--- Testing GET /reports/{report_id}/export?format=markdown ---")
        r = client.get(f"{BASE_URL}/projects/{project_id}/reports/{report_id}/export?format=markdown")
        assert r.status_code == 200
        assert "text/markdown" in r.headers.get("content-type", "")
        assert len(r.text) > 200
        assert "Executive Summary" in r.text
        print(f"[OK] Markdown export verified ({len(r.text)} chars)")

        # 6. Export HTML
        print("\n--- Testing GET /reports/{report_id}/export?format=html ---")
        r = client.get(f"{BASE_URL}/projects/{project_id}/reports/{report_id}/export?format=html")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "<!DOCTYPE html>" in r.text
        assert "Executive Summary" in r.text
        print(f"[OK] HTML export verified ({len(r.text)} chars)")

        # 7. Export PDF
        print("\n--- Testing GET /reports/{report_id}/export?format=pdf ---")
        r = client.get(f"{BASE_URL}/projects/{project_id}/reports/{report_id}/export?format=pdf")
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        pdf_bytes = r.content
        assert pdf_bytes.startswith(b"%PDF"), "Response is not a valid PDF binary"
        assert len(pdf_bytes) > 1000
        print(f"[OK] PDF export verified ({len(pdf_bytes)} bytes, starts with %PDF)")

        # 8. Generate another report type (API_DOCUMENTATION)
        print("\n--- Testing POST /reports/generate (API_DOCUMENTATION) ---")
        r = client.post(f"{BASE_URL}/projects/{project_id}/reports/generate", json={
            "report_type": "API_DOCUMENTATION",
            "title": "REST API Reference Manual"
        })
        assert r.status_code in [200, 201]
        api_rep = r.json()
        assert api_rep["report_type"] == "API_DOCUMENTATION"
        print(f"[OK] Generated API_DOCUMENTATION: {api_rep['title']}")

        # Export API doc as PDF
        r = client.get(f"{BASE_URL}/projects/{project_id}/reports/{api_rep['id']}/export?format=pdf")
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
        print(f"[OK] API Documentation PDF export verified ({len(r.content)} bytes)")

    print("\n>>> ALL LIVE END-TO-END TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_tests()
