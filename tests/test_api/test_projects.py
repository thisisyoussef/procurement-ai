"""Tests for the projects API endpoints."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import AuthUser, create_access_token

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.main import app
from app.api.v1.projects import (
    PROJECT_ANSWER_FAILURE_DETAIL,
    PROJECT_RETROSPECTIVE_ALREADY_SUBMITTED_DETAIL,
    PROJECT_START_FAILURE_DETAIL,
    _projects,
)

client = TestClient(app)


def _auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    token, _ = create_access_token(AuthUser(user_id=user_id, email="test@example.com"))
    return {"Authorization": f"Bearer {token}"}


def test_root():
    """Test root endpoint returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "Procurement AI"
    assert data["status"] == "running"


def test_health():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_project():
    """Test creating a new sourcing project."""
    _projects.clear()
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test Project",
            "product_description": "I need 500 custom canvas tote bags for my brand",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert data["status"] == "started"
    created = _projects[data["project_id"]]
    assert isinstance(created.get("created_at"), str)
    assert isinstance(created.get("updated_at"), str)


def test_create_project_strips_surrounding_whitespace():
    _projects.clear()
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "   Trimmed Title   ",
            "product_description": "   Need 500 custom canvas tote bags for my brand   ",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    project_id = response.json()["project_id"]
    created = _projects[project_id]
    assert created["title"] == "Trimmed Title"
    assert created["product_description"] == "Need 500 custom canvas tote bags for my brand"


def test_create_project_requires_auth():
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test Project",
            "product_description": "I need 500 custom canvas tote bags for my brand",
        },
    )
    assert response.status_code == 401


def test_create_project_validation():
    """Test that short descriptions are rejected."""
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test",
            "product_description": "short",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 422  # Validation error


def test_create_project_rejects_whitespace_only_title():
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "   ",
            "product_description": "I need 500 custom canvas tote bags for my brand",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 422


def test_create_project_rejects_whitespace_only_description():
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test",
            "product_description": "           ",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 422


def test_create_project_internal_error_returns_safe_message():
    with patch("app.api.v1.projects._create_project", new_callable=AsyncMock) as create_project:
        create_project.side_effect = RuntimeError("sensitive failure details")
        response = client.post(
            "/api/v1/projects",
            json={
                "title": "Test Project",
                "product_description": "I need 500 custom canvas tote bags for my brand",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == PROJECT_START_FAILURE_DETAIL
    assert "sensitive failure details" not in payload["detail"]


def test_get_nonexistent_project():
    """Test 404 for nonexistent project."""
    response = client.get("/api/v1/projects/nonexistent-id/status", headers=_auth_headers())
    assert response.status_code == 404


def test_list_projects():
    """Test listing projects."""
    _projects.clear()

    _projects["active-old"] = {
        "id": "active-old",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active Old",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-10T12:00:00+00:00",
        "updated_at": "2026-03-10T12:00:00+00:00",
    }
    _projects["complete-new"] = {
        "id": "complete-new",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete New",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }
    _projects["active-new"] = {
        "id": "active-new",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active New",
        "status": "parsing",
        "current_stage": "parsing",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-12T18:00:00+00:00",
    }
    _projects["other-user"] = {
        "id": "other-user",
        "user_id": "00000000-0000-0000-0000-000000000099",
        "title": "Should be filtered",
        "status": "parsing",
        "current_stage": "parsing",
        "created_at": "2026-03-13T12:00:00+00:00",
        "updated_at": "2026-03-13T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert [project["id"] for project in payload] == ["active-new", "active-old", "complete-new"]
    assert [project["status"] for project in payload] == ["parsing", "discovering", "complete"]
    assert [project["current_stage"] for project in payload] == ["parsing", "discovering", "complete"]
    assert "created_at" in payload[0]
    assert "updated_at" in payload[0]


def test_list_projects_sorts_legacy_projects_without_timestamps_last_within_status_group():
    _projects.clear()

    _projects["active-legacy"] = {
        "id": "active-legacy",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active Legacy",
        "status": "discovering",
        "current_stage": "discovering",
    }
    _projects["active-timestamped"] = {
        "id": "active-timestamped",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active Timestamped",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T13:00:00+00:00",
    }

    response = client.get("/api/v1/projects", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["active-timestamped", "active-legacy"]


def test_list_projects_uses_created_at_fallback_when_updated_at_missing():
    _projects.clear()

    _projects["project-older-created"] = {
        "id": "project-older-created",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Older Created",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-10T12:00:00+00:00",
    }
    _projects["project-newer-created"] = {
        "id": "project-newer-created",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Newer Created",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-12T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["project-newer-created", "project-older-created"]


def test_list_projects_filters_by_single_status():
    _projects.clear()

    _projects["active-parsing"] = {
        "id": "active-parsing",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active Parsing",
        "status": "parsing",
        "current_stage": "parsing",
        "created_at": "2026-03-10T12:00:00+00:00",
        "updated_at": "2026-03-10T12:00:00+00:00",
    }
    _projects["active-discovering"] = {
        "id": "active-discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active Discovering",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T12:00:00+00:00",
    }
    _projects["complete"] = {
        "id": "complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=parsing", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["active-parsing"]


def test_list_projects_filters_by_multiple_statuses():
    _projects.clear()

    _projects["discovering"] = {
        "id": "discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Discovering",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-10T12:00:00+00:00",
        "updated_at": "2026-03-10T12:00:00+00:00",
    }
    _projects["complete"] = {
        "id": "complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T12:00:00+00:00",
    }
    _projects["failed"] = {
        "id": "failed",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Failed",
        "status": "failed",
        "current_stage": "failed",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }

    response = client.get(
        "/api/v1/projects?status=complete&status=failed",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["failed", "complete"]


def test_list_projects_filters_by_comma_separated_statuses():
    _projects.clear()

    _projects["discovering"] = {
        "id": "discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Discovering",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-10T12:00:00+00:00",
        "updated_at": "2026-03-10T12:00:00+00:00",
    }
    _projects["complete"] = {
        "id": "complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T12:00:00+00:00",
    }
    _projects["failed"] = {
        "id": "failed",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Failed",
        "status": "failed",
        "current_stage": "failed",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=complete,failed", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["failed", "complete"]


def test_list_projects_filters_by_active_alias():
    _projects.clear()

    _projects["steering-project"] = {
        "id": "steering-project",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Steering Needed",
        "status": "steering",
        "current_stage": "steering",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }
    _projects["complete-project"] = {
        "id": "complete-project",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Completed",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=active", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["steering-project"]
    assert payload[0]["status"] == "steering"


def test_list_projects_filters_by_closed_alias():
    _projects.clear()

    _projects["canceled-project"] = {
        "id": "canceled-project",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Canceled",
        "status": "canceled",
        "current_stage": "canceled",
        "created_at": "2026-03-10T12:00:00+00:00",
        "updated_at": "2026-03-10T12:00:00+00:00",
    }
    _projects["failed-project"] = {
        "id": "failed-project",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Failed",
        "status": "failed",
        "current_stage": "failed",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T12:00:00+00:00",
    }
    _projects["complete-project"] = {
        "id": "complete-project",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }
    _projects["active-project"] = {
        "id": "active-project",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-13T12:00:00+00:00",
        "updated_at": "2026-03-13T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=closed", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == [
        "complete-project",
        "failed-project",
        "canceled-project",
    ]
    assert sorted(project["status"] for project in payload) == ["canceled", "complete", "failed"]


def test_list_projects_rejects_invalid_status_filter():
    _projects.clear()
    _projects["parsing"] = {
        "id": "parsing",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Parsing",
        "status": "parsing",
        "current_stage": "parsing",
    }

    response = client.get("/api/v1/projects?status=not-real", headers=_auth_headers())
    assert response.status_code == 422
    assert "Invalid status filter value(s): not-real" in response.json()["detail"]
    assert "active" in response.json()["detail"]
    assert "closed" in response.json()["detail"]


def test_list_projects_rejects_invalid_value_in_comma_separated_status_filter():
    _projects.clear()
    _projects["parsing"] = {
        "id": "parsing",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Parsing",
        "status": "parsing",
        "current_stage": "parsing",
    }

    response = client.get("/api/v1/projects?status=parsing,not-real", headers=_auth_headers())
    assert response.status_code == 422
    assert "Invalid status filter value(s): not-real" in response.json()["detail"]


def test_list_projects_filter_normalizes_stored_status_case_and_whitespace():
    _projects.clear()
    _projects["legacy-parsing"] = {
        "id": "legacy-parsing",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Legacy Parsing",
        "status": " Parsing ",
        "current_stage": " Parsing ",
        "created_at": "2026-03-13T12:00:00+00:00",
        "updated_at": "2026-03-13T12:00:00+00:00",
    }
    _projects["complete"] = {
        "id": "complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=parsing", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["legacy-parsing"]
    assert payload[0]["status"] == "parsing"
    assert payload[0]["current_stage"] == "parsing"


def test_list_projects_returns_canonical_current_stage_when_missing():
    _projects.clear()
    _projects["legacy-no-stage"] = {
        "id": "legacy-no-stage",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Legacy Missing Stage",
        "status": " Discovering ",
        "current_stage": "   ",
        "created_at": "2026-03-14T12:00:00+00:00",
        "updated_at": "2026-03-14T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["legacy-no-stage"]
    assert payload[0]["status"] == "discovering"
    assert payload[0]["current_stage"] == "discovering"


def test_list_projects_filters_by_status_when_legacy_status_is_blank():
    _projects.clear()
    _projects["legacy-stage-only"] = {
        "id": "legacy-stage-only",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Legacy stage only",
        "status": "   ",
        "current_stage": " Discovering ",
        "created_at": "2026-03-15T12:00:00+00:00",
        "updated_at": "2026-03-15T12:00:00+00:00",
    }
    _projects["complete"] = {
        "id": "complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-14T12:00:00+00:00",
        "updated_at": "2026-03-14T12:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=discovering", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["legacy-stage-only"]
    assert payload[0]["status"] == "discovering"
    assert payload[0]["current_stage"] == "discovering"


def test_list_projects_active_alias_treats_normalized_status_as_active_for_sorting():
    _projects.clear()
    _projects["active-parsing-legacy"] = {
        "id": "active-parsing-legacy",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Legacy Active",
        "status": " Parsing ",
        "current_stage": "parsing",
        "created_at": "2026-03-11T12:00:00+00:00",
        "updated_at": "2026-03-11T12:00:00+00:00",
    }
    _projects["complete-newer"] = {
        "id": "complete-newer",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete Newer",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T13:00:00+00:00",
    }

    response = client.get("/api/v1/projects?status=active", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["active-parsing-legacy"]

    response_all = client.get("/api/v1/projects", headers=_auth_headers())
    assert response_all.status_code == 200
    payload_all = response_all.json()
    assert [project["id"] for project in payload_all] == ["active-parsing-legacy", "complete-newer"]


def test_list_projects_filters_by_title_keyword():
    _projects.clear()
    _projects["capsules"] = {
        "id": "capsules",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Biodegradable Coffee Capsules",
        "status": "discovering",
        "current_stage": "discovering",
    }
    _projects["labels"] = {
        "id": "labels",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Luxury Candle Labels",
        "status": "discovering",
        "current_stage": "discovering",
    }

    response = client.get("/api/v1/projects?q=coffee", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["capsules"]


def test_list_projects_title_keyword_filter_is_case_insensitive():
    _projects.clear()
    _projects["motor-shafts"] = {
        "id": "motor-shafts",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Precision Motor Shafts",
        "status": "parsing",
        "current_stage": "parsing",
    }

    response = client.get("/api/v1/projects?q=SHAFTS", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["motor-shafts"]


def test_list_projects_keyword_matches_product_description():
    _projects.clear()
    _projects["fasteners"] = {
        "id": "fasteners",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Metal Components",
        "product_description": "Need zinc-coated steel fasteners for assembly line.",
        "status": "parsing",
        "current_stage": "parsing",
    }
    _projects["labels"] = {
        "id": "labels",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Packaging Labels",
        "product_description": "Need premium matte labels.",
        "status": "parsing",
        "current_stage": "parsing",
    }

    response = client.get("/api/v1/projects?q=FASTENERS", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["fasteners"]


def test_list_projects_keyword_requires_all_terms_across_title_and_description():
    _projects.clear()
    _projects["motor-housing-aluminum"] = {
        "id": "motor-housing-aluminum",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Precision Motor Housing",
        "product_description": "Need anodized aluminum finish.",
        "status": "parsing",
        "current_stage": "parsing",
    }
    _projects["motor-bracket-steel"] = {
        "id": "motor-bracket-steel",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Precision Motor Bracket",
        "product_description": "Need cold-rolled steel parts.",
        "status": "parsing",
        "current_stage": "parsing",
    }

    response = client.get("/api/v1/projects?q=motor aluminum", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["motor-housing-aluminum"]


def test_list_projects_keyword_all_term_match_is_order_insensitive():
    _projects.clear()
    _projects["motor-housing-aluminum"] = {
        "id": "motor-housing-aluminum",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Precision Motor Housing",
        "product_description": "Need anodized aluminum finish.",
        "status": "parsing",
        "current_stage": "parsing",
    }

    response = client.get("/api/v1/projects?q=ALUMINUM%20motor", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["motor-housing-aluminum"]


def test_list_projects_combines_status_and_description_keyword_filters():
    _projects.clear()
    _projects["fasteners-discovering"] = {
        "id": "fasteners-discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run A",
        "product_description": "Need zinc-coated steel fasteners for assembly line.",
        "status": "discovering",
        "current_stage": "discovering",
    }
    _projects["fasteners-complete"] = {
        "id": "fasteners-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run B",
        "product_description": "Need zinc-coated steel fasteners for assembly line.",
        "status": "complete",
        "current_stage": "complete",
    }

    response = client.get(
        "/api/v1/projects?status=discovering&q=fasteners",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["fasteners-discovering"]


def test_list_projects_combines_status_and_multi_term_query_filters():
    _projects.clear()
    _projects["motor-aluminum-discovering"] = {
        "id": "motor-aluminum-discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Precision motor housings",
        "product_description": "Need anodized aluminum finish.",
        "status": "discovering",
        "current_stage": "discovering",
    }
    _projects["motor-aluminum-complete"] = {
        "id": "motor-aluminum-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Precision motor housings",
        "product_description": "Need anodized aluminum finish.",
        "status": "complete",
        "current_stage": "complete",
    }

    response = client.get(
        "/api/v1/projects?status=discovering&q=motor%20aluminum",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["motor-aluminum-discovering"]


def test_list_projects_title_keyword_ignores_whitespace_only_query():
    _projects.clear()
    _projects["default-visible"] = {
        "id": "default-visible",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Default Visible Project",
        "status": "complete",
        "current_stage": "complete",
    }

    response = client.get("/api/v1/projects?q=   ", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload] == ["default-visible"]


def test_list_projects_title_keyword_rejects_overlong_query():
    query = "a" * 121

    response = client.get(f"/api/v1/projects?q={query}", headers=_auth_headers())

    assert response.status_code == 422


def test_cancel_project():
    """Test canceling an in-progress project."""
    create_response = client.post(
        "/api/v1/projects",
        json={
            "title": "Cancel Test",
            "product_description": "Need 500 steel fasteners sourced for automotive assembly",
        },
        headers=_auth_headers(),
    )
    assert create_response.status_code == 200
    project_id = create_response.json()["project_id"]

    cancel_response = client.post(
        f"/api/v1/projects/{project_id}/cancel",
        headers=_auth_headers(),
    )
    assert cancel_response.status_code == 200
    cancel_data = cancel_response.json()
    assert cancel_data["project_id"] == project_id
    assert cancel_data["status"] in {"canceled", "failed", "complete"}


def test_answer_clarifying_questions_resumes_pipeline():
    _projects.clear()
    project_id = "answer-success"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Answer Success",
        "product_description": "Need custom die-cast housings.",
        "status": "clarifying",
        "current_stage": "clarifying",
        "parsed_requirements": {"product_type": "Housing"},
        "clarifying_questions": [{"field": "quantity", "question": "How many units?"}],
        "checkpoint_responses": {},
    }

    llm_payload = (
        '{"product_type":"Housing","material":"Aluminum","dimensions":null,"quantity":1200,'
        '"customization":"Black powder coat","delivery_location":"Chicago, IL","deadline":null,'
        '"certifications_needed":[],"budget_range":null,"missing_fields":[],"search_queries":[],'
        '"regional_searches":[],"clarifying_questions":[],"sourcing_strategy":"regional",'
        '"sourcing_preference":null}'
    )
    with patch("app.api.v1.projects.call_llm_structured", new=AsyncMock(return_value=llm_payload)):
        with patch("app.api.v1.projects._resume_pipeline_task", new=AsyncMock()) as resume_pipeline:
            response = client.post(
                f"/api/v1/projects/{project_id}/answer",
                json={"answers": {"quantity": "1200"}},
                headers=_auth_headers(),
            )

    assert response.status_code == 200
    assert response.json()["status"] == "resumed"
    updated = _projects[project_id]
    assert updated["status"] == "discovering"
    assert updated["current_stage"] == "discovering"
    assert updated["clarifying_questions"] is None
    assert updated["user_answers"] == {"quantity": "1200"}
    resume_pipeline.assert_awaited_once_with(project_id)


def test_answer_clarifying_questions_returns_safe_error_message_on_unexpected_failure():
    _projects.clear()
    project_id = "answer-safe-error"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Answer Safe Error",
        "product_description": "Need precision metal washers.",
        "status": "clarifying",
        "current_stage": "clarifying",
        "parsed_requirements": {"product_type": "Washer"},
        "clarifying_questions": [{"field": "material", "question": "What alloy?"}],
        "checkpoint_responses": {},
    }

    with patch("app.api.v1.projects._save_project", new=AsyncMock(side_effect=RuntimeError("db password leaked"))):
        response = client.post(
            f"/api/v1/projects/{project_id}/answer",
            json={"answers": {"material": "316 stainless"}},
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == PROJECT_ANSWER_FAILURE_DETAIL
    assert "db password leaked" not in payload["detail"]


def test_answer_clarifying_questions_requires_clarifying_status():
    _projects.clear()
    project_id = "answer-wrong-status"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Answer Wrong Status",
        "product_description": "Need custom machined shafts.",
        "status": "discovering",
        "current_stage": "discovering",
        "parsed_requirements": {"product_type": "Shaft"},
        "clarifying_questions": None,
        "checkpoint_responses": {},
    }

    response = client.post(
        f"/api/v1/projects/{project_id}/answer",
        json={"answers": {"material": "4140 steel"}},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Project is not waiting for answers"


def test_restart_project_from_discovering_resets_downstream_state():
    _projects.clear()
    project_id = "proj-restart-discover"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Restart Test",
        "product_description": "Need precision machined brackets",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": {
            "product_type": "Bracket",
            "material": "Steel",
            "dimensions": None,
            "quantity": 500,
            "customization": None,
            "delivery_location": "Detroit, MI",
            "deadline": None,
            "certifications_needed": [],
            "budget_range": None,
            "missing_fields": [],
            "search_queries": [],
            "regional_searches": [],
            "clarifying_questions": [],
            "sourcing_strategy": None,
            "sourcing_preference": None,
        },
        "discovery_results": {"suppliers": []},
        "verification_results": {"verifications": []},
        "comparison_result": {"comparisons": []},
        "recommendation_result": {"recommendations": []},
        "chat_messages": [],
        "outreach_state": {"selected_suppliers": [], "supplier_statuses": [], "draft_emails": []},
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": "best_low_risk",
    }

    with patch("app.api.v1.projects._resume_pipeline_task", new=AsyncMock()):
        response = client.post(
            f"/api/v1/projects/{project_id}/restart",
            json={"from_stage": "discovering"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "restarted"
        assert payload["from_stage"] == "discovering"

    updated = _projects[project_id]
    assert updated["status"] == "discovering"
    assert updated["discovery_results"] is None
    assert updated["verification_results"] is None
    assert updated["comparison_result"] is None
    assert updated["recommendation_result"] is None
    assert updated["outreach_state"] is None
    assert updated["decision_preference"] is None


def test_restart_with_additional_context_forces_parsing():
    _projects.clear()
    project_id = "proj-restart-parse"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Restart Parsing Test",
        "product_description": "Need stamped aluminum parts",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": {
            "product_type": "Stamped Part",
            "material": "Aluminum",
            "dimensions": None,
            "quantity": 10000,
            "customization": None,
            "delivery_location": "Flint, MI",
            "deadline": None,
            "certifications_needed": [],
            "budget_range": None,
            "missing_fields": [],
            "search_queries": [],
            "regional_searches": [],
            "clarifying_questions": [],
            "sourcing_strategy": None,
            "sourcing_preference": None,
        },
        "discovery_results": {"suppliers": []},
        "verification_results": {"verifications": []},
        "comparison_result": {"comparisons": []},
        "recommendation_result": {"recommendations": []},
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": "best_overall",
    }

    with patch("app.api.v1.projects._run_pipeline_task", new=AsyncMock()):
        response = client.post(
            f"/api/v1/projects/{project_id}/restart",
            json={
                "from_stage": "discovering",
                "additional_context": "Prioritize suppliers with in-house anodizing and PPAP support.",
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "restarted"
        assert payload["from_stage"] == "parsing"

    updated = _projects[project_id]
    assert updated["status"] == "parsing"
    assert "Additional context" in updated["product_description"]
    assert updated["parsed_requirements"] is None
    assert updated["decision_preference"] is None


def test_status_includes_decision_preference():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000111"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Decision Preference",
        "product_description": "Need custom packaging",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": "best_speed_to_order",
    }

    response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["decision_preference"] == "best_speed_to_order"


def test_get_status_normalizes_legacy_status_and_stage_values():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000113"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Legacy Status Formatting",
        "product_description": "Need custom packaging",
        "status": " Complete ",
        "current_stage": " ReCommending ",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": None,
    }

    response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["current_stage"] == "recommending"


def test_get_status_uses_stage_when_status_missing():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000114"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Stage Fallback",
        "product_description": "Need custom packaging",
        "status": "   ",
        "current_stage": " Verifying ",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": None,
    }

    response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "verifying"
    assert payload["current_stage"] == "verifying"


def test_get_status_uses_status_when_stage_missing():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000115"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Status Fallback",
        "product_description": "Need custom packaging",
        "status": " Discovering ",
        "current_stage": "   ",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": None,
    }

    response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "discovering"
    assert payload["current_stage"] == "discovering"


def test_set_decision_preference_endpoint_auth_ownership_and_validation():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000112"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Decision Preference",
        "product_description": "Need custom packaging",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
        "decision_preference": None,
    }

    ok_response = client.post(
        f"/api/v1/projects/{project_id}/decision-preference",
        json={"lane_preference": "best_low_risk"},
        headers=_auth_headers(),
    )
    assert ok_response.status_code == 200
    assert ok_response.json()["lane_preference"] == "best_low_risk"
    assert _projects[project_id]["decision_preference"] == "best_low_risk"

    forbidden_response = client.post(
        f"/api/v1/projects/{project_id}/decision-preference",
        json={"lane_preference": "best_overall"},
        headers=_auth_headers("00000000-0000-0000-0000-000000000099"),
    )
    assert forbidden_response.status_code == 403

    invalid_response = client.post(
        f"/api/v1/projects/{project_id}/decision-preference",
        json={"lane_preference": "not_a_lane"},
        headers=_auth_headers(),
    )
    assert invalid_response.status_code == 422


def test_get_status_returns_null_retrospective_when_not_recorded():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000120"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "No Retrospective Yet",
        "product_description": "Need forged steel flange supplier",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "decision_preference": None,
        "buyer_context": None,
        "active_checkpoint": None,
        "proactive_alerts": [],
    }

    response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["retrospective"] is None


def test_submit_retrospective_rejects_non_complete_project():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000123"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Retrospective Requires Completion",
        "product_description": "Need CNC machining supplier",
        "status": "discovering",
        "current_stage": "discovering",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "decision_preference": None,
        "buyer_context": None,
        "retrospective": None,
        "active_checkpoint": None,
        "proactive_alerts": [],
    }

    response = client.post(
        f"/api/v1/projects/{project_id}/retrospective",
        json={"supplier_chosen": "Acme"},
        headers=_auth_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Retrospective can only be submitted for completed projects"
    assert _projects[project_id]["retrospective"] is None


def test_submit_retrospective_is_visible_in_status():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000121"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Retrospective Persistence",
        "product_description": "Need precision molded plastic housings",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "decision_preference": None,
        "buyer_context": None,
        "active_checkpoint": None,
        "proactive_alerts": [],
    }

    payload = {
        "supplier_chosen": "Acme Plastics",
        "overall_satisfaction": 5,
        "communication_rating": 4,
        "pricing_accuracy": "as_expected",
        "what_went_well": "Fast DFM turnaround",
        "what_went_wrong": "Minor packaging issue",
    }
    submit_response = client.post(
        f"/api/v1/projects/{project_id}/retrospective",
        json=payload,
        headers=_auth_headers(),
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "recorded"

    status_response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert status_response.status_code == 200
    retrospective = status_response.json()["retrospective"]
    assert retrospective is not None
    assert retrospective["supplier_chosen"] == "Acme Plastics"
    assert retrospective["overall_satisfaction"] == 5
    assert retrospective["communication_rating"] == 4
    assert retrospective["pricing_accuracy"] == "as_expected"


def test_submit_retrospective_rejects_duplicate_submission():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000125"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Retrospective Single Submission",
        "product_description": "Need cast aluminum enclosure supplier",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "decision_preference": None,
        "buyer_context": None,
        "retrospective": None,
        "active_checkpoint": None,
        "proactive_alerts": [],
    }

    first_payload = {"supplier_chosen": "First Supplier", "overall_satisfaction": 4}
    first_response = client.post(
        f"/api/v1/projects/{project_id}/retrospective",
        json=first_payload,
        headers=_auth_headers(),
    )
    assert first_response.status_code == 200
    assert _projects[project_id]["retrospective"]["supplier_chosen"] == "First Supplier"

    second_payload = {"supplier_chosen": "Second Supplier", "overall_satisfaction": 2}
    second_response = client.post(
        f"/api/v1/projects/{project_id}/retrospective",
        json=second_payload,
        headers=_auth_headers(),
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == PROJECT_RETROSPECTIVE_ALREADY_SUBMITTED_DETAIL
    assert _projects[project_id]["retrospective"]["supplier_chosen"] == "First Supplier"

    status_response = client.get(f"/api/v1/projects/{project_id}/status", headers=_auth_headers())
    assert status_response.status_code == 200
    assert status_response.json()["retrospective"]["supplier_chosen"] == "First Supplier"


def test_submit_retrospective_forbidden_for_non_owner():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000124"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Retrospective Owner Only",
        "product_description": "Need electronics assembly supplier",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "decision_preference": None,
        "buyer_context": None,
        "retrospective": None,
        "active_checkpoint": None,
        "proactive_alerts": [],
    }

    response = client.post(
        f"/api/v1/projects/{project_id}/retrospective",
        json={"supplier_chosen": "Unauthorized Supplier"},
        headers=_auth_headers("00000000-0000-0000-0000-000000000099"),
    )
    assert response.status_code == 403
    assert _projects[project_id]["retrospective"] is None


def test_status_retrospective_hidden_from_other_users():
    _projects.clear()
    project_id = "00000000-0000-0000-0000-000000000122"
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Retrospective Ownership",
        "product_description": "Need cable harness supplier",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "decision_preference": None,
        "buyer_context": None,
        "retrospective": {"supplier_chosen": "Owner-only Supplier"},
        "active_checkpoint": None,
        "proactive_alerts": [],
    }

    forbidden = client.get(
        f"/api/v1/projects/{project_id}/status",
        headers=_auth_headers("00000000-0000-0000-0000-000000000099"),
    )
    assert forbidden.status_code == 403
