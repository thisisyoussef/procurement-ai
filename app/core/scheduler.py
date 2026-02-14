"""Background scheduler for autonomous outreach operations.

Uses asyncio tasks managed by FastAPI's lifespan events.
Runs in the same process as the FastAPI app and persists updates
through the configured project store backend.

Loops:
  - Email queue processor (30s) — sends auto_queued drafts
  - Follow-up checker (1h) — generates and sends follow-ups for non-responsive suppliers
  - Inbox monitor (5m) — checks Gmail for supplier responses, auto-parses them
  - Phone escalation (1h) — initiates calls for bounced/unresponsive suppliers with phone numbers
"""

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.communication_monitor import (
    ensure_monitor,
    mark_inbound_message_parsed,
    record_inbound_email,
    record_inbox_check,
    record_outbound_email,
)
from app.services.project_contact import resolve_project_owner_email

logger = logging.getLogger(__name__)
settings = get_settings()

UNFULFILLMENT_PATTERNS = [
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bunable to\b",
    r"\bdo not manufacture\b",
    r"\bdo not produce\b",
    r"\boutside our capability\b",
    r"\bnot able to\b",
    r"\bwe don't offer\b",
    r"\bcan't meet\b",
]

# Singleton scheduler instance
_scheduler: "OutreachScheduler | None" = None


def get_scheduler() -> "OutreachScheduler":
    global _scheduler
    if _scheduler is None:
        _scheduler = OutreachScheduler()
    return _scheduler


class OutreachScheduler:
    """Manages periodic background tasks for autonomous outreach."""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._stats: dict[str, Any] = {
            "started_at": None,
            "emails_sent": 0,
            "follow_ups_sent": 0,
            "inbox_checks": 0,
            "phone_calls_initiated": 0,
            "responses_parsed": 0,
            "loop_runs": {
                "email_queue": 0,
                "follow_ups": 0,
                "inbox_monitor": 0,
                "phone_escalation": 0,
            },
            "last_run": {
                "email_queue": None,
                "follow_ups": None,
                "inbox_monitor": None,
                "phone_escalation": None,
            },
            "errors": [],
        }

    @property
    def stats(self) -> dict:
        return {**self._stats, "running": self._running}

    async def start(self):
        """Start all background loops."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._stats["started_at"] = time.time()

        self._tasks["email_queue"] = asyncio.create_task(
            self._loop("email_queue", 30, self._process_email_queues)
        )
        self._tasks["follow_ups"] = asyncio.create_task(
            self._loop("follow_ups", 3600, self._check_and_send_follow_ups)
        )
        self._tasks["inbox_monitor"] = asyncio.create_task(
            self._loop("inbox_monitor", 300, self._check_inboxes)
        )
        self._tasks["phone_escalation"] = asyncio.create_task(
            self._loop("phone_escalation", 3600, self._escalate_to_phone)
        )

        logger.info("OutreachScheduler started with %d background loops", len(self._tasks))

    async def stop(self):
        """Stop all background loops gracefully."""
        self._running = False
        for name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("OutreachScheduler stopped")

    async def _loop(self, name: str, interval_seconds: float, fn):
        """Generic loop wrapper with error handling."""
        # Initial delay to let the app start up
        await asyncio.sleep(5)

        while self._running:
            try:
                await fn()
                self._stats["loop_runs"][name] += 1
                self._stats["last_run"][name] = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = f"{name}: {type(e).__name__}: {str(e)}"
                logger.error("Scheduler loop %s failed: %s", name, error_msg)
                self._stats["errors"].append({
                    "loop": name,
                    "error": error_msg,
                    "time": time.time(),
                })
                # Keep only last 50 errors
                self._stats["errors"] = self._stats["errors"][-50:]

            await asyncio.sleep(interval_seconds)

    # ── Helpers ──────────────────────────────────────────────────

    async def _list_projects(self) -> list[dict[str, Any]]:
        """Load projects from the configured store."""
        from app.services.project_store import StoreUnavailableError, get_project_store

        store = get_project_store()
        try:
            return await store.list_projects()
        except StoreUnavailableError as exc:
            logger.warning("Scheduler: project store unavailable while listing projects: %s", exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("Scheduler: failed to list projects: %s", exc)
            return []

    async def _save_project(self, project: dict[str, Any]) -> None:
        """Persist a project through the configured store."""
        from app.services.project_store import StoreUnavailableError, get_project_store

        store = get_project_store()
        try:
            await store.save_project(project)
        except StoreUnavailableError as exc:
            logger.warning(
                "Scheduler: project store unavailable while saving project %s: %s",
                project.get("id"),
                exc,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Scheduler: failed to save project %s: %s",
                project.get("id"),
                exc,
            )

    def _get_outreach_state(self, project: dict):
        """Parse OutreachState from a project dict."""
        from app.schemas.agent_state import OutreachState
        raw = project.get("outreach_state")
        if not raw:
            return None
        return OutreachState(**raw) if isinstance(raw, dict) else raw

    async def _save_outreach_state(self, project: dict, outreach) -> None:
        """Serialize OutreachState back to the project dict."""
        project["outreach_state"] = outreach.model_dump(mode="json")
        await self._save_project(project)

    def _response_indicates_cannot_fulfill(self, quote_text: str | None, response_text: str) -> bool:
        text = f"{quote_text or ''}\n{response_text}".lower()
        return any(re.search(pattern, text) for pattern in UNFULFILLMENT_PATTERNS)

    def _exclude_supplier_from_project(
        self,
        project: dict,
        outreach,
        supplier_index: int,
        supplier_name: str,
        reason: str,
    ) -> None:
        if supplier_index not in outreach.excluded_suppliers:
            outreach.excluded_suppliers.append(supplier_index)

        for status in outreach.supplier_statuses:
            if status.supplier_index == supplier_index:
                status.excluded = True
                status.exclusion_reason = reason
                break

        discovery = project.get("discovery_results")
        if discovery and 0 <= supplier_index < len(discovery.get("suppliers", [])):
            discovery["suppliers"][supplier_index]["filtered_reason"] = "unable_to_fulfill"

        comparison = project.get("comparison_result")
        if comparison and comparison.get("comparisons"):
            comparison["comparisons"] = [
                c
                for c in comparison["comparisons"]
                if c.get("supplier_index") != supplier_index
            ]
            project["comparison_result"] = comparison

        recommendation = project.get("recommendation_result")
        if recommendation and recommendation.get("recommendations"):
            kept = [
                r
                for r in recommendation["recommendations"]
                if r.get("supplier_index") != supplier_index
            ]
            for rank, item in enumerate(kept, start=1):
                item["rank"] = rank
            recommendation["recommendations"] = kept
            project["recommendation_result"] = recommendation

    def _match_supplier_from_token(
        self,
        outreach,
        discovery_results,
        matched_token: str | None,
    ) -> tuple[int | None, str | None]:
        if not matched_token:
            return None, None

        token = matched_token.lower()
        for supplier_status in outreach.supplier_statuses:
            if supplier_status.excluded:
                continue
            idx = supplier_status.supplier_index
            if not (0 <= idx < len(discovery_results.suppliers)):
                continue
            supplier = discovery_results.suppliers[idx]
            if supplier.email and supplier.email.lower() in token:
                return idx, supplier.name
            if supplier.website:
                try:
                    domain = urlparse(supplier.website).netloc.replace("www.", "").lower()
                except Exception:  # noqa: BLE001
                    domain = ""
                if domain and domain in token:
                    return idx, supplier.name
        return None, None

    # ── Loop 1: Email Queue Processor ─────────────────────────────

    async def _process_email_queues(self):
        """Find auto_queued drafts across all projects and send them."""
        from app.core.email_service import build_rfq_html, send_email
        from app.schemas.agent_state import OutreachEvent

        projects = await self._list_projects()

        for project in projects:
            project_id = str(project.get("id", ""))
            outreach = self._get_outreach_state(project)
            if not outreach or not outreach.auto_config:
                continue
            if outreach.auto_config.mode not in ("auto", "semi_auto"):
                continue
            owner_email = await resolve_project_owner_email(project)
            ensure_monitor(outreach, owner_email=owner_email)

            queued = [
                d
                for d in outreach.draft_emails
                if d.status == "auto_queued" and d.supplier_index not in outreach.excluded_suppliers
            ]
            if not queued:
                continue

            logger.info(
                "Scheduler: Processing %d auto_queued emails for project %s",
                len(queued), project_id,
            )

            # Resolve recipient emails from discovery data
            discovery_data = project.get("discovery_results")
            suppliers_list = []
            if discovery_data:
                from app.schemas.agent_state import DiscoveryResults
                dr = DiscoveryResults(**discovery_data)
                suppliers_list = dr.suppliers

            for draft in queued:
                if draft.supplier_index in outreach.excluded_suppliers:
                    continue

                supplier_status = None
                for status in outreach.supplier_statuses:
                    if status.supplier_index == draft.supplier_index:
                        supplier_status = status
                        break

                recipient = draft.recipient_email
                if not recipient and draft.supplier_index < len(suppliers_list):
                    recipient = suppliers_list[draft.supplier_index].email

                if not recipient:
                    draft.status = "failed"
                    if supplier_status:
                        supplier_status.email_sent = False
                        supplier_status.delivery_status = "failed"
                        supplier_status.send_error = "No supplier email found"
                    record_outbound_email(
                        outreach,
                        supplier_index=draft.supplier_index,
                        supplier_name=draft.supplier_name,
                        to_email=None,
                        from_email=settings.from_email,
                        cc_emails=[owner_email] if owner_email else [],
                        subject=draft.subject,
                        body=draft.body,
                        resend_email_id=None,
                        delivery_status="failed",
                        source="scheduler_auto_queue",
                        event_type="send_failed",
                        details={"reason": "missing_email", "project_id": project_id},
                    )
                    logger.warning(
                        "Scheduler: No email for %s — marking failed",
                        draft.supplier_name,
                    )
                    continue

                result = await send_email(
                    to=recipient,
                    subject=draft.subject,
                    body_html=build_rfq_html(draft.body),
                    cc=[owner_email] if owner_email else [],
                    reply_to=settings.from_email,
                    headers={"X-Tamkin-Project-ID": project_id},
                )

                if result.get("sent"):
                    draft.status = "sent"
                    email_id = result.get("id", "")
                    self._stats["emails_sent"] += 1

                    # Update supplier status
                    for status in outreach.supplier_statuses:
                        if status.supplier_index == draft.supplier_index:
                            status.email_sent = True
                            status.sent_at = time.time()
                            status.email_id = email_id
                            if email_id and email_id not in status.email_ids:
                                status.email_ids.append(email_id)
                            status.delivery_status = "sent"
                            status.send_error = None
                            break
                    record_outbound_email(
                        outreach,
                        supplier_index=draft.supplier_index,
                        supplier_name=draft.supplier_name,
                        to_email=recipient,
                        from_email=result.get("from") or settings.from_email,
                        cc_emails=result.get("cc") or ([owner_email] if owner_email else []),
                        subject=draft.subject,
                        body=draft.body,
                        resend_email_id=email_id,
                        delivery_status="sent",
                        source="scheduler_auto_queue",
                        event_type="email_sent",
                        details={"project_id": project_id},
                    )

                    outreach.events.append(OutreachEvent(
                        event_type="auto_email_sent",
                        supplier_index=draft.supplier_index,
                        supplier_name=draft.supplier_name,
                        details={"email_id": email_id, "recipient": recipient},
                    ))

                    logger.info(
                        "Scheduler: Sent email to %s (%s)",
                        draft.supplier_name, recipient,
                    )
                else:
                    draft.status = "failed"
                    if supplier_status:
                        supplier_status.email_sent = False
                        supplier_status.delivery_status = "failed"
                        supplier_status.send_error = result.get("error", "unknown")
                    record_outbound_email(
                        outreach,
                        supplier_index=draft.supplier_index,
                        supplier_name=draft.supplier_name,
                        to_email=recipient,
                        from_email=settings.from_email,
                        cc_emails=[owner_email] if owner_email else [],
                        subject=draft.subject,
                        body=draft.body,
                        resend_email_id=None,
                        delivery_status="failed",
                        source="scheduler_auto_queue",
                        event_type="send_failed",
                        details={"project_id": project_id, "error": result.get("error", "unknown")},
                    )
                    outreach.events.append(OutreachEvent(
                        event_type="auto_email_failed",
                        supplier_index=draft.supplier_index,
                        supplier_name=draft.supplier_name,
                        details={"error": result.get("error", "unknown")},
                    ))

                # Rate limit: 2 seconds between sends
                await asyncio.sleep(2.0)

            await self._save_outreach_state(project, outreach)

    # ── Loop 2: Follow-up Checker ────────────────────────────────

    async def _check_and_send_follow_ups(self):
        """Check if any suppliers need follow-ups and generate/send them."""
        from app.agents.followup_agent import generate_follow_ups
        from app.core.email_service import build_rfq_html, send_email
        from app.schemas.agent_state import (
            OutreachEvent,
            ParsedRequirements,
        )

        projects = await self._list_projects()
        now = time.time()

        for project in projects:
            project_id = str(project.get("id", ""))
            outreach = self._get_outreach_state(project)
            if not outreach:
                continue
            if not outreach.auto_config and outreach.quick_approval_decision != "approved":
                continue
            if outreach.auto_config and outreach.auto_config.mode not in ("auto", "semi_auto"):
                continue
            owner_email = await resolve_project_owner_email(project)
            ensure_monitor(outreach, owner_email=owner_email)

            schedule = outreach.auto_config.follow_up_schedule if outreach.auto_config else [3, 7, 14]
            needs_follow_up = False

            for status in outreach.supplier_statuses:
                if status.excluded:
                    continue
                if not status.email_sent or status.response_received:
                    continue
                if status.follow_ups_sent >= len(schedule):
                    continue

                sent_at = status.sent_at or 0
                days_since_sent = (now - sent_at) / 86400
                next_follow_up_day = schedule[status.follow_ups_sent]

                if days_since_sent >= next_follow_up_day:
                    needs_follow_up = True
                    break

            if not needs_follow_up:
                continue

            reqs_data = project.get("parsed_requirements")
            if not reqs_data:
                continue

            logger.info("Scheduler: Generating follow-ups for project %s", project_id)

            try:
                reqs = ParsedRequirements(**reqs_data)
                result = await generate_follow_ups(outreach, reqs)

                if not result.follow_ups:
                    continue

                outreach.follow_up_emails.extend(result.follow_ups)

                # Auto-send follow-ups
                discovery_data = project.get("discovery_results")
                suppliers_list = []
                if discovery_data:
                    from app.schemas.agent_state import DiscoveryResults
                    dr = DiscoveryResults(**discovery_data)
                    suppliers_list = dr.suppliers

                for fu in result.follow_ups:
                    if fu.supplier_index in outreach.excluded_suppliers:
                        fu.status = "failed"
                        continue

                    recipient = fu.recipient_email
                    if not recipient and fu.supplier_index < len(suppliers_list):
                        recipient = suppliers_list[fu.supplier_index].email

                    if not recipient:
                        fu.status = "failed"
                        record_outbound_email(
                            outreach,
                            supplier_index=fu.supplier_index,
                            supplier_name=fu.supplier_name,
                            to_email=None,
                            from_email=settings.from_email,
                            cc_emails=[owner_email] if owner_email else [],
                            subject=fu.subject,
                            body=fu.body,
                            resend_email_id=None,
                            delivery_status="failed",
                            source="scheduler_followup",
                            event_type="followup_send_failed",
                            details={"reason": "missing_email", "project_id": project_id},
                        )
                        continue

                    send_result = await send_email(
                        to=recipient,
                        subject=fu.subject,
                        body_html=build_rfq_html(fu.body),
                        cc=[owner_email] if owner_email else [],
                        reply_to=settings.from_email,
                        headers={"X-Tamkin-Project-ID": project_id},
                    )

                    if send_result.get("sent"):
                        fu.status = "sent"
                        self._stats["follow_ups_sent"] += 1

                        for s in outreach.supplier_statuses:
                            if s.supplier_index == fu.supplier_index:
                                s.follow_ups_sent += 1
                                s.last_follow_up_at = now
                                email_id = send_result.get("id", "")
                                if email_id:
                                    s.email_id = email_id
                                    if email_id not in s.email_ids:
                                        s.email_ids.append(email_id)
                                s.delivery_status = "sent"
                                s.send_error = None
                                break
                        record_outbound_email(
                            outreach,
                            supplier_index=fu.supplier_index,
                            supplier_name=fu.supplier_name,
                            to_email=recipient,
                            from_email=send_result.get("from") or settings.from_email,
                            cc_emails=send_result.get("cc") or ([owner_email] if owner_email else []),
                            subject=fu.subject,
                            body=fu.body,
                            resend_email_id=send_result.get("id"),
                            delivery_status="sent",
                            source="scheduler_followup",
                            event_type="followup_sent",
                            details={
                                "project_id": project_id,
                                "follow_up_number": fu.follow_up_number,
                            },
                        )

                        outreach.events.append(OutreachEvent(
                            event_type="auto_followup_sent",
                            supplier_index=fu.supplier_index,
                            supplier_name=fu.supplier_name,
                            details={"follow_up_number": fu.follow_up_number},
                        ))

                        logger.info(
                            "Scheduler: Sent follow-up #%d to %s",
                            fu.follow_up_number, fu.supplier_name,
                        )
                    else:
                        fu.status = "failed"
                        for s in outreach.supplier_statuses:
                            if s.supplier_index == fu.supplier_index:
                                s.email_sent = False
                                s.delivery_status = "failed"
                                s.send_error = send_result.get("error", "unknown")
                                break
                        record_outbound_email(
                            outreach,
                            supplier_index=fu.supplier_index,
                            supplier_name=fu.supplier_name,
                            to_email=recipient,
                            from_email=settings.from_email,
                            cc_emails=[owner_email] if owner_email else [],
                            subject=fu.subject,
                            body=fu.body,
                            resend_email_id=None,
                            delivery_status="failed",
                            source="scheduler_followup",
                            event_type="followup_send_failed",
                            details={
                                "project_id": project_id,
                                "error": send_result.get("error", "unknown"),
                                "follow_up_number": fu.follow_up_number,
                            },
                        )

                    await asyncio.sleep(2.0)

                await self._save_outreach_state(project, outreach)

            except Exception as e:
                logger.error("Scheduler: Follow-up generation failed for %s: %s", project_id, e)

    # ── Loop 3: Inbox Monitor ────────────────────────────────────

    async def _check_inboxes(self):
        """Check Gmail for supplier responses and auto-parse them."""
        from app.agents.inbox_monitor import get_monitor
        from app.agents.response_parser import parse_supplier_response
        from app.schemas.agent_state import (
            DiscoveryResults,
            OutreachEvent,
            ParsedRequirements,
        )

        projects = await self._list_projects()

        for project in projects:
            project_id = str(project.get("id", ""))
            outreach = self._get_outreach_state(project)
            if not outreach:
                continue

            auto_mode = outreach.auto_config.mode if outreach.auto_config else None
            monitor_enabled = auto_mode in ("auto", "semi_auto") or outreach.quick_approval_decision == "approved"
            if not monitor_enabled:
                continue

            owner_email = await resolve_project_owner_email(project)
            ensure_monitor(outreach, owner_email=owner_email)

            # Need at least one email sent
            sent_suppliers = [
                s
                for s in outreach.supplier_statuses
                if s.email_sent and not s.excluded
            ]
            if not sent_suppliers:
                continue

            # Build supplier email/domain lists for filtering
            discovery_data = project.get("discovery_results")
            if not discovery_data:
                continue

            dr = DiscoveryResults(**discovery_data)
            supplier_emails = []
            supplier_domains = []

            supplier_indices = outreach.selected_suppliers or [s.supplier_index for s in sent_suppliers]
            for idx in supplier_indices:
                if idx in outreach.excluded_suppliers:
                    continue
                if idx < len(dr.suppliers):
                    supplier = dr.suppliers[idx]
                    if supplier.email:
                        supplier_emails.append(supplier.email)
                    if supplier.website:
                        try:
                            domain = urlparse(supplier.website).netloc.replace("www.", "")
                            if domain:
                                supplier_domains.append(domain)
                        except Exception:
                            pass

            if not supplier_emails and not supplier_domains:
                continue

            try:
                monitor = get_monitor("gmail")
                messages = await monitor.check_once(
                    config={
                        "supplier_emails": supplier_emails,
                        "supplier_domains": supplier_domains,
                        "max_results": 20,
                    },
                    project_id=project_id,
                )

                self._stats["inbox_checks"] += 1
                record_inbox_check(
                    outreach,
                    source="scheduler_inbox_monitor",
                    message_count=len(messages),
                )

                if not messages:
                    await self._save_outreach_state(project, outreach)
                    continue

                outreach.events.append(OutreachEvent(
                    event_type="auto_inbox_checked",
                    details={"messages_found": len(messages)},
                ))

                # Auto-parse each response
                reqs_data = project.get("parsed_requirements")
                if not reqs_data:
                    await self._save_outreach_state(project, outreach)
                    continue

                reqs = ParsedRequirements(**reqs_data)

                for msg in messages:
                    sender = msg.get("sender", "")
                    subject = msg.get("subject")
                    body = msg.get("body", "")
                    snippet = msg.get("snippet")
                    inbox_message_id = msg.get("message_id")
                    matched = msg.get("matched_supplier")
                    supplier_idx, supplier_name = self._match_supplier_from_token(outreach, dr, matched)

                    record_inbound_email(
                        outreach,
                        inbox_message_id=inbox_message_id,
                        sender=sender,
                        subject=subject,
                        body=body,
                        snippet=snippet,
                        matched_sender=matched,
                        supplier_index=supplier_idx,
                        supplier_name=supplier_name,
                        source="scheduler_inbox_monitor",
                    )

                    if supplier_idx is None:
                        continue

                    supplier_status = next(
                        (s for s in outreach.supplier_statuses if s.supplier_index == supplier_idx),
                        None,
                    )
                    if supplier_status and supplier_status.response_received:
                        continue

                    if not body or len(body.strip()) < 10:
                        continue

                    try:
                        quote = await parse_supplier_response(
                            supplier_name=supplier_name or dr.suppliers[supplier_idx].name,
                            supplier_index=supplier_idx,
                            response_text=body,
                            requirements=reqs,
                        )

                        outreach.parsed_quotes.append(quote)
                        self._stats["responses_parsed"] += 1

                        if supplier_status:
                            supplier_status.response_received = True
                            supplier_status.response_text = body
                            supplier_status.parsed_quote = quote
                        mark_inbound_message_parsed(
                            outreach,
                            inbox_message_id=inbox_message_id,
                            supplier_index=supplier_idx,
                            confidence_score=quote.confidence_score,
                            source="scheduler_inbox_monitor",
                        )

                        if quote.can_fulfill is False or self._response_indicates_cannot_fulfill(
                            quote.fulfillment_note or quote.notes,
                            body,
                        ):
                            self._exclude_supplier_from_project(
                                project=project,
                                outreach=outreach,
                                supplier_index=supplier_idx,
                                supplier_name=supplier_name,
                                reason=quote.fulfillment_note
                                or "Supplier indicated they cannot fulfill this request",
                            )
                            outreach.events.append(OutreachEvent(
                                event_type="supplier_excluded",
                                supplier_index=supplier_idx,
                                supplier_name=supplier_name,
                                details={
                                    "reason": quote.fulfillment_note
                                    or "Supplier indicated they cannot fulfill this request",
                                    "source": "scheduler_inbox_monitor",
                                },
                            ))

                        outreach.events.append(OutreachEvent(
                            event_type="auto_response_parsed",
                            supplier_index=supplier_idx,
                            supplier_name=supplier_name,
                            details={
                                "confidence": quote.confidence_score,
                                "source": "scheduler_inbox_monitor",
                            },
                        ))

                        logger.info(
                            "Scheduler: Auto-parsed response from %s (confidence: %.0f)",
                            supplier_name, quote.confidence_score,
                        )

                    except Exception as e:
                        logger.error("Scheduler: Failed to parse response from %s: %s", supplier_name, e)

                await self._save_outreach_state(project, outreach)

            except Exception as e:
                logger.error("Scheduler: Inbox check failed for %s: %s", project_id, e)

    # ── Loop 4: Phone Escalation ─────────────────────────────────

    async def _escalate_to_phone(self):
        """Initiate phone calls for suppliers where email has failed or gone unanswered."""
        from app.agents.phone_agent import initiate_supplier_call
        from app.schemas.agent_state import (
            DiscoveryResults,
            OutreachEvent,
            ParsedRequirements,
        )

        projects = await self._list_projects()
        now = time.time()

        for project in projects:
            project_id = str(project.get("id", ""))
            outreach = self._get_outreach_state(project)
            if not outreach or not outreach.auto_config:
                continue
            if outreach.auto_config.mode != "auto":
                continue

            discovery_data = project.get("discovery_results")
            reqs_data = project.get("parsed_requirements")
            if not discovery_data or not reqs_data:
                continue

            dr = DiscoveryResults(**discovery_data)
            reqs = ParsedRequirements(**reqs_data)

            for status in outreach.supplier_statuses:
                # Skip if already responded or already called
                if status.response_received:
                    continue
                if status.excluded:
                    continue
                if status.phone_call_id:
                    continue

                # Escalation triggers:
                # 1. Email bounced
                # 2. Day 7+ with no response and at least 1 follow-up sent
                should_call = False

                if status.delivery_status == "bounced":
                    should_call = True

                if status.email_sent and status.sent_at:
                    days_since = (now - status.sent_at) / 86400
                    if days_since >= 7 and status.follow_ups_sent >= 1:
                        should_call = True

                if not should_call:
                    continue

                # Need a phone number
                if status.supplier_index >= len(dr.suppliers):
                    continue
                supplier = dr.suppliers[status.supplier_index]
                if not supplier.phone:
                    continue

                # Check Retell API is configured
                if not settings.retell_api_key:
                    continue

                try:
                    call_status = await initiate_supplier_call(
                        supplier_name=supplier.name,
                        supplier_index=status.supplier_index,
                        phone_number=supplier.phone,
                        requirements=reqs,
                    )

                    status.phone_call_id = call_status.call_id
                    status.phone_status = "pending"

                    outreach.phone_calls.append(call_status)
                    self._stats["phone_calls_initiated"] += 1

                    outreach.events.append(OutreachEvent(
                        event_type="auto_phone_escalation",
                        supplier_index=status.supplier_index,
                        supplier_name=supplier.name,
                        details={
                            "call_id": call_status.call_id,
                            "reason": "bounced" if status.delivery_status == "bounced" else "no_response_7d",
                        },
                    ))

                    logger.info(
                        "Scheduler: Escalated to phone for %s (call_id: %s)",
                        supplier.name, call_status.call_id,
                    )

                except Exception as e:
                    logger.error("Scheduler: Phone escalation failed for %s: %s", supplier.name, e)

            await self._save_outreach_state(project, outreach)

    # ── Manual trigger ──────────────────────────────────────────

    async def process_project_now(self, project_id: str) -> dict:
        """Immediately process the auto-queue for a specific project.

        Returns a summary dict of what was sent.
        """
        from app.services.project_store import StoreUnavailableError, get_project_store

        store = get_project_store()
        try:
            project = await store.get_project(project_id)
        except StoreUnavailableError as exc:
            return {"error": f"Project store unavailable: {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to load project: {exc}"}

        if not project:
            return {"error": "Project not found"}

        outreach = self._get_outreach_state(project)
        if not outreach:
            return {"error": "No outreach state"}

        queued_before = len([d for d in outreach.draft_emails if d.status == "auto_queued"])

        # Temporarily run the email queue processor just for this project
        await self._process_email_queues()

        refreshed = await store.get_project(project_id)
        if not refreshed:
            return {"error": "Project disappeared during processing"}
        refreshed_outreach = self._get_outreach_state(refreshed)
        if not refreshed_outreach:
            return {"error": "Outreach state missing after processing"}

        queued_after = len([d for d in refreshed_outreach.draft_emails if d.status == "auto_queued"])
        failed = len([d for d in refreshed_outreach.draft_emails if d.status == "failed"])
        sent = queued_before - queued_after

        return {
            "emails_sent": sent,
            "failed_count": failed,
            "remaining_queued": queued_after,
        }
