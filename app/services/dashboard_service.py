"""Dashboard summary/activity orchestration service."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.database import async_session_factory, engine
from app.models.dashboard import ProjectEvent
from app.repositories import dashboard_repository as dashboard_repo
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardAttentionItem,
    DashboardContactsResponse,
    DashboardGreeting,
    DashboardProjectCard,
    DashboardProjectStats,
    DashboardSummaryResponse,
    DashboardSupplierContact,
)
from app.schemas.proactive import ProactiveAlert
from app.services.project_store import get_project_store

logger = logging.getLogger(__name__)

_dashboard_schema_ready = False

_PHASE_LABELS = {
    "parsing": "Brief",
    "clarifying": "Brief",
    "steering": "Brief",
    "discovering": "Search",
    "verifying": "Search",
    "comparing": "Compare",
    "recommending": "Compare",
    "outreaching": "Outreach",
    "complete": "Order placed",
    "failed": "Failed",
    "canceled": "Canceled",
}

_STAGE_PROGRESS = {
    "parsing": 1,
    "clarifying": 1,
    "steering": 1,
    "discovering": 2,
    "verifying": 2,
    "comparing": 3,
    "recommending": 3,
    "outreaching": 4,
    "complete": 6,
    "failed": 1,
    "canceled": 1,
}

_ACTIVE_STATUSES = {
    "parsing",
    "clarifying",
    "discovering",
    "verifying",
    "steering",
    "comparing",
    "recommending",
    "outreaching",
}


async def _ensure_dashboard_schema() -> None:
    global _dashboard_schema_ready
    if _dashboard_schema_ready:
        return

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: ProjectEvent.__table__.create(sync_conn, checkfirst=True))
    _dashboard_schema_ready = True


def _first_name(full_name: str | None, email: str | None) -> str:
    if full_name:
        return full_name.strip().split(" ")[0]
    if email:
        return email.split("@")[0]
    return "there"


def _time_label_now() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _to_relative_time(epoch_seconds: float | None) -> str:
    if not epoch_seconds:
        return "just now"
    now = datetime.now(timezone.utc).timestamp()
    delta = max(0, int(now - epoch_seconds))

    if delta < 60:
        return "just now"
    if delta < 3600:
        mins = delta // 60
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    if delta < 86400:
        hours = delta // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if delta < 172800:
        return "Yesterday"
    days = delta // 86400
    return f"{days} days ago"


def _truncate(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _price_from_text(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _best_price_label(project: dict[str, Any]) -> str | None:
    best: float | None = None
    currency = "$"

    comparison = (project.get("comparison_result") or {}).get("comparisons") or []
    for row in comparison:
        for key in ("estimated_landed_cost", "estimated_unit_price"):
            value = _price_from_text(row.get(key))
            if value is None:
                continue
            if best is None or value < best:
                best = value

    quotes = (project.get("outreach_state") or {}).get("parsed_quotes") or []
    for quote in quotes:
        value = _price_from_text(quote.get("unit_price"))
        if value is None:
            continue
        if best is None or value < best:
            best = value
        quote_currency = quote.get("currency") or "USD"
        if quote_currency.upper() == "USD":
            currency = "$"
        else:
            currency = quote_currency.upper() + " "

    if best is None:
        return None
    if currency == "$":
        return f"${best:,.2f}"
    return f"{currency}{best:,.2f}"


def _project_visual_variant(project_id: str) -> int:
    digest = hashlib.md5(project_id.encode("utf-8")).hexdigest()  # noqa: S324
    return int(digest[:2], 16) % 3 + 1


def _is_active_status(status: Any) -> bool:
    return str(status or "").strip().lower() in _ACTIVE_STATUSES


def _normalized_status(project: dict[str, Any]) -> str:
    status = str(project.get("status") or "").strip().lower()
    if status:
        return status
    return str(project.get("current_stage") or "").strip().lower()


def _normalized_stage(project: dict[str, Any]) -> str:
    stage = str(project.get("current_stage") or "").strip().lower()
    if stage:
        return stage
    return _normalized_status(project)


def _parse_sort_timestamp(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _normalized_query_tokens(query: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(query or "").lower()).strip()
    if not cleaned:
        return []
    return [token for token in cleaned.split(" ") if token]


def _project_matches_query_tokens(project: dict[str, Any], query_tokens: list[str]) -> bool:
    if not query_tokens:
        return True
    searchable = " ".join(
        [
            str(project.get("title") or ""),
            str(project.get("product_description") or ""),
        ]
    ).lower()
    normalized_searchable = re.sub(r"[^a-z0-9]+", " ", searchable)
    return all(token in normalized_searchable for token in query_tokens)


def _sorted_projects_for_dashboard(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _sort_key(project: dict[str, Any]) -> tuple[int, float, float, str]:
        status = _normalized_status(project)
        updated_at = _parse_sort_timestamp(project.get("updated_at"))
        created_at = _parse_sort_timestamp(project.get("created_at"))
        return (
            0 if _is_active_status(status) else 1,
            -updated_at,
            -created_at,
            str(project.get("id") or ""),
        )

    return sorted(projects, key=_sort_key)


def _project_status_note(project: dict[str, Any]) -> str:
    status = _normalized_status(project) or "unknown"
    stage = _normalized_stage(project) or status
    outreach = project.get("outreach_state") or {}

    if status == "clarifying":
        questions = len(project.get("clarifying_questions") or [])
        return f"Waiting on {questions} clarification answer{'s' if questions != 1 else ''}"
    if status == "failed":
        return "Run failed. Open project to retry."
    if status == "canceled":
        return "Run canceled."

    statuses = outreach.get("supplier_statuses") or []
    responded = sum(1 for s in statuses if s.get("response_received"))
    awaiting = sum(
        1
        for s in statuses
        if s.get("email_sent") and not s.get("response_received") and not s.get("excluded")
    )
    excluded = sum(1 for s in statuses if s.get("excluded"))

    if responded > 0:
        parts = [f"{responded} supplier response{'s' if responded != 1 else ''} received"]
        if awaiting > 0:
            parts.append(f"{awaiting} awaiting")
        if excluded > 0:
            parts.append(f"{excluded} removed")
        return " - ".join(parts)

    if outreach.get("quick_approval_decision") == "declined":
        return "Outreach skipped. Send anytime."
    if project.get("recommendation_result") and outreach.get("quick_approval_decision") is None:
        return "Ready for outreach approval."

    if status == "complete":
        return "Recommendation ready."

    stage_label = _PHASE_LABELS.get(stage, stage.replace("_", " ").title())
    return f"{stage_label} in progress"


def _project_progress_step(project: dict[str, Any]) -> int:
    stage = _normalized_stage(project) or "parsing"
    base = _STAGE_PROGRESS.get(stage, 1)

    outreach = project.get("outreach_state") or {}
    quotes = outreach.get("parsed_quotes") or []
    if quotes:
        base = max(base, 5)
    if _normalized_status(project) == "complete" and quotes:
        base = 6
    return max(1, min(base, 6))


def _project_card(project: dict[str, Any]) -> DashboardProjectCard:
    project_id = str(project.get("id"))
    parsed = project.get("parsed_requirements") or {}
    outreach = project.get("outreach_state") or {}

    name = parsed.get("product_type") or project.get("title") or "Untitled project"
    description = _truncate(project.get("product_description") or "No description.")
    stage = _normalized_stage(project) or "parsing"
    status = _normalized_status(project) or "unknown"

    stats = DashboardProjectStats(
        quotes_count=max(
            len(outreach.get("parsed_quotes") or []),
            len((project.get("recommendation_result") or {}).get("recommendations") or []),
        ),
        best_price=_best_price_label(project),
        samples_sent=sum(
            1
            for e in (outreach.get("events") or [])
            if str(e.get("event_type", "")).startswith("sample_")
        ),
    )

    return DashboardProjectCard(
        id=project_id,
        name=name,
        description=description,
        phase_label=_PHASE_LABELS.get(stage, stage.replace("_", " ").title()),
        status=status,
        progress_step=_project_progress_step(project),
        progress_total=6,
        stats=stats,
        status_note=_project_status_note(project),
        visual_variant=_project_visual_variant(project_id),
    )


def _attention_items(projects: list[dict[str, Any]]) -> list[DashboardAttentionItem]:
    items: list[DashboardAttentionItem] = []

    for project in projects:
        project_id = str(project.get("id"))
        name = (project.get("parsed_requirements") or {}).get("product_type") or project.get("title") or "project"
        status = str(project.get("status") or "")
        outreach = project.get("outreach_state") or {}

        if status == "clarifying":
            questions = len(project.get("clarifying_questions") or [])
            items.append(
                DashboardAttentionItem(
                    id=f"{project_id}:clarifying",
                    kind="clarifying_required",
                    priority="high",
                    title="A few details are missing",
                    subtitle=f"Answer {questions} quick question{'s' if questions != 1 else ''} to continue {name}.",
                    project_id=project_id,
                    cta="Answer questions",
                    target_phase="brief",
                )
            )

        if project.get("recommendation_result") and outreach.get("quick_approval_decision") is None:
            items.append(
                DashboardAttentionItem(
                    id=f"{project_id}:outreach_approval",
                    kind="outreach_approval_needed",
                    priority="high",
                    title="Outreach approval needed",
                    subtitle=f"Top suppliers are ready for {name}. Approve outreach to send emails.",
                    project_id=project_id,
                    cta="Approve outreach",
                    target_phase="outreach",
                )
            )

        failed_sends = [
            s
            for s in (outreach.get("supplier_statuses") or [])
            if s.get("delivery_status") == "failed"
        ]
        if failed_sends:
            items.append(
                DashboardAttentionItem(
                    id=f"{project_id}:send_failed",
                    kind="send_failed",
                    priority="high",
                    title="Some outreach emails failed",
                    subtitle=f"{len(failed_sends)} supplier email send failure{'s' if len(failed_sends) != 1 else ''} in {name}.",
                    project_id=project_id,
                    cta="Review outreach",
                    target_phase="outreach",
                )
            )

        parsed_quotes = outreach.get("parsed_quotes") or []
        if parsed_quotes:
            items.append(
                DashboardAttentionItem(
                    id=f"{project_id}:quote_ready",
                    kind="quote_ready",
                    priority="medium",
                    title="New quote data is ready",
                    subtitle=f"{len(parsed_quotes)} quote{'s' if len(parsed_quotes) != 1 else ''} parsed for {name}.",
                    project_id=project_id,
                    cta="Review comparison",
                    target_phase="compare",
                )
            )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda item: priority_order.get(item.priority, 9))
    return items[:8]


def _activity_from_timeline(project: dict[str, Any], project_name: str) -> list[DashboardActivityItem]:
    events: list[DashboardActivityItem] = []
    for raw in project.get("timeline_events") or []:
        at = float(raw.get("timestamp") or 0)
        events.append(
            DashboardActivityItem(
                id=str(raw.get("id") or f"{project.get('id')}:{raw.get('event_type')}:{at}"),
                at=at,
                time_label=_to_relative_time(at),
                title=str(raw.get("title") or "Project update"),
                description=str(raw.get("description") or ""),
                project_id=str(project.get("id")) if project.get("id") else None,
                project_name=project_name,
                type=str(raw.get("event_type") or "project_update"),
                priority=str(raw.get("priority") or "info"),
                payload=raw.get("payload") or {},
            )
        )
    return events


async def _runtime_activity_for_user(
    *,
    user_id: str,
    limit: int,
    cursor: float | None,
) -> list[DashboardActivityItem]:
    try:
        projects = await get_project_store().list_projects()
    except Exception:  # noqa: BLE001
        logger.warning("Dashboard runtime activity query failed", exc_info=True)
        return []

    user_projects = [p for p in projects if str(p.get("user_id")) == str(user_id)]
    fallback_events: list[DashboardActivityItem] = []
    for project in user_projects:
        name = (project.get("parsed_requirements") or {}).get("product_type") or project.get("title") or "Project"
        fallback_events.extend(_activity_from_timeline(project, name))

    fallback_events.sort(key=lambda item: (-item.at, item.id))

    if cursor is not None:
        fallback_events = [item for item in fallback_events if item.at < cursor]

    return fallback_events[: max(1, limit)]


async def _db_activity_for_user(user_id: str, limit: int, cursor: float | None) -> list[DashboardActivityItem]:
    try:
        await _ensure_dashboard_schema()
        before = None
        if cursor:
            before = datetime.fromtimestamp(cursor, tz=timezone.utc)

        async with async_session_factory() as session:
            rows = await dashboard_repo.list_project_events(
                session=session,
                user_id=user_id,
                limit=limit,
                before=before,
            )
    except Exception:  # noqa: BLE001
        logger.warning("Dashboard DB activity query failed; falling back to runtime timeline", exc_info=True)
        return []

    return [
        DashboardActivityItem(
            id=row["id"],
            at=float(row.get("created_at") or 0),
            time_label=_to_relative_time(float(row.get("created_at") or 0)),
            title=row.get("title") or "Project update",
            description=row.get("description") or "",
            project_id=row.get("project_id"),
            type=row.get("event_type") or "project_update",
            priority=row.get("priority") or "info",
            payload=row.get("payload") or {},
        )
        for row in rows
    ]


async def get_dashboard_summary_for_user(
    *,
    user_id: str,
    full_name: str | None,
    email: str | None,
    project_statuses: set[str] | None = None,
    project_query: str | None = None,
) -> DashboardSummaryResponse:
    store = get_project_store()
    projects = await store.list_projects()
    user_projects = [p for p in projects if str(p.get("user_id")) == str(user_id)]
    sorted_user_projects = _sorted_projects_for_dashboard(user_projects)
    filtered_projects = sorted_user_projects
    if project_statuses:
        filtered_projects = [
            project
            for project in sorted_user_projects
            if _normalized_status(project) in project_statuses
        ]
    query_tokens = _normalized_query_tokens(project_query or "")
    if query_tokens:
        filtered_projects = [
            project
            for project in filtered_projects
            if _project_matches_query_tokens(project, query_tokens)
        ]

    project_cards = [_project_card(project) for project in filtered_projects]
    attention = _attention_items(filtered_projects)
    activity = await _db_activity_for_user(user_id=user_id, limit=20, cursor=None)

    if not activity:
        # Fallback to in-project timeline events so UI still has a feed without DB events.
        activity = await _runtime_activity_for_user(user_id=user_id, limit=20, cursor=None)

    project_name_by_id = {card.id: card.name for card in project_cards}
    for event in activity:
        if event.project_id and not event.project_name:
            event.project_name = project_name_by_id.get(event.project_id)

    active_projects = sum(1 for p in user_projects if _is_active_status(_normalized_status(p)))
    first = _first_name(full_name, email)
    daytime = _time_label_now()

    proactive_alerts: list[ProactiveAlert] = []
    seen_alert_ids: set[str] = set()
    for project in user_projects:
        for raw_alert in project.get("proactive_alerts") or []:
            if not isinstance(raw_alert, dict):
                continue
            try:
                alert = ProactiveAlert(**raw_alert)
            except Exception:
                continue
            if alert.id in seen_alert_ids:
                continue
            seen_alert_ids.add(alert.id)
            proactive_alerts.append(alert)
    proactive_alerts.sort(key=lambda item: item.created_at, reverse=True)

    greeting = DashboardGreeting(
        time_label=f"{datetime.now().strftime('%A')} {daytime}",
        user_first_name=first,
        active_projects=active_projects,
        headline=f"Good {daytime}, {first}",
        body=(
            f"You have {active_projects} active project{'s' if active_projects != 1 else ''}. "
            "Procurement AI is handling supplier discovery, comparisons, and outreach updates in the background."
        ),
    )

    return DashboardSummaryResponse(
        greeting=greeting,
        attention=attention,
        projects=project_cards,
        recent_activity=activity,
        proactive_alerts=proactive_alerts[:8],
    )


async def get_dashboard_activity_for_user(
    *,
    user_id: str,
    limit: int,
    cursor: float | None,
) -> tuple[list[DashboardActivityItem], str | None]:
    events = await _db_activity_for_user(user_id=user_id, limit=limit, cursor=cursor)
    if not events:
        events = await _runtime_activity_for_user(user_id=user_id, limit=limit, cursor=cursor)
    next_cursor = None
    if events:
        next_cursor = str(events[-1].at)
    return events, next_cursor


def _contact_matches_query(contact: dict[str, Any], query: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True
    searchable = [
        str(contact.get("name") or ""),
        str(contact.get("email") or ""),
        str(contact.get("phone") or ""),
        str(contact.get("website") or ""),
        str(contact.get("city") or ""),
        str(contact.get("country") or ""),
    ]
    if any(needle in value.lower() for value in searchable):
        return True

    phone_needle = re.sub(r"\D", "", needle)
    if not phone_needle:
        return False

    phone_value = re.sub(r"\D", "", str(contact.get("phone") or ""))
    return bool(phone_value) and phone_needle in phone_value


def _runtime_contact_key_and_id(contact: dict[str, Any]) -> tuple[str, str]:
    supplier_id = str(contact.get("supplier_id") or "").strip()
    if supplier_id:
        return f"id:{supplier_id}", supplier_id

    normalized_name = str(contact.get("name") or "").strip().lower()
    normalized_email = str(contact.get("email") or "").strip().lower()
    normalized_phone = str(contact.get("phone") or "").strip().lower()
    normalized_website = str(contact.get("website") or "").strip().lower()
    raw_key = "|".join([normalized_name, normalized_email, normalized_phone, normalized_website])
    if not raw_key.strip("|"):
        raw_key = "unknown"
    stable_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"dashboard-runtime-contact:{raw_key}"))
    return f"derived:{raw_key}", stable_id


async def _runtime_contacts_for_user(
    *,
    user_id: str,
    limit: int,
    contact_query: str | None,
) -> list[dict[str, Any]]:
    try:
        projects = await get_project_store().list_projects()
    except Exception:  # noqa: BLE001
        logger.warning("Dashboard runtime contacts query failed", exc_info=True)
        return []

    normalized_query = (contact_query or "").strip()
    aggregated: dict[str, dict[str, Any]] = {}
    seen_projects_by_supplier: dict[str, set[str]] = {}

    for project in projects:
        if str(project.get("user_id")) != str(user_id):
            continue

        project_id = str(project.get("id") or "")
        project_ts = _parse_sort_timestamp(project.get("updated_at") or project.get("created_at"))
        suppliers = ((project.get("discovery_results") or {}).get("suppliers") or [])
        for supplier in suppliers:
            if not isinstance(supplier, dict):
                continue

            contact = {
                "supplier_id": supplier.get("supplier_id"),
                "name": str(supplier.get("name") or "").strip(),
                "website": supplier.get("website"),
                "email": supplier.get("email"),
                "phone": supplier.get("phone"),
                "city": supplier.get("city"),
                "country": supplier.get("country"),
            }
            if not contact["name"]:
                continue
            if normalized_query and not _contact_matches_query(contact, normalized_query):
                continue

            supplier_key, supplier_id = _runtime_contact_key_and_id(contact)
            project_ids = seen_projects_by_supplier.setdefault(supplier_key, set())

            existing = aggregated.get(supplier_key)
            if not existing:
                aggregated[supplier_key] = {
                    "supplier_id": supplier_id,
                    "name": contact["name"],
                    "website": contact["website"],
                    "email": contact["email"],
                    "phone": contact["phone"],
                    "city": contact["city"],
                    "country": contact["country"],
                    "interaction_count": 1,
                    "project_count": 1 if project_id else 0,
                    "last_interaction_at": project_ts or None,
                    "last_project_id": project_id or None,
                }
                if project_id:
                    project_ids.add(project_id)
                continue

            existing["interaction_count"] += 1
            if project_id and project_id not in project_ids:
                project_ids.add(project_id)
                existing["project_count"] += 1
            if project_ts >= float(existing.get("last_interaction_at") or 0):
                existing["last_interaction_at"] = project_ts or None
                existing["last_project_id"] = project_id or existing.get("last_project_id")

            if not existing.get("email") and contact.get("email"):
                existing["email"] = contact["email"]
            if not existing.get("phone") and contact.get("phone"):
                existing["phone"] = contact["phone"]
            if not existing.get("website") and contact.get("website"):
                existing["website"] = contact["website"]
            if not existing.get("city") and contact.get("city"):
                existing["city"] = contact["city"]
            if not existing.get("country") and contact.get("country"):
                existing["country"] = contact["country"]

    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -int(row.get("interaction_count") or 0),
            -float(row.get("last_interaction_at") or 0),
            str(row.get("name") or "").lower(),
        )
    )
    return rows[: max(1, min(limit, 200))]


def _merge_contact_rows(
    *,
    primary_rows: list[dict[str, Any]],
    supplemental_rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def _upsert(row: dict[str, Any]) -> None:
        key, supplier_id = _runtime_contact_key_and_id(row)
        existing = merged.get(key)
        if not existing:
            merged[key] = {
                "supplier_id": row.get("supplier_id") or supplier_id,
                "name": row.get("name"),
                "website": row.get("website"),
                "email": row.get("email"),
                "phone": row.get("phone"),
                "city": row.get("city"),
                "country": row.get("country"),
                "interaction_count": int(row.get("interaction_count") or 0),
                "project_count": int(row.get("project_count") or 0),
                "last_interaction_at": row.get("last_interaction_at"),
                "last_project_id": row.get("last_project_id"),
            }
            return

        existing["interaction_count"] = max(
            int(existing.get("interaction_count") or 0),
            int(row.get("interaction_count") or 0),
        )
        existing["project_count"] = max(
            int(existing.get("project_count") or 0),
            int(row.get("project_count") or 0),
        )

        row_last_interaction = float(row.get("last_interaction_at") or 0)
        existing_last_interaction = float(existing.get("last_interaction_at") or 0)
        if row_last_interaction >= existing_last_interaction:
            existing["last_interaction_at"] = row.get("last_interaction_at")
            existing["last_project_id"] = row.get("last_project_id") or existing.get("last_project_id")

        if not existing.get("email") and row.get("email"):
            existing["email"] = row.get("email")
        if not existing.get("phone") and row.get("phone"):
            existing["phone"] = row.get("phone")
        if not existing.get("website") and row.get("website"):
            existing["website"] = row.get("website")
        if not existing.get("city") and row.get("city"):
            existing["city"] = row.get("city")
        if not existing.get("country") and row.get("country"):
            existing["country"] = row.get("country")

    for row in primary_rows:
        _upsert(row)
    for row in supplemental_rows:
        _upsert(row)

    rows = list(merged.values())
    rows.sort(
        key=lambda row: (
            -int(row.get("interaction_count") or 0),
            -float(row.get("last_interaction_at") or 0),
            str(row.get("name") or "").lower(),
        )
    )
    return rows[: max(1, min(limit, 200))]


async def get_dashboard_contacts_for_user(
    *,
    user_id: str,
    limit: int = 50,
    contact_query: str | None = None,
) -> DashboardContactsResponse:
    normalized_query = (contact_query or "").strip()
    query_filter = normalized_query or None

    try:
        await _ensure_dashboard_schema()
        async with async_session_factory() as session:
            rows = await dashboard_repo.list_supplier_contacts_for_user(
                session=session,
                user_id=user_id,
                limit=limit,
                contact_query=query_filter,
            )
    except Exception:  # noqa: BLE001
        logger.warning("Dashboard contacts query failed", exc_info=True)
        rows = await _runtime_contacts_for_user(
            user_id=user_id,
            limit=limit,
            contact_query=query_filter,
        )
    else:
        runtime_rows = await _runtime_contacts_for_user(
            user_id=user_id,
            limit=200,
            contact_query=query_filter,
        )
        rows = _merge_contact_rows(
            primary_rows=rows,
            supplemental_rows=runtime_rows,
            limit=limit,
        )

    suppliers = [DashboardSupplierContact(**row) for row in rows]
    return DashboardContactsResponse(suppliers=suppliers, count=len(suppliers))
