"""
tests/integration/test_auth_flow.py — End-to-end authentication integration tests

Tests the full flow: register → verify → login → refresh → logout
Uses the async test client against the real FastAPI app with an in-memory DB.
"""
import pytest
import pytest_asyncio


@pytest.mark.asyncio
class TestRegistrationFlow:
    async def test_register_returns_201(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == "newuser@example.com"

    async def test_register_duplicate_email_returns_409(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Already exists from test_user fixture
                "username": "anotheruser",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409

    async def test_register_invalid_password_returns_422(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "username": "validuser",
                "password": "weak",  # Fails password policy
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLoginFlow:
    async def test_login_verified_user_returns_tokens(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        # HttpOnly refresh cookie should be set
        assert "refresh_token" in response.cookies or "set-cookie" in response.headers

    async def test_login_wrong_password_returns_401(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "Whatever123!"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestProtectedRoutes:
    async def test_me_without_token_returns_401(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_with_valid_token_returns_user(self, client, test_user):
        # Login to get token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"},
        )
        token = login_response.json()["data"]["access_token"]

        # Call /me with bearer token
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "test@example.com"
