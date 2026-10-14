import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    print("=== Testing Phase 17: Authentication & User Management End-to-End ===")

    with httpx.Client(timeout=30.0) as client:
        # 1. System health check
        r = client.get(f"{BASE_URL}/system/status")
        assert r.status_code == 200
        print("[OK] Backend service online and responsive")

        # 2. Register User 1 (Dev Alice)
        u_suffix = uuid.uuid4().hex[:6]
        alice_email = f"alice_{u_suffix}@docpilot.ai"
        alice_pw = "AlicePass123!"
        print(f"\n--- Testing User Registration: {alice_email} ---")
        r_reg = client.post(f"{BASE_URL}/auth/register", json={
            "email": alice_email,
            "password": alice_pw,
            "full_name": "Alice Senior Architect"
        })
        assert r_reg.status_code == 201, f"Register failed: {r_reg.text}"
        alice_auth = r_reg.json()
        assert "access_token" in alice_auth
        assert alice_auth["user"]["email"] == alice_email.lower()
        assert alice_auth["user"]["full_name"] == "Alice Senior Architect"
        print(f"[OK] Registration succeeded: User ID {alice_auth['user']['id']}")

        # 3. Duplicate registration check
        r_dup = client.post(f"{BASE_URL}/auth/register", json={
            "email": alice_email,
            "password": "AnotherPassword456!",
        })
        assert r_dup.status_code == 400
        print("[OK] Duplicate email rejected with 400 Bad Request")

        # 4. Login with correct credentials
        print(f"\n--- Testing User Login: {alice_email} ---")
        r_login = client.post(f"{BASE_URL}/auth/login", json={
            "email": alice_email,
            "password": alice_pw
        })
        assert r_login.status_code == 200
        alice_token = r_login.json()["access_token"]
        assert len(alice_token.split(".")) == 3
        print(f"[OK] Login succeeded, valid 3-part JWT issued")

        # 5. Login with invalid password
        r_bad_pw = client.post(f"{BASE_URL}/auth/login", json={
            "email": alice_email,
            "password": "WrongPassword999!"
        })
        assert r_bad_pw.status_code == 401
        print("[OK] Invalid password correctly rejected with 401 Unauthorized")

        # 6. Profile inspection: GET /api/v1/auth/me
        print("\n--- Testing GET /auth/me ---")
        alice_headers = {"Authorization": f"Bearer {alice_token}"}
        r_me = client.get(f"{BASE_URL}/auth/me", headers=alice_headers)
        assert r_me.status_code == 200
        assert r_me.json()["email"] == alice_email.lower()
        print(f"[OK] Token introspection verified: {r_me.json()['email']}")

        # 7. Protected route without token
        r_unauth = client.get(f"{BASE_URL}/auth/me")
        assert r_unauth.status_code == 401
        print("[OK] Missing token on protected endpoint rejected with 401 Unauthorized")

        # 8. Register User 2 (Bob)
        bob_email = f"bob_{u_suffix}@docpilot.ai"
        bob_pw = "BobSecret456!"
        r_bob_reg = client.post(f"{BASE_URL}/auth/register", json={
            "email": bob_email,
            "password": bob_pw,
            "full_name": "Bob DevOps Lead"
        })
        assert r_bob_reg.status_code == 201
        bob_token = r_bob_reg.json()["access_token"]
        bob_headers = {"Authorization": f"Bearer {bob_token}"}
        print(f"[OK] Registered second user Bob: {bob_email}")

        # 9. Project Ownership & Multi-tenant Isolation
        print("\n--- Testing Project Ownership & User Isolation ---")
        # Alice creates Project A
        r_proj_a = client.post(f"{BASE_URL}/projects", json={
            "name": f"Alice Vault {u_suffix}",
            "description": "Proprietary financial model",
            "source_type": "git"
        }, headers=alice_headers)
        assert r_proj_a.status_code == 201
        alice_project_id = r_proj_a.json()["id"]
        print(f"[OK] Alice created Project ID: {alice_project_id}")

        # Bob creates Project B
        r_proj_b = client.post(f"{BASE_URL}/projects", json={
            "name": f"Bob Cloud Engine {u_suffix}",
            "description": "Public kubernetes toolchain",
            "source_type": "git"
        }, headers=bob_headers)
        assert r_proj_b.status_code == 201
        bob_project_id = r_proj_b.json()["id"]
        print(f"[OK] Bob created Project ID: {bob_project_id}")

        # Alice lists projects
        r_alice_list = client.get(f"{BASE_URL}/projects", headers=alice_headers)
        assert r_alice_list.status_code == 200
        alice_list_ids = [p["id"] for p in r_alice_list.json()]
        assert alice_project_id in alice_list_ids
        assert bob_project_id not in alice_list_ids
        print("[OK] Alice's project list strictly isolated (does NOT contain Bob's project)")

        # Bob lists projects
        r_bob_list = client.get(f"{BASE_URL}/projects", headers=bob_headers)
        assert r_bob_list.status_code == 200
        bob_list_ids = [p["id"] for p in r_bob_list.json()]
        assert bob_project_id in bob_list_ids
        assert alice_project_id not in bob_list_ids
        print("[OK] Bob's project list strictly isolated (does NOT contain Alice's project)")

        # Bob tries to access Alice's project
        r_cross = client.get(f"{BASE_URL}/projects/{alice_project_id}", headers=bob_headers)
        assert r_cross.status_code == 403
        print("[OK] Cross-tenant access blocked: Bob getting Alice's project returns 403 Forbidden")

        # Bob tries to delete Alice's project
        r_cross_del = client.delete(f"{BASE_URL}/projects/{alice_project_id}", headers=bob_headers)
        assert r_cross_del.status_code == 403
        print("[OK] Cross-tenant deletion blocked: Bob deleting Alice's project returns 403 Forbidden")

        # Alice deletes Alice's project
        r_alice_del = client.delete(f"{BASE_URL}/projects/{alice_project_id}", headers=alice_headers)
        assert r_alice_del.status_code == 204
        print("[OK] Alice successfully deleted Alice's project")

    print("\n>>> ALL PHASE 17 LIVE END-TO-END TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_tests()
