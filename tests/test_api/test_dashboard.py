"""Tests for dashboard API project start flow."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.v1.dashboard import PROJECT_START_FAILURE_DETAIL
from app.core.auth import AuthUser, create_access_token
from app.services.project_store import (
    StoreUnavailableError,
    get_legacy_project_dict,
    reset_project_store_for_tests,
)

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


def test_dashboard_start_project_internal_error_returns_safe_message():
    with patch("app.api.v1.dashboard.get_project_store") as get_store:
        store = AsyncMock()
        store.create_project.side_effect = RuntimeError("sensitive failure details")
        get_store.return_value = store

        response = client.post(
            "/api/v1/dashboard/projects/start",
            json={
                "description": "Need 500 custom insulated bottles with logo printing.",
                "source": "dashboard_search",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == PROJECT_START_FAILURE_DETAIL
    assert "sensitive failure details" not in payload["detail"]


def test_dashboard_start_project_store_unavailable_preserves_503_mapping():
    with patch("app.api.v1.dashboard.get_project_store") as get_store:
        store = AsyncMock()
        store.create_project.side_effect = StoreUnavailableError("memory backend offline")
        get_store.return_value = store

        response = client.post(
            "/api/v1/dashboard/projects/start",
            json={
                "description": "Need 500 custom insulated bottles with logo printing.",
                "source": "dashboard_search",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 503
    assert "Project store unavailable: memory backend offline" == response.json()["detail"]


def test_dashboard_summary_filters_projects_by_single_status():
    projects = get_legacy_project_dict()
    projects["proj-dash-1"] = {
        "id": "proj-dash-1",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Parsing project",
        "product_description": "Need forged aluminum enclosures.",
        "status": "parsing",
        "current_stage": "parsing",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-2"] = {
        "id": "proj-dash-2",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Completed project",
        "product_description": "Need stainless precision fittings.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?status=parsing", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-1"]
    assert payload["projects"][0]["status"] == "parsing"


def test_dashboard_summary_filters_projects_by_multiple_statuses():
    projects = get_legacy_project_dict()
    projects["proj-dash-3"] = {
        "id": "proj-dash-3",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Failed project",
        "product_description": "Need molded caps.",
        "status": "failed",
        "current_stage": "failed",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-4"] = {
        "id": "proj-dash-4",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Discovery project",
        "product_description": "Need custom cartons.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-5"] = {
        "id": "proj-dash-5",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete project",
        "product_description": "Need custom sleeves.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get(
        "/api/v1/dashboard/summary?status=complete&status=failed",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    statuses = sorted(project["status"] for project in payload["projects"])
    assert statuses == ["complete", "failed"]


def test_dashboard_summary_rejects_invalid_status_filter():
    projects = get_legacy_project_dict()
    projects["proj-dash-6"] = {
        "id": "proj-dash-6",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Any project",
        "product_description": "Need die-cut inserts.",
        "status": "parsing",
        "current_stage": "parsing",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?status=not-real", headers=_auth_headers())
    assert response.status_code == 422
    assert "Invalid status filter value(s): not-real" in response.json()["detail"]
