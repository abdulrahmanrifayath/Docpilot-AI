import io
import os
import zipfile
import httpx
from pathlib import Path

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)


def make_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p, c in files_dict.items():
            zf.writestr(p, c)
    buf.seek(0)
    return buf


def run_all_tests():
    print("--- TEST 1: Python Project ZIP Upload ---")
    p1 = client.post("/api/v1/projects", json={"name": "Live Python App", "source_type": "zip"}).json()
    p1_id = p1["id"]
    py_zip = make_zip({
        "src/main.py": "from fastapi import FastAPI\napp = FastAPI()",
        "src/routes/items.py": "def get_items(): return []",
        "src/__pycache__/cache.pyc": "cache",
        "node_modules/x.js": "ignored",
        "README.md": "# Live Python App"
    })
    upload_res = client.post(f"/api/v1/projects/{p1_id}/upload", files={"file": ("python_app.zip", py_zip, "application/zip")})
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    assert upload_res.json()["status"] == "READY"
    files_res1 = client.get(f"/api/v1/projects/{p1_id}/files")
    assert files_res1.status_code == 200
    t1 = files_res1.json()
    print("Python files total:", t1["total_files"], "languages:", t1["language_counts"])
    assert t1["language_counts"].get("Python", 0) >= 2
    assert not any("__pycache__" in f["path"] for f in t1["files"])
    print("-> TEST 1 PASSED")

    print("\n--- TEST 2: TypeScript / JavaScript Project ZIP Upload ---")
    p2 = client.post("/api/v1/projects", json={"name": "Live TS App", "source_type": "zip"}).json()
    p2_id = p2["id"]
    ts_zip = make_zip({
        "src/App.tsx": "export const App = () => <h1>Hello</h1>;",
        "src/utils/api.ts": "export const get = () => {};",
        "src/index.js": "console.log('ready');",
        "package.json": '{"name":"ts-app"}',
        "dist/bundle.js": "built code"
    })
    upload_res2 = client.post(f"/api/v1/projects/{p2_id}/upload", files={"file": ("ts_app.zip", ts_zip, "application/zip")})
    assert upload_res2.status_code == 200
    assert upload_res2.json()["status"] == "READY"
    files_res2 = client.get(f"/api/v1/projects/{p2_id}/files")
    assert files_res2.status_code == 200
    t2 = files_res2.json()
    print("TS/JS files total:", t2["total_files"], "languages:", t2["language_counts"])
    assert t2["language_counts"].get("TypeScript", 0) >= 2
    assert t2["language_counts"].get("JavaScript", 0) >= 1
    print("-> TEST 2 PASSED")

    print("\n--- TEST 3: Public GitHub Repository Clone ---")
    p3 = client.post("/api/v1/projects", json={"name": "GitHub Octocat", "source_type": "github"}).json()
    p3_id = p3["id"]
    clone_res = client.post(f"/api/v1/projects/{p3_id}/clone", json={"url": "https://github.com/octocat/Hello-World"})
    assert clone_res.status_code == 200, f"Clone failed: {clone_res.text}"
    assert clone_res.json()["status"] == "READY"
    files_res3 = client.get(f"/api/v1/projects/{p3_id}/files")
    assert files_res3.status_code == 200
    t3 = files_res3.json()
    print("Cloned repo files count:", t3["total_files"])
    assert t3["total_files"] >= 1
    print("-> TEST 3 PASSED")

    print("\n--- TEST 4: Invalid ZIP Upload ---")
    p4 = client.post("/api/v1/projects", json={"name": "Invalid Zip Test", "source_type": "zip"}).json()
    p4_id = p4["id"]
    bad_buf = io.BytesIO(b"plain text, not a zip archive")
    bad_res = client.post(f"/api/v1/projects/{p4_id}/upload", files={"file": ("corrupt.zip", bad_buf, "application/zip")})
    assert bad_res.status_code == 422
    get_p4 = client.get(f"/api/v1/projects/{p4_id}").json()
    assert get_p4["status"] == "FAILED"
    print("Bad zip handled correctly, project status is FAILED:", get_p4["status_message"])
    print("-> TEST 4 PASSED")

    print("\n--- TEST 5: Invalid GitHub URL ---")
    p5 = client.post("/api/v1/projects", json={"name": "Invalid Git URL Test", "source_type": "github"}).json()
    p5_id = p5["id"]
    bad_git = client.post(f"/api/v1/projects/{p5_id}/clone", json={"url": "https://not-github.com/random/repo"})
    assert bad_git.status_code == 422
    print("Invalid GitHub URL rejected properly:", bad_git.json()["error"]["message"])
    print("-> TEST 5 PASSED")

    print("\n--- TEST 6: Project Deletion & Disk Cleanup ---")
    del_res1 = client.delete(f"/api/v1/projects/{p1_id}")
    assert del_res1.status_code == 204
    del_res2 = client.delete(f"/api/v1/projects/{p2_id}")
    assert del_res2.status_code == 204
    del_res3 = client.delete(f"/api/v1/projects/{p3_id}")
    assert del_res3.status_code == 204
    del_res4 = client.delete(f"/api/v1/projects/{p4_id}")
    assert del_res4.status_code == 204
    del_res5 = client.delete(f"/api/v1/projects/{p5_id}")
    assert del_res5.status_code == 204

    # Verify DB 404
    assert client.get(f"/api/v1/projects/{p1_id}").status_code == 404
    # Verify storage deleted
    p1_disk = Path(f"./storage/repos/{p1_id}")
    assert not p1_disk.exists(), "Project 1 directory was not cleaned up on disk!"
    print("Project deletion cleanly removed database records and disk storage.")
    print("-> TEST 6 PASSED")

    print("\n========================================")
    print("ALL 6 PHASE 2 INTEGRATION TESTS PASSED!")
    print("========================================")


if __name__ == "__main__":
    run_all_tests()
