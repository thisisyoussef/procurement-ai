"""Tests for dashboard API project start flow."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.v1.dashboard import PROJECT_START_FAILURE_DETAIL
from app.core.auth import AuthUser, create_access_token
from app.schemas.dashboard import DashboardContactsResponse
from app.services.dashboard_service import _contact_matches_query
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


def test_dashboard_summary_filters_projects_by_steering_status():
    projects = get_legacy_project_dict()
    projects["proj-dash-steering"] = {
        "id": "proj-dash-steering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Steering project",
        "product_description": "Need precision coil springs.",
        "status": "steering",
        "current_stage": "steering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-complete"] = {
        "id": "proj-dash-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete project",
        "product_description": "Need finished labels.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?status=steering", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-steering"]
    assert payload["projects"][0]["status"] == "steering"


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


def test_dashboard_summary_filters_projects_by_title_keyword_case_insensitive():
    projects = get_legacy_project_dict()
    projects["proj-dash-bottle"] = {
        "id": "proj-dash-bottle",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle labels supplier shortlist",
        "product_description": "Need premium bottle labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-carton"] = {
        "id": "proj-dash-carton",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Carton inserts",
        "product_description": "Need carton inserts.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?q=BOTTLE", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-bottle"]


def test_dashboard_summary_ignores_whitespace_only_title_query():
    projects = get_legacy_project_dict()
    projects["proj-dash-bottle"] = {
        "id": "proj-dash-bottle",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle labels supplier shortlist",
        "product_description": "Need premium bottle labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-carton"] = {
        "id": "proj-dash-carton",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Carton inserts",
        "product_description": "Need carton inserts.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?q=%20%20%20", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert sorted(project["id"] for project in payload["projects"]) == [
        "proj-dash-bottle",
        "proj-dash-carton",
    ]


def test_dashboard_summary_combines_status_and_title_query_filters():
    projects = get_legacy_project_dict()
    projects["proj-dash-bottle-discovering"] = {
        "id": "proj-dash-bottle-discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle labels supplier shortlist",
        "product_description": "Need premium bottle labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-bottle-complete"] = {
        "id": "proj-dash-bottle-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle labels completed run",
        "product_description": "Need premium bottle labels.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get(
        "/api/v1/dashboard/summary?status=discovering&q=bottle",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-bottle-discovering"]


def test_dashboard_summary_filters_projects_by_active_alias():
    projects = get_legacy_project_dict()
    projects["proj-dash-steering"] = {
        "id": "proj-dash-steering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Needs steering",
        "product_description": "Need stainless tube bends.",
        "status": "steering",
        "current_stage": "steering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-complete"] = {
        "id": "proj-dash-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Done",
        "product_description": "Need labels.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?status=active", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-steering"]
    assert payload["projects"][0]["status"] == "steering"


def test_dashboard_summary_filters_projects_by_closed_alias():
    projects = get_legacy_project_dict()
    projects["proj-dash-canceled"] = {
        "id": "proj-dash-canceled",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Canceled project",
        "product_description": "Need coated springs.",
        "status": "canceled",
        "current_stage": "canceled",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-failed"] = {
        "id": "proj-dash-failed",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Failed project",
        "product_description": "Need wire harness clips.",
        "status": "failed",
        "current_stage": "failed",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-complete"] = {
        "id": "proj-dash-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete project",
        "product_description": "Need stamped nameplates.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-active"] = {
        "id": "proj-dash-active",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Active project",
        "product_description": "Need cast housings.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?status=closed", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    statuses = sorted(project["status"] for project in payload["projects"])
    assert statuses == ["canceled", "complete", "failed"]


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
    assert "active" in response.json()["detail"]
    assert "closed" in response.json()["detail"]


def test_dashboard_summary_greeting_counts_steering_as_active():
    projects = get_legacy_project_dict()
    projects["proj-active-steering"] = {
        "id": "proj-active-steering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Needs checkpoint answer",
        "product_description": "Need cast aluminum housings.",
        "status": "steering",
        "current_stage": "steering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-complete"] = {
        "id": "proj-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Done",
        "product_description": "Need shipping labels.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["greeting"]["active_projects"] == 1


def test_dashboard_summary_greeting_active_count_normalizes_status_whitespace_and_case():
    projects = get_legacy_project_dict()
    projects["proj-active-parsing-normalized"] = {
        "id": "proj-active-parsing-normalized",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Parsing with legacy formatting",
        "product_description": "Need embossed cartons.",
        "status": " Parsing ",
        "current_stage": "parsing",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["greeting"]["active_projects"] == 1


def test_dashboard_summary_greeting_excludes_terminal_statuses_from_active_count():
    projects = get_legacy_project_dict()
    projects["proj-failed"] = {
        "id": "proj-failed",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run failed",
        "product_description": "Need precision fasteners.",
        "status": "failed",
        "current_stage": "failed",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-canceled"] = {
        "id": "proj-canceled",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run canceled",
        "product_description": "Need custom inserts.",
        "status": "canceled",
        "current_stage": "canceled",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-complete"] = {
        "id": "proj-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run complete",
        "product_description": "Need nylon spacers.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["greeting"]["active_projects"] == 0


def test_dashboard_summary_returns_canonical_status_and_phase_for_legacy_values():
    projects = get_legacy_project_dict()
    projects["proj-legacy-complete"] = {
        "id": "proj-legacy-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Legacy complete formatting",
        "product_description": "Need precision washers.",
        "status": " Complete ",
        "current_stage": " Complete ",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-legacy-complete"]
    assert payload["projects"][0]["status"] == "complete"
    assert payload["projects"][0]["phase_label"] == "Order placed"


def test_dashboard_summary_sorts_projects_active_first_then_recently_updated():
    projects = get_legacy_project_dict()
    projects["proj-complete-newest"] = {
        "id": "proj-complete-newest",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Newest complete",
        "product_description": "Need corrugated trays.",
        "status": "complete",
        "current_stage": "complete",
        "created_at": "2026-03-15T12:00:00+00:00",
        "updated_at": "2026-03-15T12:00:00+00:00",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-active-old"] = {
        "id": "proj-active-old",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Older active",
        "product_description": "Need laser-cut inserts.",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-12T12:00:00+00:00",
        "updated_at": "2026-03-12T12:00:00+00:00",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-active-new"] = {
        "id": "proj-active-new",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Newer active",
        "product_description": "Need anodized housings.",
        "status": "parsing",
        "current_stage": "parsing",
        "created_at": "2026-03-14T12:00:00+00:00",
        "updated_at": "2026-03-14T12:00:00+00:00",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == [
        "proj-active-new",
        "proj-active-old",
        "proj-complete-newest",
    ]


def test_dashboard_summary_sorts_by_created_at_when_updated_at_missing():
    projects = get_legacy_project_dict()
    projects["proj-active-created-older"] = {
        "id": "proj-active-created-older",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Older created",
        "product_description": "Need stamped clips.",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-10T12:00:00+00:00",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-active-created-newer"] = {
        "id": "proj-active-created-newer",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Newer created",
        "product_description": "Need formed steel tabs.",
        "status": "discovering",
        "current_stage": "discovering",
        "created_at": "2026-03-13T12:00:00+00:00",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == [
        "proj-active-created-newer",
        "proj-active-created-older",
    ]


def test_dashboard_contacts_passes_trimmed_query_to_service():
    with patch(
        "app.api.v1.dashboard.get_dashboard_contacts_for_user",
        new=AsyncMock(return_value=DashboardContactsResponse(suppliers=[], count=0)),
    ) as get_contacts:
        response = client.get("/api/v1/dashboard/contacts?q=%20acme%20", headers=_auth_headers())

    assert response.status_code == 200
    get_contacts.assert_awaited_once_with(
        user_id="00000000-0000-0000-0000-000000000001",
        limit=50,
        contact_query="acme",
    )


def test_dashboard_contacts_ignores_whitespace_query():
    with patch(
        "app.api.v1.dashboard.get_dashboard_contacts_for_user",
        new=AsyncMock(return_value=DashboardContactsResponse(suppliers=[], count=0)),
    ) as get_contacts:
        response = client.get("/api/v1/dashboard/contacts?q=%20%20%20", headers=_auth_headers())

    assert response.status_code == 200
    get_contacts.assert_awaited_once_with(
        user_id="00000000-0000-0000-0000-000000000001",
        limit=50,
        contact_query=None,
    )


def test_dashboard_contacts_rejects_overlong_query():
    query = "a" * 121
    response = client.get(f"/api/v1/dashboard/contacts?q={query}", headers=_auth_headers())

    assert response.status_code == 422


def test_contact_matches_query_matches_name_email_and_location():
    contact = {
        "name": "Acme Precision Metals",
        "email": "sales@acme.example",
        "website": "https://acme.example",
        "city": "Detroit",
        "country": "USA",
    }

    assert _contact_matches_query(contact, "precision")
    assert _contact_matches_query(contact, "sales@acme")
    assert _contact_matches_query(contact, "detroit")
    assert not _contact_matches_query(contact, "toronto")
