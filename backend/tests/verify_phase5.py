import io
import zipfile
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)


def make_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p, c in files_dict.items():
            zf.writestr(p, c)
    buf.seek(0)
    return buf


def run_phase5_live_tests():
    print("==================================================")
    print("PHASE 5 LIVE VERIFICATION: DEPENDENCY & RELATIONSHIP ANALYSIS")
    print("==================================================")

    # 1. Create project
    p = client.post(
        "/api/v1/projects",
        json={
            "name": "Live Dependency Graph Verification",
            "description": "Validating AST and Regex import/dependency extraction",
            "source_type": "zip",
        },
    ).json()
    p_id = p["id"]

    sample_zip = make_zip({
        "backend/app/api/auth.py": (
            'from fastapi import APIRouter, Depends\n'
            'from backend.app.services.user_service import UserService\n\n'
            'router = APIRouter()\n\n'
            'def login_route():\n'
            '    service = UserService()\n'
            '    return service.login("admin@example.com")\n'
        ),
        "backend/app/services/user_service.py": (
            'from backend.app.services.base_service import BaseService\n'
            'from backend.app.services.jwt_service import JWTService\n'
            'from backend.app.repositories.user_repo import UserRepository\n\n'
            'class UserService(BaseService):\n'
            '    def __init__(self, repo: UserRepository):\n'
            '        self.repo = repo\n'
            '        self.jwt = JWTService()\n\n'
            '    def login(self, email: str):\n'
            '        return self.jwt.generate_token(email)\n'
        ),
        "backend/app/services/base_service.py": (
            'class BaseService:\n'
            '    """Base service class."""\n'
            '    pass\n'
        ),
        "backend/app/services/jwt_service.py": (
            'import jwt\n\n'
            'class JWTService:\n'
            '    def generate_token(self, email: str) -> str:\n'
            '        return f"token_{email}"\n'
        ),
        "backend/app/repositories/user_repo.py": (
            'from sqlalchemy.orm import Session\n\n'
            'class UserRepository:\n'
            '    def find_user(self, email: str):\n'
            '        return {"email": email}\n'
        ),
    })

    client.post(f"/api/v1/projects/{p_id}/upload", files={"file": ("graph.zip", sample_zip, "application/zip")})

    # 2. Analyze dependencies
    print("\n--- 1. Testing POST /dependencies/analyze ---")
    analyze_res = client.post(f"/api/v1/projects/{p_id}/dependencies/analyze")
    assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
    analyze_data = analyze_res.json()

    print(f"Status: {analyze_data['status']}")
    print(f"Total Nodes: {analyze_data['total_nodes']}")
    print(f"Total Edges: {analyze_data['total_edges']}")
    print(f"Internal Edges: {analyze_data['internal_edges']}")
    print(f"External Edges: {analyze_data['external_edges']}")
    print(f"Duration: {analyze_data['duration_ms']}ms")

    assert analyze_data["status"] == "ANALYZED"
    assert analyze_data["total_nodes"] >= 6
    assert analyze_data["total_edges"] >= 5
    assert analyze_data["internal_edges"] >= 3

    # 3. Query GET /dependencies
    print("\n--- 2. Testing GET /dependencies ---")
    deps_res = client.get(f"/api/v1/projects/{p_id}/dependencies")
    assert deps_res.status_code == 200
    all_deps = deps_res.json()
    print(f"Total dependencies: {all_deps['total_dependencies']}")
    print(f"Counts by type: {all_deps['counts_by_type']}")

    assert "IMPORTS" in all_deps["counts_by_type"]
    assert "EXTENDS" in all_deps["counts_by_type"]
    assert "DEPENDS_ON" in all_deps["counts_by_type"]

    # 4. Query GET /dependencies/graph
    print("\n--- 3. Testing GET /dependencies/graph ---")
    graph_res = client.get(f"/api/v1/projects/{p_id}/dependencies/graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()
    print(f"Graph nodes count: {graph['total_nodes']}")
    print(f"Graph edges count: {graph['total_edges']}")

    labels = [n["label"] for n in graph["nodes"]]
    print(f"Graph node labels: {labels}")
    assert "UserService" in labels
    assert "BaseService" in labels
    assert "JWTService" in labels
    assert "UserRepository" in labels

    # 5. Query GET /dependencies/entity/class:UserService
    print("\n--- 4. Testing GET /dependencies/entity/class:UserService ---")
    ent_res = client.get(f"/api/v1/projects/{p_id}/dependencies/entity/class:UserService")
    assert ent_res.status_code == 200
    ent_data = ent_res.json()
    print(f"Entity: {ent_data['entity_name']}")
    print(f"Total connections: {ent_data['total_dependencies']}")
    print(f"Outgoing: {[e['relationship_type'] + ' -> ' + e['target_name'] for e in ent_data['outgoing_dependencies']]}")
    print(f"Incoming: {[e['source_name'] + ' -> ' + e['relationship_type'] for e in ent_data['incoming_dependencies']]}")

    assert ent_data["total_dependencies"] >= 1

    # Cleanup
    client.delete(f"/api/v1/projects/{p_id}")

    print("\n==================================================")
    print("ALL PHASE 5 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_phase5_live_tests()
