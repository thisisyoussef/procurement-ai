"""Tests for dashboard API project start flow."""

import asyncio
import os
from unittest.mock import ANY, AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.v1.dashboard import PROJECT_START_FAILURE_DETAIL
from app.core.auth import AuthUser, create_access_token
from app.schemas.dashboard import DashboardContactsResponse
from app.services.dashboard_service import _contact_matches_query
from app.services.dashboard_service import get_dashboard_activity_for_user
from app.services.dashboard_service import get_dashboard_contacts_for_user
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


def test_dashboard_start_project_normalizes_source_whitespace_and_case():
    with patch("app.api.v1.dashboard._run_pipeline_task", new_callable=AsyncMock):
        response = client.post(
            "/api/v1/dashboard/projects/start",
            json={
                "description": "Need 500 insulated bottles, matte black finish, and fast lead time.",
                "source": "  DASHBOARD_SEARCH  ",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["redirect_path"] == (
        f"/product?projectId={payload['project_id']}&entry=dashboard_search"
    )


def test_dashboard_start_project_defaults_unknown_source_to_dashboard_new():
    with patch("app.api.v1.dashboard._run_pipeline_task", new_callable=AsyncMock):
        response = client.post(
            "/api/v1/dashboard/projects/start",
            json={
                "description": "Need 500 insulated bottles, matte black finish, and fast lead time.",
                "source": "dashboard_sidebar",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["redirect_path"] == (
        f"/product?projectId={payload['project_id']}&entry=dashboard_new"
    )


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


def test_dashboard_summary_filters_projects_by_comma_separated_statuses_and_aliases():
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
    projects["proj-dash-canceled"] = {
        "id": "proj-dash-canceled",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Canceled project",
        "product_description": "Need precision washers.",
        "status": "canceled",
        "current_stage": "canceled",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-complete"] = {
        "id": "proj-dash-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete project",
        "product_description": "Need stamped clips.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get(
        "/api/v1/dashboard/summary?status=active,closed",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    statuses = sorted(project["status"] for project in payload["projects"])
    assert statuses == ["canceled", "complete", "steering"]


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


def test_dashboard_summary_filters_projects_by_description_keyword_case_insensitive():
    projects = get_legacy_project_dict()
    projects["proj-dash-fasteners"] = {
        "id": "proj-dash-fasteners",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run A",
        "product_description": "Need zinc-coated steel fasteners for assembly line.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-labels"] = {
        "id": "proj-dash-labels",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run B",
        "product_description": "Need premium matte labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?q=FASTENERS", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-fasteners"]


def test_dashboard_summary_multi_term_query_matches_across_title_and_description():
    projects = get_legacy_project_dict()
    projects["proj-dash-bottle-matte"] = {
        "id": "proj-dash-bottle-matte",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle supplier shortlist",
        "product_description": "Need premium matte labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-bottle-glossy"] = {
        "id": "proj-dash-bottle-glossy",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle supplier shortlist",
        "product_description": "Need premium glossy labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?q=bottle matte", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-bottle-matte"]


def test_dashboard_summary_multi_term_query_tolerates_punctuation_and_spacing():
    projects = get_legacy_project_dict()
    projects["proj-dash-food-grade"] = {
        "id": "proj-dash-food-grade",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Food-Grade Tube Fittings",
        "product_description": "Need hygienic fittings for beverage line.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?q= food,   grade fittings ", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-dash-food-grade"]


def test_dashboard_summary_multi_term_query_requires_all_tokens():
    projects = get_legacy_project_dict()
    projects["proj-dash-bottle-matte"] = {
        "id": "proj-dash-bottle-matte",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Bottle supplier shortlist",
        "product_description": "Need premium matte labels.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?q=bottle titanium", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["projects"] == []


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


def test_dashboard_summary_rejects_overlong_title_query():
    query = "a" * 121

    response = client.get(f"/api/v1/dashboard/summary?q={query}", headers=_auth_headers())

    assert response.status_code == 422


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


def test_dashboard_summary_combines_status_and_description_query_filters():
    projects = get_legacy_project_dict()
    projects["proj-dash-fasteners-discovering"] = {
        "id": "proj-dash-fasteners-discovering",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run A",
        "product_description": "Need zinc-coated steel fasteners for assembly line.",
        "status": "discovering",
        "current_stage": "discovering",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-dash-fasteners-complete"] = {
        "id": "proj-dash-fasteners-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Run B",
        "product_description": "Need zinc-coated steel fasteners for assembly line.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get(
        "/api/v1/dashboard/summary?status=discovering&q=fasteners",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == [
        "proj-dash-fasteners-discovering"
    ]


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


def test_dashboard_summary_filters_by_active_alias_when_status_is_blank_and_stage_is_active():
    projects = get_legacy_project_dict()
    projects["proj-stage-only-active"] = {
        "id": "proj-stage-only-active",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Stage only active",
        "product_description": "Need stamped inserts.",
        "status": "   ",
        "current_stage": " Steering ",
        "outreach_state": None,
        "parsed_requirements": {},
    }
    projects["proj-complete"] = {
        "id": "proj-complete",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Complete run",
        "product_description": "Need anodized brackets.",
        "status": "complete",
        "current_stage": "complete",
        "outreach_state": None,
        "parsed_requirements": {},
    }

    response = client.get("/api/v1/dashboard/summary?status=active", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert [project["id"] for project in payload["projects"]] == ["proj-stage-only-active"]
    assert payload["projects"][0]["status"] == "steering"


def test_dashboard_summary_greeting_counts_active_when_status_is_blank_and_stage_is_active():
    projects = get_legacy_project_dict()
    projects["proj-stage-only-parsing"] = {
        "id": "proj-stage-only-parsing",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Stage only parsing",
        "product_description": "Need molded enclosures.",
        "status": "   ",
        "current_stage": " Parsing ",
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


def test_dashboard_contacts_service_passes_query_to_repository_before_limit():
    rows = [
        {
            "supplier_id": "11111111-1111-1111-1111-111111111111",
            "name": "Acme Precision Metals",
            "website": "https://acme.example",
            "email": "sales@acme.example",
            "phone": "+1 (312) 555-0142",
            "city": "Detroit",
            "country": "USA",
            "interaction_count": 12,
            "project_count": 3,
            "last_interaction_at": 1710000000.0,
            "last_project_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        }
    ]
    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=rows),
    ) as list_contacts:
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=1,
                contact_query="  acme  ",
            )
        )

    assert response.count == 1
    list_contacts.assert_awaited_once_with(
        session=ANY,
        user_id="00000000-0000-0000-0000-000000000001",
        limit=1,
        contact_query="acme",
    )


def test_dashboard_contacts_service_passes_none_query_to_repository():
    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=[]),
    ) as list_contacts:
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=5,
                contact_query="   ",
            )
        )

    assert response.count == 0
    list_contacts.assert_awaited_once_with(
        session=ANY,
        user_id="00000000-0000-0000-0000-000000000001",
        limit=5,
        contact_query=None,
    )


def test_dashboard_contacts_service_falls_back_to_runtime_contacts_when_db_unavailable():
    runtime_projects = [
        {
            "id": "proj-runtime-1",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-20T10:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "11111111-1111-1111-1111-111111111111",
                        "name": "Acme Precision Metals",
                        "website": "https://acme.example",
                        "email": "sales@acme.example",
                        "phone": "+1 (312) 555-0142",
                        "city": "Detroit",
                        "country": "USA",
                    }
                ]
            },
        }
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=runtime_projects)

    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(side_effect=RuntimeError("db unavailable")),
    ), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=10,
                contact_query=None,
            )
        )

    assert response.count == 1
    assert response.suppliers[0].name == "Acme Precision Metals"
    assert response.suppliers[0].email == "sales@acme.example"
    assert response.suppliers[0].last_project_id == "proj-runtime-1"


def test_dashboard_contacts_service_runtime_fallback_filters_before_limit():
    runtime_projects = [
        {
            "id": "proj-runtime-2",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-20T11:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "22222222-2222-2222-2222-222222222222",
                        "name": "Bravo Molding",
                        "email": "hello@bravo.example",
                    },
                    {
                        "supplier_id": "33333333-3333-3333-3333-333333333333",
                        "name": "Acme Plastics",
                        "email": "contact@acmeplastics.example",
                    },
                ]
            },
        }
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=runtime_projects)

    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=1,
                contact_query="acme",
            )
        )

    assert response.count == 1
    assert [supplier.name for supplier in response.suppliers] == ["Acme Plastics"]


def test_dashboard_contacts_service_runtime_fallback_deduplicates_across_projects():
    runtime_projects = [
        {
            "id": "proj-runtime-old",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-19T09:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "name": "Acme Precision Metals",
                        "email": "sales@acme.example",
                    }
                ]
            },
        },
        {
            "id": "proj-runtime-new",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-21T09:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "name": "Acme Precision Metals",
                        "email": "sales@acme.example",
                    }
                ]
            },
        },
        {
            "id": "proj-other-user",
            "user_id": "00000000-0000-0000-0000-000000000099",
            "updated_at": "2026-03-22T09:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        "name": "Other User Supplier",
                    }
                ]
            },
        },
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=runtime_projects)

    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=10,
                contact_query="acme",
            )
        )

    assert response.count == 1
    supplier = response.suppliers[0]
    assert supplier.name == "Acme Precision Metals"
    assert supplier.project_count == 2
    assert supplier.interaction_count == 2
    assert supplier.last_project_id == "proj-runtime-new"


def test_dashboard_contacts_service_merges_db_and_runtime_contacts():
    db_rows = [
        {
            "supplier_id": "11111111-1111-1111-1111-111111111111",
            "name": "Acme Precision Metals",
            "website": None,
            "email": "sales@acme.example",
            "phone": None,
            "city": "Detroit",
            "country": "USA",
            "interaction_count": 12,
            "project_count": 3,
            "last_interaction_at": 1710000000.0,
            "last_project_id": "proj-db-1",
        }
    ]
    runtime_projects = [
        {
            "id": "proj-runtime-1",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-20T10:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "11111111-1111-1111-1111-111111111111",
                        "name": "Acme Precision Metals",
                        "website": "https://acme.example",
                        "email": "sales@acme.example",
                    },
                    {
                        "supplier_id": "22222222-2222-2222-2222-222222222222",
                        "name": "Bravo Molding",
                        "email": "hello@bravo.example",
                    },
                ]
            },
        }
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=runtime_projects)

    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=db_rows),
    ), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=10,
                contact_query=None,
            )
        )

    assert [supplier.name for supplier in response.suppliers] == ["Acme Precision Metals", "Bravo Molding"]
    acme = response.suppliers[0]
    assert acme.interaction_count == 12
    assert acme.website == "https://acme.example"
    assert acme.last_project_id == "proj-runtime-1"


def test_dashboard_contacts_service_merges_with_query_filter_before_limit():
    db_rows = [
        {
            "supplier_id": "11111111-1111-1111-1111-111111111111",
            "name": "Acme Precision Metals",
            "website": "https://acme.example",
            "email": "sales@acme.example",
            "phone": None,
            "city": "Detroit",
            "country": "USA",
            "interaction_count": 12,
            "project_count": 3,
            "last_interaction_at": 1710000000.0,
            "last_project_id": "proj-db-1",
        }
    ]
    runtime_projects = [
        {
            "id": "proj-runtime-1",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-20T10:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "11111111-1111-1111-1111-111111111111",
                        "name": "Acme Precision Metals",
                        "email": "sales@acme.example",
                    },
                    {
                        "supplier_id": "33333333-3333-3333-3333-333333333333",
                        "name": "Acme Plastics",
                        "email": "contact@acmeplastics.example",
                    },
                ]
            },
        }
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=runtime_projects)

    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=db_rows),
    ), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=1,
                contact_query="acme",
            )
        )

    assert response.count == 1
    assert [supplier.name for supplier in response.suppliers] == ["Acme Precision Metals"]

def test_contact_matches_query_matches_name_email_phone_and_location():
    contact = {
        "name": "Acme Precision Metals",
        "email": "sales@acme.example",
        "phone": "+1 (312) 555-0142",
        "website": "https://acme.example",
        "city": "Detroit",
        "country": "USA",
    }

    assert _contact_matches_query(contact, "precision")
    assert _contact_matches_query(contact, "sales@acme")
    assert _contact_matches_query(contact, "555-0142")
    assert _contact_matches_query(contact, "3125550142")
    assert _contact_matches_query(contact, "5550142")
    assert _contact_matches_query(contact, "detroit")
    assert not _contact_matches_query(contact, "toronto")
    assert not _contact_matches_query(contact, "555-9999")
    assert not _contact_matches_query(contact, "9999999")


def test_dashboard_contacts_service_runtime_fallback_matches_phone_digits_query():
    runtime_projects = [
        {
            "id": "proj-runtime-phone",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "updated_at": "2026-03-20T10:00:00+00:00",
            "discovery_results": {
                "suppliers": [
                    {
                        "supplier_id": "11111111-1111-1111-1111-111111111111",
                        "name": "Acme Precision Metals",
                        "website": "https://acme.example",
                        "email": "sales@acme.example",
                        "phone": "+1 (312) 555-0142",
                        "city": "Detroit",
                        "country": "USA",
                    },
                    {
                        "supplier_id": "22222222-2222-2222-2222-222222222222",
                        "name": "Bravo Tooling",
                        "email": "hello@bravo.example",
                        "phone": "+1 (773) 555-0100",
                    },
                ]
            },
        }
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=runtime_projects)

    with patch("app.services.dashboard_service._ensure_dashboard_schema", new=AsyncMock()), patch(
        "app.services.dashboard_service.async_session_factory"
    ) as session_factory, patch(
        "app.services.dashboard_service.dashboard_repo.list_supplier_contacts_for_user",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        session_factory.return_value.__aenter__ = AsyncMock(return_value=object())
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        response = asyncio.run(
            get_dashboard_contacts_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=10,
                contact_query="3125550142",
            )
        )

    assert response.count == 1
    assert [supplier.name for supplier in response.suppliers] == ["Acme Precision Metals"]


def test_dashboard_activity_service_falls_back_to_runtime_timeline_when_db_empty():
    projects = [
        {
            "id": "proj-runtime-new",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "title": "New runtime project",
            "timeline_events": [
                {
                    "id": "evt-runtime-new",
                    "timestamp": 300.0,
                    "event_type": "project_created",
                    "title": "Project started",
                    "description": "Started sourcing.",
                    "priority": "info",
                }
            ],
        },
        {
            "id": "proj-runtime-old",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "title": "Old runtime project",
            "timeline_events": [
                {
                    "id": "evt-runtime-old",
                    "timestamp": 200.0,
                    "event_type": "supplier_verified",
                    "title": "Supplier verified",
                    "description": "Verification done.",
                    "priority": "info",
                }
            ],
        },
        {
            "id": "proj-other-user",
            "user_id": "00000000-0000-0000-0000-000000000099",
            "title": "Other user project",
            "timeline_events": [
                {
                    "id": "evt-other-user",
                    "timestamp": 999.0,
                    "event_type": "project_created",
                    "title": "Other project started",
                    "description": "Should not appear.",
                    "priority": "info",
                }
            ],
        },
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=projects)

    with patch("app.services.dashboard_service._db_activity_for_user", new=AsyncMock(return_value=[])), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        events, next_cursor = asyncio.run(
            get_dashboard_activity_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=2,
                cursor=None,
            )
        )

    assert [event.id for event in events] == ["evt-runtime-new", "evt-runtime-old"]
    assert [event.project_name for event in events] == ["New runtime project", "Old runtime project"]
    assert next_cursor == "200.0"


def test_dashboard_activity_service_runtime_fallback_honors_cursor():
    projects = [
        {
            "id": "proj-runtime",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "title": "Runtime project",
            "timeline_events": [
                {
                    "id": "evt-runtime-300",
                    "timestamp": 300.0,
                    "event_type": "project_created",
                    "title": "Project started",
                    "description": "Started sourcing.",
                    "priority": "info",
                },
                {
                    "id": "evt-runtime-250",
                    "timestamp": 250.0,
                    "event_type": "supplier_contacted",
                    "title": "Supplier contacted",
                    "description": "Email sent.",
                    "priority": "info",
                },
                {
                    "id": "evt-runtime-100",
                    "timestamp": 100.0,
                    "event_type": "supplier_responded",
                    "title": "Supplier responded",
                    "description": "Quote received.",
                    "priority": "info",
                },
            ],
        }
    ]
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=projects)

    with patch("app.services.dashboard_service._db_activity_for_user", new=AsyncMock(return_value=[])), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        events, next_cursor = asyncio.run(
            get_dashboard_activity_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=10,
                cursor=250.0,
            )
        )

    assert [event.id for event in events] == ["evt-runtime-100"]
    assert next_cursor == "100.0"


def test_dashboard_activity_service_runtime_fallback_returns_no_cursor_without_events():
    store = AsyncMock()
    store.list_projects = AsyncMock(return_value=[])

    with patch("app.services.dashboard_service._db_activity_for_user", new=AsyncMock(return_value=[])), patch(
        "app.services.dashboard_service.get_project_store",
        return_value=store,
    ):
        events, next_cursor = asyncio.run(
            get_dashboard_activity_for_user(
                user_id="00000000-0000-0000-0000-000000000001",
                limit=5,
                cursor=None,
            )
        )

    assert events == []
    assert next_cursor is None
