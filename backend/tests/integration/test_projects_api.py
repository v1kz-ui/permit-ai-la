"""Integration tests for the /api/v1/projects endpoints.

These tests use a real PostgreSQL database (via docker-compose.test.yml) and
verify end-to-end behaviour of the projects API including authorization rules.
"""

import pytest
from fastapi.testclient import TestClient

from app.middleware.auth import get_current_user
from app.models.user import User
from tests.integration.conftest import make_auth_override

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_BASE_PAYLOAD = {
    "address": "1234 Oakwood Ave, Los Angeles, CA 90068",
    "description": "Fire rebuild – single-family residence",
    "original_sqft": 1800.0,
    "proposed_sqft": 1800.0,
    "stories": 1,
}


def _auth_client(test_client: TestClient, user: User) -> TestClient:
    """Temporarily patch the auth dependency so *test_client* acts as *user*."""
    from app.main import app

    app.dependency_overrides[get_current_user] = make_auth_override(user)
    return test_client


def _create_project(client: TestClient, payload: dict | None = None) -> dict:
    body = payload or PROJECT_BASE_PAYLOAD
    resp = client.post("/api/v1/projects", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_project_success(test_client: TestClient, test_user: User):
    _auth_client(test_client, test_user)

    resp = test_client.post("/api/v1/projects", json=PROJECT_BASE_PAYLOAD)

    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["address"] == PROJECT_BASE_PAYLOAD["address"]
    assert data["status"] == "intake"
    assert data["owner_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_list_projects_empty(test_client: TestClient, test_user: User):
    """A freshly registered user has no projects."""
    _auth_client(test_client, test_user)

    resp = test_client.get("/api/v1/projects")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_projects_with_data(test_client: TestClient, test_user: User):
    _auth_client(test_client, test_user)

    _create_project(test_client, {**PROJECT_BASE_PAYLOAD, "address": "100 First St, LA 90001"})
    _create_project(test_client, {**PROJECT_BASE_PAYLOAD, "address": "200 Second St, LA 90002"})

    resp = test_client.get("/api/v1/projects")

    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 2  # may be more if other tests share the session


@pytest.mark.asyncio
async def test_get_project_by_id(test_client: TestClient, test_user: User):
    _auth_client(test_client, test_user)

    address = "555 Maple Dr, Los Angeles, CA 90210"
    created = _create_project(test_client, {**PROJECT_BASE_PAYLOAD, "address": address})
    project_id = created["id"]

    resp = test_client.get(f"/api/v1/projects/{project_id}")

    assert resp.status_code == 200
    assert resp.json()["address"] == address
    assert resp.json()["id"] == project_id


@pytest.mark.asyncio
async def test_get_project_not_found(test_client: TestClient, test_user: User):
    _auth_client(test_client, test_user)

    nil_uuid = "00000000-0000-0000-0000-000000000000"
    resp = test_client.get(f"/api/v1/projects/{nil_uuid}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_project_owner_isolation(
    test_client: TestClient,
    test_user: User,
    test_staff: User,
):
    """User A's project is not visible to User B (homeowner)."""
    from app.main import app
    from app.models.user import User as UserModel
    import uuid

    # Create a second homeowner (User B)
    from tests.integration.conftest import _FakeAuthUser
    import app.schemas.common as sc

    # Inline a second fake homeowner so we don't need a second DB fixture here
    user_b_id = uuid.uuid4()

    class _UserB:
        id          = user_b_id
        email       = f"userb-{user_b_id.hex[:6]}@test.permitai.la"
        name        = "User B"
        role        = sc.UserRole.HOMEOWNER
        angeleno_id = ""

    # Create project as test_user (User A)
    _auth_client(test_client, test_user)
    created = _create_project(test_client)
    project_id = created["id"]

    # Switch to User B
    app.dependency_overrides[get_current_user] = lambda: _UserB()

    resp = test_client.get(f"/api/v1/projects/{project_id}")

    # The API returns 404 for unauthorized access to another user's project
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_staff_can_see_all_projects(
    test_client: TestClient,
    test_user: User,
    test_staff: User,
):
    """Staff role can retrieve any project regardless of owner."""
    # Create project as homeowner
    _auth_client(test_client, test_user)
    created = _create_project(test_client)
    project_id = created["id"]

    # Fetch as staff
    _auth_client(test_client, test_staff)
    resp = test_client.get(f"/api/v1/projects/{project_id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == project_id
