"""Tests for Procurement AI intake, lead capture, and first-party telemetry endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import AuthUser, create_access_token
from app.main import app

client = TestClient(app)


def _auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    token, _ = create_access_token(AuthUser(user_id=user_id, email="test@example.com"))
    return {"Authorization": f"Bearer {token}"}


def test_start_intake_creates_project_and_redirect_path():
    with patch("app.api.v1.projects._run_pipeline_task", new=AsyncMock(return_value=None)):
        response = client.post(
            "/api/v1/intake/start",
            json={
                "message": "Need 300 custom tote bags with logo print, delivery to Austin in four weeks.",
                "source": "landing_hero",
                "session_id": "sess_test_1",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "project_id" in data
    assert data["redirect_path"].startswith("/product?projectId=")
    assert "entry=landing_hero" in data["redirect_path"]


def test_lead_capture_deduplicates_by_email():
    first = client.post(
        "/api/v1/leads",
        json={
            "email": "Founder@Brand.com",
            "sourcing_note": "Need packaging suppliers",
            "source": "landing_early_access",
        },
    )
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["ok"] is True
    assert first_data["deduped"] is False

    second = client.post(
        "/api/v1/leads",
        json={
            "email": "founder@brand.com",
            "sourcing_note": "Need apparel suppliers too",
            "source": "landing_early_access",
        },
    )
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["ok"] is True
    assert second_data["deduped"] is True
    assert second_data["lead_id"] == first_data["lead_id"]


def test_events_endpoint_persists_event():
    response = client.post(
        "/api/v1/events",
        json={
            "event_name": "cta_start_sourcing_click",
            "session_id": "sess_events_1",
            "path": "/",
            "payload": {"location": "hero"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "event_id" in data
