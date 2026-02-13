"""Repository helpers for supplier memory and supplier interaction history."""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier, SupplierInteraction
from app.schemas.agent_state import DiscoveredSupplier, ParsedRequirements


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        host = urlparse(candidate).netloc.lower().strip()
    except Exception:  # noqa: BLE001
        return None
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _merge_list(existing: list[str] | None, incoming: list[str] | None) -> list[str] | None:
    merged: list[str] = []
    seen: set[str] = set()
    for values in (existing or [], incoming or []):
        cleaned = str(values).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(cleaned)
    return merged or None


def _build_terms(requirements: ParsedRequirements) -> list[str]:
    candidates: list[str] = [
        requirements.product_type or "",
        requirements.material or "",
        requirements.delivery_location or "",
        requirements.sourcing_preference or "",
    ]
    candidates.extend(requirements.search_queries[:3])

    terms: list[str] = []
    for phrase in candidates:
        for token in re.split(r"[^a-zA-Z0-9]+", phrase.lower()):
            token = token.strip()
            if len(token) >= 3:
                terms.append(token)

    unique_terms: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        unique_terms.append(term)

    return unique_terms[:12]


async def _find_existing_supplier(
    session: AsyncSession,
    supplier: DiscoveredSupplier,
) -> Supplier | None:
    supplier_id = _normalize_uuid(supplier.supplier_id)
    if supplier_id:
        row = await session.get(Supplier, supplier_id)
        if row:
            return row

    email = _normalize_email(supplier.email)
    if email:
        row = (
            await session.execute(
                select(Supplier).where(func.lower(Supplier.email) == email).limit(1)
            )
        ).scalars().first()
        if row:
            return row

    domain = _normalize_domain(supplier.website)
    candidates: dict[uuid.UUID, Supplier] = {}
    if domain:
        domain_rows = (
            await session.execute(
                select(Supplier).where(func.lower(Supplier.website).like(f"%{domain}%")).limit(10)
            )
        ).scalars().all()
        for row in domain_rows:
            candidates[row.id] = row

    name = (supplier.name or "").strip().lower()
    if name:
        name_rows = (
            await session.execute(
                select(Supplier).where(func.lower(Supplier.name) == name).limit(10)
            )
        ).scalars().all()
        for row in name_rows:
            candidates[row.id] = row

    if not candidates:
        return None

    target_country = (supplier.country or "").strip().lower()
    best: Supplier | None = None
    best_score = -1
    for row in candidates.values():
        score = 0
        if email and row.email and row.email.strip().lower() == email:
            score += 5
        row_domain = _normalize_domain(row.website)
        if domain and row_domain and row_domain == domain:
            score += 4
        if name and row.name and row.name.strip().lower() == name:
            score += 3
        row_country = (row.country or "").strip().lower()
        if target_country and row_country and target_country == row_country:
            score += 1
        if score > best_score:
            best_score = score
            best = row

    return best if best_score > 0 else None


def _merge_supplier_row(row: Supplier, supplier: DiscoveredSupplier) -> None:
    if supplier.website and (not row.website or len(supplier.website) > len(row.website)):
        row.website = supplier.website
    if supplier.email and (not row.email or len(supplier.email) > len(row.email)):
        row.email = supplier.email
    if supplier.phone and (not row.phone or len(supplier.phone) > len(row.phone)):
        row.phone = supplier.phone
    if supplier.address and (not row.address or len(supplier.address) > len(row.address)):
        row.address = supplier.address
    if supplier.city and (not row.city or len(supplier.city) > len(row.city)):
        row.city = supplier.city
    if supplier.country and (not row.country or len(supplier.country) > len(row.country)):
        row.country = supplier.country
    if supplier.description and (not row.description or len(supplier.description) > len(row.description)):
        row.description = supplier.description

    row.categories = _merge_list(row.categories, supplier.categories)
    row.certifications = _merge_list(row.certifications, supplier.certifications)

    if supplier.google_rating is not None:
        row.google_rating = max(row.google_rating or 0.0, supplier.google_rating)
    if supplier.google_review_count is not None:
        row.google_review_count = max(row.google_review_count or 0, supplier.google_review_count)
    if supplier.source and row.source in ("manual", "unknown"):
        row.source = supplier.source


async def upsert_discovered_suppliers(
    session: AsyncSession,
    suppliers: Iterable[DiscoveredSupplier],
    project_id: str | None = None,
    source_context: str = "pipeline_discovery",
) -> list[str | None]:
    ids: list[str | None] = []
    project_uuid = _normalize_uuid(project_id)

    for supplier in suppliers:
        if not supplier.name.strip():
            ids.append(None)
            continue

        row = await _find_existing_supplier(session, supplier)
        if row is None:
            row = Supplier(
                name=supplier.name.strip(),
                website=supplier.website,
                email=_normalize_email(supplier.email),
                phone=supplier.phone,
                address=supplier.address,
                city=supplier.city,
                country=supplier.country,
                description=supplier.description,
                categories=supplier.categories or None,
                certifications=supplier.certifications or None,
                source=supplier.source or "discovery",
                google_rating=supplier.google_rating,
                google_review_count=supplier.google_review_count,
            )
            session.add(row)
        else:
            _merge_supplier_row(row, supplier)

        await session.flush()
        supplier_id = str(row.id)
        ids.append(supplier_id)

        session.add(
            SupplierInteraction(
                supplier_id=row.id,
                project_id=project_uuid,
                interaction_type="discovered",
                source=source_context,
                details={
                    "relevance_score": supplier.relevance_score,
                    "discovery_source": supplier.source,
                    "language_discovered": supplier.language_discovered,
                },
            )
        )

    await session.flush()
    return ids


async def create_supplier_interaction(
    session: AsyncSession,
    supplier_id: str | uuid.UUID,
    interaction_type: str,
    source: str,
    project_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> str:
    normalized_supplier_id = _normalize_uuid(supplier_id)
    if normalized_supplier_id is None:
        raise ValueError("supplier_id is required for interaction logging")

    row = SupplierInteraction(
        supplier_id=normalized_supplier_id,
        project_id=_normalize_uuid(project_id),
        interaction_type=interaction_type,
        source=source,
        details=details or {},
    )
    session.add(row)
    await session.flush()
    return str(row.id)


async def search_supplier_memory(
    session: AsyncSession,
    requirements: ParsedRequirements,
    limit: int = 20,
) -> list[tuple[Supplier, int]]:
    interaction_counts = (
        select(
            SupplierInteraction.supplier_id.label("supplier_id"),
            func.count(SupplierInteraction.id).label("interaction_count"),
        )
        .group_by(SupplierInteraction.supplier_id)
        .subquery()
    )

    interaction_count_col = func.coalesce(interaction_counts.c.interaction_count, 0)
    stmt = (
        select(Supplier, interaction_count_col.label("interaction_count"))
        .outerjoin(interaction_counts, interaction_counts.c.supplier_id == Supplier.id)
    )

    terms = _build_terms(requirements)
    if terms:
        clauses = []
        for term in terms:
            like = f"%{term}%"
            clauses.extend(
                [
                    func.lower(Supplier.name).like(like),
                    func.lower(func.coalesce(Supplier.description, "")).like(like),
                    func.lower(func.coalesce(Supplier.city, "")).like(like),
                    func.lower(func.coalesce(Supplier.country, "")).like(like),
                    func.lower(cast(Supplier.categories, String)).like(like),
                    func.lower(cast(Supplier.certifications, String)).like(like),
                ]
            )
        stmt = stmt.where(or_(*clauses))

    stmt = stmt.order_by(
        interaction_count_col.desc(),
        Supplier.verification_score.desc(),
        Supplier.updated_at.desc(),
    ).limit(limit)

    rows = (await session.execute(stmt)).all()
    return [(row[0], int(row[1] or 0)) for row in rows]


async def apply_verification_feedback(
    session: AsyncSession,
    project_id: str | None,
    discovery_suppliers: list[DiscoveredSupplier],
    verification_payload: list[dict[str, Any]],
) -> None:
    project_uuid = _normalize_uuid(project_id)

    for verification in verification_payload:
        supplier_index = verification.get("supplier_index")
        if not isinstance(supplier_index, int):
            continue
        if supplier_index < 0 or supplier_index >= len(discovery_suppliers):
            continue

        discovered = discovery_suppliers[supplier_index]
        row = await _find_existing_supplier(session, discovered)
        if row is None:
            inserted = await upsert_discovered_suppliers(
                session,
                [discovered],
                project_id=project_id,
                source_context="verification_backfill",
            )
            if inserted and inserted[0]:
                discovered.supplier_id = inserted[0]
                row = await session.get(Supplier, _normalize_uuid(inserted[0]))
        if row is None:
            continue

        discovered.supplier_id = str(row.id)
        composite_score = float(verification.get("composite_score", 0) or 0)
        row.verification_score = max(row.verification_score or 0, composite_score)
        recommendation = str(verification.get("recommendation", "")).lower()
        row.is_verified = recommendation in {"proceed", "caution"} and composite_score >= 50
        row.verification_data = {
            "risk_level": verification.get("risk_level"),
            "summary": verification.get("summary"),
            "recommendation": verification.get("recommendation"),
            "checks": verification.get("checks", []),
        }

        session.add(
            SupplierInteraction(
                supplier_id=row.id,
                project_id=project_uuid,
                interaction_type="verified",
                source="pipeline_verify",
                details={
                    "supplier_index": supplier_index,
                    "composite_score": composite_score,
                    "recommendation": verification.get("recommendation"),
                },
            )
        )

    await session.flush()
