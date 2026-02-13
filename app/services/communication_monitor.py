"""Outreach communication monitor helpers.

Keeps a durable, per-project record of outbound/inbound communications,
delivery status changes, and inbox polling metadata.
"""

from __future__ import annotations

import time
from typing import Any

from app.schemas.agent_state import (
    CommunicationMessage,
    CommunicationMonitorState,
    CommunicationStatusEvent,
    OutreachState,
)


def _normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def _normalize_email_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        email = _normalize_email(raw)
        if not email or email in seen:
            continue
        seen.add(email)
        normalized.append(email)
    return normalized


def _preview(text: str | None, limit: int = 240) -> str | None:
    if not text:
        return None
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _thread_key(supplier_index: int | None, to_email: str | None) -> str | None:
    if supplier_index is not None:
        return f"supplier:{supplier_index}"
    email = _normalize_email(to_email)
    if email:
        return f"email:{email}"
    return None


def _append_status_event(
    message: CommunicationMessage,
    *,
    event_type: str,
    status: str,
    source: str,
    details: dict[str, Any] | None = None,
    timestamp: float | None = None,
) -> None:
    message.events.append(
        CommunicationStatusEvent(
            event_type=event_type,
            status=status,
            source=source,
            timestamp=timestamp or time.time(),
            details=details or {},
        )
    )


def _recompute_totals(monitor: CommunicationMonitorState) -> None:
    outbound = [m for m in monitor.messages if m.direction == "outbound"]
    inbound = [m for m in monitor.messages if m.direction == "inbound"]
    failures = [
        m
        for m in monitor.messages
        if m.delivery_status in {"failed", "bounced", "complained"}
    ]
    replies = [m for m in inbound if m.supplier_index is not None]

    monitor.total_outbound = len(outbound)
    monitor.total_inbound = len(inbound)
    monitor.total_replies = len(replies)
    monitor.total_failures = len(failures)


def ensure_monitor(outreach: OutreachState, owner_email: str | None = None) -> CommunicationMonitorState:
    monitor = outreach.communication_monitor or CommunicationMonitorState()
    normalized_owner = _normalize_email(owner_email)
    if normalized_owner and not monitor.owner_email:
        monitor.owner_email = normalized_owner
    outreach.communication_monitor = monitor
    return monitor


def set_owner_email(outreach: OutreachState, owner_email: str | None) -> None:
    monitor = ensure_monitor(outreach, owner_email=owner_email)
    normalized_owner = _normalize_email(owner_email)
    if normalized_owner:
        monitor.owner_email = normalized_owner


def find_message_by_resend_id(
    outreach: OutreachState,
    resend_email_id: str,
) -> CommunicationMessage | None:
    monitor = ensure_monitor(outreach)
    for message in monitor.messages:
        if message.resend_email_id == resend_email_id:
            return message
    return None


def find_message_by_inbox_id(
    outreach: OutreachState,
    inbox_message_id: str,
) -> CommunicationMessage | None:
    monitor = ensure_monitor(outreach)
    for message in monitor.messages:
        if message.inbox_message_id == inbox_message_id:
            return message
    return None


def record_outbound_email(
    outreach: OutreachState,
    *,
    supplier_index: int | None,
    supplier_name: str | None,
    to_email: str | None,
    from_email: str | None,
    cc_emails: list[str] | None,
    subject: str | None,
    body: str | None,
    resend_email_id: str | None,
    delivery_status: str,
    source: str,
    event_type: str,
    details: dict[str, Any] | None = None,
) -> CommunicationMessage:
    monitor = ensure_monitor(outreach)
    now = time.time()

    message: CommunicationMessage | None = None
    if resend_email_id:
        message = find_message_by_resend_id(outreach, resend_email_id)

    if message is None:
        key = (
            f"outbound:{resend_email_id}"
            if resend_email_id
            else f"outbound:{supplier_index if supplier_index is not None else 'na'}:{int(now * 1000)}"
        )
        message = CommunicationMessage(
            message_key=key,
            direction="outbound",
            supplier_index=supplier_index,
            supplier_name=supplier_name,
            to_email=_normalize_email(to_email),
            from_email=_normalize_email(from_email),
            cc_emails=_normalize_email_list(cc_emails),
            subject=subject,
            body_preview=_preview(body),
            resend_email_id=resend_email_id,
            thread_key=_thread_key(supplier_index, to_email),
            source=source,
            delivery_status=delivery_status,
            created_at=now,
            updated_at=now,
        )
        monitor.messages.append(message)
    else:
        message.supplier_index = supplier_index if supplier_index is not None else message.supplier_index
        message.supplier_name = supplier_name or message.supplier_name
        message.to_email = _normalize_email(to_email) or message.to_email
        message.from_email = _normalize_email(from_email) or message.from_email
        normalized_cc = _normalize_email_list(cc_emails)
        if normalized_cc:
            message.cc_emails = normalized_cc
        message.subject = subject or message.subject
        message.body_preview = _preview(body) or message.body_preview
        message.delivery_status = delivery_status or message.delivery_status
        message.source = source or message.source
        message.updated_at = now

    _append_status_event(
        message,
        event_type=event_type,
        status=delivery_status,
        source=source,
        details=details,
        timestamp=now,
    )
    _recompute_totals(monitor)
    return message


def apply_delivery_event(
    outreach: OutreachState,
    *,
    resend_email_id: str,
    event_type: str,
    delivery_status: str,
    source: str,
    details: dict[str, Any] | None = None,
    timestamp: float | None = None,
) -> bool:
    message = find_message_by_resend_id(outreach, resend_email_id)
    if message is None:
        return False

    monitor = ensure_monitor(outreach)
    now = timestamp or time.time()
    message.delivery_status = delivery_status
    message.updated_at = now
    _append_status_event(
        message,
        event_type=event_type,
        status=delivery_status,
        source=source,
        details=details,
        timestamp=now,
    )
    _recompute_totals(monitor)
    return True


def record_inbox_check(
    outreach: OutreachState,
    *,
    source: str,
    message_count: int,
    checked_at: float | None = None,
) -> None:
    monitor = ensure_monitor(outreach)
    monitor.last_inbox_check_at = checked_at or time.time()
    monitor.last_inbox_check_source = source
    monitor.last_inbox_message_count = message_count


def record_inbound_email(
    outreach: OutreachState,
    *,
    inbox_message_id: str | None,
    sender: str | None,
    subject: str | None,
    body: str | None,
    snippet: str | None,
    matched_sender: str | None,
    supplier_index: int | None,
    supplier_name: str | None,
    source: str,
    received_at: float | None = None,
) -> tuple[CommunicationMessage, bool]:
    monitor = ensure_monitor(outreach)
    now = received_at or time.time()
    sender_email = _normalize_email(sender)
    message = (
        find_message_by_inbox_id(outreach, inbox_message_id)
        if inbox_message_id
        else None
    )
    is_new = message is None

    if message is None:
        key = (
            f"inbound:{inbox_message_id}"
            if inbox_message_id
            else f"inbound:{supplier_index if supplier_index is not None else 'na'}:{int(now * 1000)}"
        )
        message = CommunicationMessage(
            message_key=key,
            direction="inbound",
            supplier_index=supplier_index,
            supplier_name=supplier_name,
            from_email=sender_email,
            subject=subject,
            body_preview=_preview(snippet or body),
            inbox_message_id=inbox_message_id,
            matched_sender=matched_sender,
            thread_key=_thread_key(supplier_index, None),
            source=source,
            delivery_status="received",
            created_at=now,
            updated_at=now,
        )
        monitor.messages.append(message)
    else:
        message.supplier_index = supplier_index if supplier_index is not None else message.supplier_index
        message.supplier_name = supplier_name or message.supplier_name
        message.from_email = sender_email or message.from_email
        message.subject = subject or message.subject
        message.body_preview = _preview(snippet or body) or message.body_preview
        message.matched_sender = matched_sender or message.matched_sender
        message.delivery_status = "received"
        message.updated_at = now

    _append_status_event(
        message,
        event_type="inbox_received",
        status="received",
        source=source,
        details={"matched_sender": matched_sender},
        timestamp=now,
    )
    _recompute_totals(monitor)
    return message, is_new


def mark_inbound_message_parsed(
    outreach: OutreachState,
    *,
    inbox_message_id: str | None,
    supplier_index: int | None,
    confidence_score: float | None = None,
    source: str = "inbox_parser",
) -> None:
    monitor = ensure_monitor(outreach)
    target: CommunicationMessage | None = None
    if inbox_message_id:
        target = find_message_by_inbox_id(outreach, inbox_message_id)

    if target is None and supplier_index is not None:
        for message in reversed(monitor.messages):
            if (
                message.direction == "inbound"
                and message.supplier_index == supplier_index
                and not message.parsed_response
            ):
                target = message
                break
    if target is None:
        return

    now = time.time()
    target.parsed_response = True
    target.updated_at = now
    _append_status_event(
        target,
        event_type="response_parsed",
        status="parsed",
        source=source,
        details={"confidence_score": confidence_score},
        timestamp=now,
    )
    _recompute_totals(monitor)
