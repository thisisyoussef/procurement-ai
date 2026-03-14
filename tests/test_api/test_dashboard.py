"""Tests for dashboard API project start flow."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import AuthUser, create_access_token
from app.services.project_store import get_legacy_project_dict, reset_project_store_for_tests

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.main import app

client = TestClient(app)


def _auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    token, _ = create_access_token(AuthUser(user_id=user_id, email="test@example.com"))
    return {"Authorization": f"Bearer {token}"}


def setup_function() -> None:
    reset_project_store_for_tests()


def teardown_function() -> None:
    reset_project_store_for_tests()


def test_dashboard_start_project_persists_request_and_redirect_path():
    with patch("app.api.v1.dashboard._run_pipeline_task", new_callable=AsyncMock) as run_pipeline:
        response = client.post(
            "/api/v1/dashboard/projects/start",
            json={
                "description": "Need 500 custom insulated bottles with logo printing.",
                "source": "dashboard_search",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "started"
    assert payload["project_id"]
    assert payload["redirect_path"] == (
        f"/product?projectId={payload['project_id']}&entry=dashboard_search"
    )

    project = get_legacy_project_dict()[payload["project_id"]]
    assert project["title"] == "Need 500 custom insulated bottles with logo printing."
    assert project["product_description"] == "Need 500 custom insulated bottles with logo printing."
    assert project["auto_outreach"] is False
    assert project["status"] == "parsing"
    run_pipeline.assert_awaited_once()


def test_dashboard_start_project_uses_custom_title_and_auto_outreach():
    with patch("app.api.v1.dashboard._run_pipeline_task", new_callable=AsyncMock):
        response = client.post(
            "/api/v1/dashboard/projects/start",
            json={
                "title": "Spring launch bottles",
                "description": "Need 500 insulated bottles, matte black finish, and fast lead time.",
                "auto_outreach": True,
                "source": "dashboard_new",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    project = get_legacy_project_dict()[payload["project_id"]]
    assert project["title"] == "Spring launch bottles"
    assert project["auto_outreach"] is True


def test_dashboard_start_project_rejects_short_description():
    response = client.post(
        "/api/v1/dashboard/projects/start",
        json={"description": "short"},
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    assert get_legacy_project_dict() == {}
