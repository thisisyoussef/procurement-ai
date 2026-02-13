"""Tests for outreach lifecycle planning and tracking."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import AuthUser, create_access_token

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.api.v1.projects import _projects
from app.main import app

client = TestClient(app)


def _auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    token, _ = create_access_token(AuthUser(user_id=user_id, email="test@example.com"))
    return {"Authorization": f"Bearer {token}"}


def _seed_project(project_id: str) -> None:
    _projects[project_id] = {
        "id": project_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Tote Bags",
        "product_description": "Need 1000 tote bags",
        "status": "complete",
        "current_stage": "complete",
        "error": None,
        "parsed_requirements": {
            "product_type": "Canvas Tote Bag",
            "material": "Canvas",
            "dimensions": "40x30cm",
            "quantity": 1000,
            "customization": "Printed logo",
            "delivery_location": "Austin, TX",
            "deadline": None,
            "certifications_needed": [],
            "budget_range": "$3-5",
            "missing_fields": [],
            "search_queries": [],
            "regional_searches": [],
            "clarifying_questions": [],
            "sourcing_strategy": None,
            "sourcing_preference": None,
        },
        "discovery_results": {
            "suppliers": [
                {
                    "name": "Acme Mills",
                    "website": "https://acme.example",
                    "email": "sales@acme.example",
                    "phone": None,
                    "city": "Istanbul",
                    "country": "Turkey",
                    "description": "Bag manufacturer",
                    "categories": ["bags"],
                    "certifications": ["ISO9001"],
                    "google_rating": 4.6,
                    "source": "web",
                    "confidence_score": 90,
                    "contact_person": None,
                    "address": None,
                    "intermediary_detection": None,
                    "is_intermediary": False,
                    "intermediary_type": None,
                    "resolved_manufacturer_name": None,
                    "resolved_manufacturer_website": None,
                    "resolution_notes": None,
                    "filter_reasons": [],
                },
                {
                    "name": "Beta Textiles",
                    "website": "https://beta.example",
                    "email": "sales@beta.example",
                    "phone": None,
                    "city": "Izmir",
                    "country": "Turkey",
                    "description": "Textile supplier",
                    "categories": ["textiles"],
                    "certifications": ["ISO9001"],
                    "google_rating": 4.4,
                    "source": "web",
                    "confidence_score": 86,
                    "contact_person": None,
                    "address": None,
                    "intermediary_detection": None,
                    "is_intermediary": False,
                    "intermediary_type": None,
                    "resolved_manufacturer_name": None,
                    "resolved_manufacturer_website": None,
                    "resolution_notes": None,
                    "filter_reasons": [],
                }
            ],
            "search_summary": "ok",
            "search_cost": 0,
            "search_rounds": 1,
            "filtered_suppliers": [],
        },
        "verification_results": {"verifications": []},
        "comparison_result": {"comparisons": [], "analysis_narrative": "", "best_value": None, "best_quality": None, "best_speed": None},
        "recommendation_result": {
            "recommendations": [
                {
                    "rank": 1,
                    "supplier_name": "Acme Mills",
                    "supplier_index": 0,
                    "overall_score": 92,
                    "confidence": "high",
                    "reasoning": "Best fit",
                    "best_for": "best overall",
                }
            ],
            "executive_summary": "",
            "caveats": [],
        },
    }


def test_outreach_plan_and_timeline_tracking():
    _projects.clear()
    project_id = "proj-outreach-1"
    _seed_project(project_id)

    draft_result = {
        "drafts": [
            {
                "supplier_name": "Acme Mills",
                "supplier_index": 0,
                "recipient_email": "sales@acme.example",
                "subject": "RFQ",
                "body": "Hello",
                "status": "draft",
            }
        ],
        "summary": "done",
    }

    with patch("app.api.v1.outreach.draft_outreach_emails", new=AsyncMock()) as mock_draft, patch(
        "app.api.v1.outreach.send_email", new=AsyncMock(return_value={"sent": True, "id": "email_123"})
    ):
        mock_draft.return_value.model_dump.return_value = draft_result
        mock_draft.return_value.drafts = []
        mock_draft.return_value.summary = "done"

        # use real schema object output compatibility
        from app.schemas.agent_state import DraftEmail, OutreachResult

        mock_draft.return_value = OutreachResult(drafts=[DraftEmail(**draft_result["drafts"][0])], summary="done")

        start = client.post(
            f"/api/v1/projects/{project_id}/outreach/start",
            json={"supplier_indices": [0]},
            headers=_auth_headers(),
        )
        assert start.status_code == 200

        send = client.post(
            f"/api/v1/projects/{project_id}/outreach/approve/0",
            json={"draft_index": 0},
            headers=_auth_headers(),
        )
        assert send.status_code == 200
        assert send.json()["sent"] is True

    plan = client.get(f"/api/v1/projects/{project_id}/outreach/plan", headers=_auth_headers())
    assert plan.status_code == 200
    assert plan.json()["funnel"]["rfq_sent"] == 1
    assert len(plan.json()["plans"]) == 1

    timeline = client.get(f"/api/v1/projects/{project_id}/outreach/timeline", headers=_auth_headers())
    assert timeline.status_code == 200
    assert timeline.json()["count"] >= 3
    event_types = [e["event_type"] for e in timeline.json()["events"]]
    assert "intent_registered" in event_types
    assert "email_sent" in event_types


def test_outreach_start_normalizes_supplier_indices():
    _projects.clear()
    project_id = "proj-outreach-index-map"
    _seed_project(project_id)

    with patch("app.api.v1.outreach.draft_outreach_emails", new=AsyncMock()) as mock_draft, patch(
        "app.api.v1.outreach.send_email", new=AsyncMock(return_value={"sent": True, "id": "email_idx_1"})
    ) as mock_send:
        from app.schemas.agent_state import DraftEmail, OutreachResult

        # Agent returns local index 0 for selected supplier list; API should map it to global index 1.
        mock_draft.return_value = OutreachResult(
            drafts=[
                DraftEmail(
                    supplier_name="Beta Textiles",
                    supplier_index=0,
                    recipient_email=None,
                    subject="RFQ",
                    body="Hello",
                    status="draft",
                )
            ],
            summary="done",
        )

        start = client.post(
            f"/api/v1/projects/{project_id}/outreach/start",
            json={"supplier_indices": [1]},
            headers=_auth_headers(),
        )
        assert start.status_code == 200
        start_payload = start.json()
        assert start_payload["drafts"][0]["supplier_index"] == 1

        send = client.post(
            f"/api/v1/projects/{project_id}/outreach/approve/0",
            json={"draft_index": 0},
            headers=_auth_headers(),
        )
        assert send.status_code == 200
        assert send.json()["sent"] is True
        assert mock_send.await_args.kwargs["to"] == "sales@beta.example"


def test_quick_approval_sends_outreach():
    _projects.clear()
    project_id = "proj-outreach-quick-1"
    _seed_project(project_id)

    with patch("app.api.v1.outreach.draft_outreach_emails", new=AsyncMock()) as mock_draft, patch(
        "app.api.v1.outreach.send_email", new=AsyncMock(return_value={"sent": True, "id": "email_quick_1"})
    ):
        from app.schemas.agent_state import DraftEmail, OutreachResult

        mock_draft.return_value = OutreachResult(
            drafts=[
                DraftEmail(
                    supplier_name="Acme Mills",
                    supplier_index=0,
                    recipient_email="sales@acme.example",
                    subject="RFQ",
                    body="Hello",
                    status="draft",
                )
            ],
            summary="done",
        )

        approve = client.post(
            f"/api/v1/projects/{project_id}/outreach/quick-approval",
            json={"approve": True, "max_suppliers": 3},
            headers=_auth_headers(),
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"
        assert approve.json()["sent_count"] == 1

    status = client.get(
        f"/api/v1/projects/{project_id}/outreach/status",
        headers=_auth_headers(),
    )
    assert status.status_code == 200
    payload = status.json()
    assert payload["quick_approval_decision"] == "approved"
    assert payload["supplier_statuses"][0]["email_sent"] is True


def test_parse_response_excludes_supplier_when_unfulfillable():
    _projects.clear()
    project_id = "proj-outreach-quick-2"
    _seed_project(project_id)

    # Seed basic outreach state with one selected supplier.
    _projects[project_id]["outreach_state"] = {
        "selected_suppliers": [0],
        "supplier_statuses": [
            {
                "supplier_name": "Acme Mills",
                "supplier_index": 0,
                "email_sent": True,
                "response_received": False,
                "follow_ups_sent": 0,
                "parsed_quote": None,
            }
        ],
        "draft_emails": [],
        "follow_up_emails": [],
        "parsed_quotes": [],
        "events": [],
    }

    from app.schemas.agent_state import ParsedQuote

    with patch(
        "app.api.v1.outreach.parse_supplier_response",
        new=AsyncMock(
            return_value=ParsedQuote(
                supplier_name="Acme Mills",
                supplier_index=0,
                can_fulfill=False,
                fulfillment_note="Cannot produce this product category",
                confidence_score=95,
                raw_text="",
            )
        ),
    ):
        parsed = client.post(
            f"/api/v1/projects/{project_id}/outreach/parse-response",
            json={
                "supplier_index": 0,
                "response_text": "Sorry, we cannot produce this product category.",
            },
            headers=_auth_headers(),
        )
        assert parsed.status_code == 200

    updated = _projects[project_id]
    assert updated["recommendation_result"]["recommendations"] == []
    assert updated["outreach_state"]["excluded_suppliers"] == [0]
