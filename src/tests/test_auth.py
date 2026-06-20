"""
Integration tests for Auth endpoints.
Tests register, login, logout, and /me with the full FastAPI test client.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import get_db, Base


from sqlalchemy.pool import StaticPool

# ── Test database (in-memory SQLite) ─────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create all tables in in-memory DB for the test session."""
    from backend.app.models import user, poem, generation, download, activity_log, ai_provider_log  # noqa: F401
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client):
        r = client.post("/api/v1/auth/register", json={
            "name": "Test User", "email": "test@example.com", "password": "password123"
        })
        assert r.status_code == 201
        data = r.json()
        assert "access_token" in data
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"

    def test_register_duplicate_email(self, client):
        r = client.post("/api/v1/auth/register", json={
            "name": "Another", "email": "test@example.com", "password": "password123"
        })
        assert r.status_code == 409
        assert "already exists" in r.json()["detail"].lower()

    def test_register_short_password(self, client):
        r = client.post("/api/v1/auth/register", json={
            "name": "User", "email": "short@example.com", "password": "abc"
        })
        assert r.status_code == 422  # Validation error

    def test_register_invalid_email(self, client):
        r = client.post("/api/v1/auth/register", json={
            "name": "User", "email": "not-an-email", "password": "password123"
        })
        assert r.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "password123"
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "wrongpassword"
        })
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com", "password": "password123"
        })
        assert r.status_code == 401


class TestProtectedEndpoints:
    @pytest.fixture
    def auth_headers(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "password123"
        })
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_me_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "test@example.com"
        assert "password" not in str(data).lower()

    def test_me_unauthenticated(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401

    def test_logout(self, client, auth_headers):
        r = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert r.status_code == 200
        assert "logged out" in r.json()["message"].lower()


class TestHealthAndPublic:
    def test_health_check(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_gallery_public(self, client):
        r = client.get("/api/v1/gallery")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_sd_status_public(self, client):
        r = client.get("/api/v1/sd-status")
        assert r.status_code == 200
        data = r.json()
        assert "ready" in data
        assert "loading" in data
