"""Tests for the projects API endpoints."""

import os
import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import AuthUser, create_access_token

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.main import app
from app.api.v1.projects import _projects

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
