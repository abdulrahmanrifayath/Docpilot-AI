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


def run_phase8_live_tests():
    print("=========================================================")
    print("PHASE 8 LIVE VERIFICATION: UNIFIED PROJECT KNOWLEDGE GRAPH")
    print("=========================================================")

    # 1. Create project
    p = client.post(
        "/api/v1/projects",
        json={
            "name": "Live Knowledge Graph Project",
            "description": "Unified knowledge graph integration validation",
            "source_type": "zip",
        },
    ).json()
    p_id = p["id"]

    sample_zip = make_zip({
        "backend/app/main.py": (
            'from fastapi import FastAPI\n'
            'from backend.app.routers import users\n\n'
            'app = FastAPI(title="Demo")\n'
            'app.include_router(users.router)\n'
        ),
        "backend/app/routers/users.py": (
            'from fastapi import APIRouter, Depends\n'
            'from backend.app.services.user_service import UserService\n'
            'from backend.app.models.user import User\n\n'
            'router = APIRouter(prefix="/api/v1/users", tags=["Users"])\n\n'
            '@router.get("", summary="List users")\n'
            'def list_users(service: UserService = Depends()):\n'
            '    return service.get_all()\n'
        ),
        "backend/app/services/user_service.py": (
            'from backend.app.models.user import User\n\n'
            'class UserService:\n'
            '    def get_all(self):\n'
            '        return []\n'
        ),
        "backend/app/models/user.py": (
            'from sqlalchemy import String, Integer\n'
            'from sqlalchemy.orm import Mapped, mapped_column\n'
            'from backend.app.database.base import Base\n\n'
            'class User(Base):\n'
            '    __tablename__ = "users"\n'
            '    id: Mapped[int] = mapped_column(primary_key=True)\n'
            '    email: Mapped[str] = mapped_column(String(255), unique=True)\n'
        ),
    })

    client.post(f"/api/v1/projects/{p_id}/upload", files={"file": ("kg_project.zip", sample_zip, "application/zip")})

    # 2. Trigger Knowledge Graph Build
    print("\n--- 1. Testing POST /knowledge/build ---")
    build_res = client.post(f"/api/v1/projects/{p_id}/knowledge/build")
    assert build_res.status_code == 200, f"Build failed: {build_res.text}"
    build_data = build_res.json()

    print(f"Status: {build_data['status']}")
    print(f"Total Nodes: {build_data['total_nodes']}")
    print(f"Total Edges: {build_data['total_edges']}")
    print(f"Counts by Category: {build_data['counts_by_category']}")
    print(f"Duration: {build_data['duration_ms']}ms")

    assert build_data["status"] == "BUILT"
    assert build_data["total_nodes"] >= 6
    assert build_data["total_edges"] >= 4

    # 3. Query GET /knowledge/graph
    print("\n--- 2. Testing GET /knowledge/graph ---")
    graph_res = client.get(f"/api/v1/projects/{p_id}/knowledge/graph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    print(f"Retrieved {graph_data['total_nodes']} nodes and {graph_data['total_edges']} edges")

    for n in graph_data["nodes"][:8]:
        print(f"  • Node: [{n['category']}] {n['name']} (Key: {n['node_key']}, in={n['in_degree']}, out={n['out_degree']})")

    for e in graph_data["edges"][:8]:
        print(f"  -> Edge: {e['source']} -[{e['relationship']}]-> {e['target']}")

    # 4. Filter by categories
    print("\n--- 3. Testing GET /knowledge/graph?categories=API,DATABASE_TABLE ---")
    cat_res = client.get(f"/api/v1/projects/{p_id}/knowledge/graph", params={"categories": "API,DATABASE_TABLE"})
    assert cat_res.status_code == 200
    cat_data = cat_res.json()
    print(f"Filtered nodes count: {len(cat_data['nodes'])}")
    assert all(n["category"] in ["API", "DATABASE_TABLE"] for n in cat_data["nodes"])

    # 5. Query Entity Knowledge
    print("\n--- 4. Testing GET /knowledge/entity/{id} ---")
    api_node = next(n for n in graph_data["nodes"] if n["category"] == "API")
    entity_res = client.get(f"/api/v1/projects/{p_id}/knowledge/entity/{api_node['id']}")
    assert entity_res.status_code == 200
    detail = entity_res.json()
    print(f"Entity detail verified: [{detail['node']['category']}] {detail['node']['name']}")
    print(f"  Upstream Callers: {[u['name'] for u in detail['upstream_callers']]}")
    print(f"  Downstream Dependencies: {[d['name'] for d in detail['downstream_dependencies']]}")
    print(f"  Connected Database Tables: {[t['name'] for t in detail['connected_database_tables']]}")

    # 6. Focus Mode Query
    print("\n--- 5. Testing GET /knowledge/graph?focus_node_id=...&depth=1 ---")
    focus_res = client.get(f"/api/v1/projects/{p_id}/knowledge/graph", params={"focus_node_id": api_node["id"], "depth": 1})
    assert focus_res.status_code == 200
    focus_data = focus_res.json()
    print(f"Focus 1-hop sub-graph: {focus_data['total_nodes']} nodes, {focus_data['total_edges']} edges")
    assert any(n["id"] == api_node["id"] for n in focus_data["nodes"])

    # Cleanup
    client.delete(f"/api/v1/projects/{p_id}")

    print("\n=========================================================")
    print("ALL PHASE 8 KNOWLEDGE GRAPH TESTS PASSED SUCCESSFULLY!")
    print("=========================================================")


if __name__ == "__main__":
    run_phase8_live_tests()
