"""Tests for phone API safe error handling."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.v1.phone import PHONE_CALL_PARSE_FAILURE_DETAIL, PHONE_CALL_START_FAILURE_DETAIL
from app.core.auth import AuthUser, create_access_token
from app.services.project_store import get_legacy_project_dict, reset_project_store_for_tests

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.main import app

client = TestClient(app)


def _auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    token, _ = create_access_token(AuthUser(user_id=user_id, email="test@example.com"))
    return {"Authorization": f"Bearer {token}"}


def _seed_project(*, include_call: bool = False) -> str:
    project_id = "proj-phone-1" if not include_call else "proj-phone-parse-1"
    outreach_state: dict[str, object] = {}
    if include_call:
        outreach_state = {
            "phone_calls": [
                {
                    "call_id": "call-123",
                    "supplier_name": "Acme Plastics",
                    "supplier_index": 0,
                    "status": "completed",
                    "transcript": "Supplier quoted $2.10 per unit and 21-day lead time.",
                }
            ],
            "supplier_statuses": [
                {
                    "supplier_name": "Acme Plastics",
                    "supplier_index": 0,
                    "phone_call_id": "call-123",
                    "phone_status": "completed",
                }
            ],
        }

    get_legacy_project_dict()[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Phone outreach project",
        "product_description": "Need 500 custom insulated bottles.",
        "status": "verifying",
        "current_stage": "verifying",
        "parsed_requirements": {"product_type": "insulated bottles"},
        "discovery_results": {
            "suppliers": [{"name": "Acme Plastics", "phone": "+13125550111"}],
        },
        "outreach_state": outreach_state,
    }
    return project_id


def setup_function() -> None:
    reset_project_store_for_tests()


def teardown_function() -> None:
    reset_project_store_for_tests()


def test_start_phone_call_internal_error_returns_safe_message() -> None:
    project_id = _seed_project()

    with patch("app.api.v1.phone.initiate_supplier_call", new_callable=AsyncMock) as initiate_call:
        initiate_call.side_effect = RuntimeError("retell credential stack trace")
        response = client.post(
            f"/api/v1/projects/{project_id}/phone/call",
            json={"supplier_index": 0, "phone_number": "+13125550111", "questions": []},
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == PHONE_CALL_START_FAILURE_DETAIL
    assert "retell credential stack trace" not in payload["detail"]


def test_start_phone_call_value_error_keeps_actionable_400_detail() -> None:
    project_id = _seed_project()

    with patch("app.api.v1.phone.initiate_supplier_call", new_callable=AsyncMock) as initiate_call:
        initiate_call.side_effect = ValueError("Invalid destination phone number")
        response = client.post(
            f"/api/v1/projects/{project_id}/phone/call",
            json={"supplier_index": 0, "phone_number": "invalid", "questions": []},
            headers=_auth_headers(),
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid destination phone number"


def test_parse_phone_call_internal_error_returns_safe_message() -> None:
    project_id = _seed_project(include_call=True)

    with patch(
        "app.api.v1.phone.parse_call_transcript",
        new_callable=AsyncMock,
    ) as parse_transcript:
        parse_transcript.side_effect = RuntimeError("llm parser internal error context")
        response = client.post(
            f"/api/v1/projects/{project_id}/phone/calls/call-123/parse",
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == PHONE_CALL_PARSE_FAILURE_DETAIL
    assert "llm parser internal error context" not in payload["detail"]
