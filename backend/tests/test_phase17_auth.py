import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_user_registration_and_validation():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"developer_reg_{pytest.importorskip('uuid').uuid4().hex[:8]}@docpilot.ai"

        # 1. Valid registration
        res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "SecurePassword123!",
                "full_name": "Test Senior Architect",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == unique_email.lower()
        assert data["user"]["full_name"] == "Test Senior Architect"
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

        # 2. Duplicate registration fails
        dup_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "AnotherPassword456!",
                "full_name": "Duplicate User",
            },
        )
        assert dup_res.status_code == 400
        assert "already registered" in dup_res.text.lower()

        # 3. Short password fails
        short_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"short_{unique_email}",
                "password": "123",
            },
        )
        assert short_res.status_code in [400, 422]

        # 4. Invalid email format fails
        invalid_email_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email-string",
                "password": "SecurePassword123!",
            },
        )
        assert invalid_email_res.status_code == 400


@pytest.mark.asyncio
async def test_user_login_and_auth_me():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"login_user_{pytest.importorskip('uuid').uuid4().hex[:8]}@docpilot.ai"
        password = "ValidPassword987!"

        # Register first
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Login Tester",
            },
        )
        assert reg_res.status_code == 201

        # 1. Successful login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert login_res.status_code == 200
        auth_data = login_res.json()
        token = auth_data["access_token"]
        assert len(token.split(".")) == 3  # Valid JWT format

        # 2. Login with wrong password
        wrong_pw_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "WrongPassword!",
            },
        )
        assert wrong_pw_res.status_code == 401
        assert "invalid email or password" in wrong_pw_res.text.lower()

        # 3. Login with nonexistent user
        no_user_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent_404@docpilot.ai",
                "password": password,
            },
        )
        assert no_user_res.status_code == 401

        # 4. GET /api/v1/auth/me with valid Bearer token
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == email.lower()
        assert me_data["full_name"] == "Login Tester"

        # 5. GET /api/v1/auth/me with missing token
        unauth_res = await client.get("/api/v1/auth/me")
        assert unauth_res.status_code == 401

        # 6. GET /api/v1/auth/me with invalid token
        invalid_tok_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert invalid_tok_res.status_code == 401


@pytest.mark.asyncio
async def test_project_ownership_and_user_isolation():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register User A (Alice)
        alice_email = f"alice_{pytest.importorskip('uuid').uuid4().hex[:8]}@docpilot.ai"
        r_alice = await client.post(
            "/api/v1/auth/register",
            json={"email": alice_email, "password": "AlicePassword123!", "full_name": "Alice Engineer"},
        )
        alice_token = r_alice.json()["access_token"]
        alice_headers = {"Authorization": f"Bearer {alice_token}"}

        # Register User B (Bob)
        bob_email = f"bob_{pytest.importorskip('uuid').uuid4().hex[:8]}@docpilot.ai"
        r_bob = await client.post(
            "/api/v1/auth/register",
            json={"email": bob_email, "password": "BobPassword123!", "full_name": "Bob DevOps"},
        )
        bob_token = r_bob.json()["access_token"]
        bob_headers = {"Authorization": f"Bearer {bob_token}"}

        # Alice creates Project A
        p_alice = await client.post(
            "/api/v1/projects",
            json={"name": "Alice Secret Project", "source_type": "git"},
            headers=alice_headers,
        )
        assert p_alice.status_code == 201
        alice_project_id = p_alice.json()["id"]

        # Bob creates Project B
        p_bob = await client.post(
            "/api/v1/projects",
            json={"name": "Bob Public Project", "source_type": "git"},
            headers=bob_headers,
        )
        assert p_bob.status_code == 201
        bob_project_id = p_bob.json()["id"]

        # Alice lists projects -> must contain Alice's project, but NOT Bob's
        alice_list = await client.get("/api/v1/projects", headers=alice_headers)
        assert alice_list.status_code == 200
        alice_project_ids = [p["id"] for p in alice_list.json()]
        assert alice_project_id in alice_project_ids
        assert bob_project_id not in alice_project_ids

        # Bob lists projects -> must contain Bob's project, but NOT Alice's
        bob_list = await client.get("/api/v1/projects", headers=bob_headers)
        assert bob_list.status_code == 200
        bob_project_ids = [p["id"] for p in bob_list.json()]
        assert bob_project_id in bob_project_ids
        assert alice_project_id not in bob_project_ids

        # Alice accesses Alice's project -> 200 OK
        res_alice_self = await client.get(f"/api/v1/projects/{alice_project_id}", headers=alice_headers)
        assert res_alice_self.status_code == 200

        # Bob tries to access Alice's project -> 403 Forbidden!
        res_bob_cross = await client.get(f"/api/v1/projects/{alice_project_id}", headers=bob_headers)
        assert res_bob_cross.status_code == 403
        assert "permission" in res_bob_cross.text.lower() or "forbidden" in res_bob_cross.text.lower()

        # Bob tries to delete Alice's project -> 403 Forbidden!
        res_bob_del = await client.delete(f"/api/v1/projects/{alice_project_id}", headers=bob_headers)
        assert res_bob_del.status_code == 403

        # Alice deletes Alice's project -> 204 No Content
        res_alice_del = await client.delete(f"/api/v1/projects/{alice_project_id}", headers=alice_headers)
        assert res_alice_del.status_code == 204
