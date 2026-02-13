"""Supplier memory service: retrieval, persistence, and interaction logging."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.repositories import supplier_repository as repo
from app.schemas.agent_state import DiscoveredSupplier, ParsedRequirements

logger = logging.getLogger(__name__)

GENERIC_QUERY_TERMS = {
    "manufacturer",
    "manufacturers",
    "factory",
    "factories",
    "supplier",
    "suppliers",
    "oem",
    "wholesale",
    "bulk",
    "custom",
    "production",
    "producer",
    "makers",
    "maker",
}

TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "need",
    "needs",
    "looking",
    "source",
    "find",
    "made",
    "make",
    "unit",
    "units",
    "piece",
    "pieces",
    "pcs",
    "per",
}


def _database_memory_enabled() -> bool:
    settings = get_settings()
    return (settings.project_store_backend or "database").lower() == "database"


def _tokenize_terms(text: str, allow_generic: bool = False) -> list[str]:
    terms: list[str] = []
    for token in re.split(r"[^a-zA-Z0-9]+", text.lower()):
        cleaned = token.strip()
        if len(cleaned) < 3:
            continue
        if cleaned in TOKEN_STOPWORDS:
            continue
        if not allow_generic and cleaned in GENERIC_QUERY_TERMS:
            continue
        terms.append(cleaned)
    return terms


def _terms_from_requirements(requirements: ParsedRequirements) -> list[str]:
    raw_terms = [
        requirements.product_type or "",
        requirements.material or "",
        requirements.delivery_location or "",
        requirements.sourcing_preference or "",
    ]
    raw_terms.extend(requirements.search_queries[:3])

    terms: list[str] = []
    for phrase in raw_terms:
        terms.extend(_tokenize_terms(phrase, allow_generic=False))
    return terms


def _product_anchor_terms(requirements: ParsedRequirements) -> list[str]:
    raw_terms = [
        requirements.product_type or "",
        requirements.material or "",
    ]
    raw_terms.extend(requirements.search_queries[:2])
    anchors: list[str] = []
    seen: set[str] = set()
    for phrase in raw_terms:
        for token in _tokenize_terms(phrase, allow_generic=False):
            if token in seen:
                continue
            seen.add(token)
            anchors.append(token)
    return anchors[:8]


def _matches_product_anchors(supplier_text: str, anchors: list[str]) -> bool:
    if not anchors:
        return True
    blob = supplier_text.lower()
    return any(anchor in blob for anchor in anchors)


def _memory_relevance_score(
    supplier_text: str,
    base_verification_score: float,
    interaction_count: int,
    is_verified: bool,
    terms: list[str],
    anchor_terms: list[str],
) -> float:
    score = 35.0 + max(0.0, min(base_verification_score, 100.0)) * 0.45
    if is_verified:
        score += 8.0
    score += min(15.0, interaction_count * 1.5)

    text = supplier_text.lower()
    anchor_hits = 0
    for term in anchor_terms:
        if term in text:
            anchor_hits += 1
    score += min(20.0, anchor_hits * 5.0)

    for term in terms:
        if term in text:
            score += 2.5

    return max(20.0, min(98.0, score))


async def search_supplier_memory_candidates(
    requirements: ParsedRequirements,
    limit: int = 20,
) -> list[DiscoveredSupplier]:
    """Query internal supplier memory for candidates relevant to requirements."""
    if not _database_memory_enabled():
        return []

    terms = _terms_from_requirements(requirements)
    anchor_terms = _product_anchor_terms(requirements)
    try:
        async with async_session_factory() as session:
            rows = await repo.search_supplier_memory(session, requirements, limit=limit)
    except Exception:  # noqa: BLE001
        logger.warning("Supplier memory query failed", exc_info=True)
        return []

    suppliers: list[DiscoveredSupplier] = []
    for supplier_row, interaction_count in rows:
        text = " ".join(
            [
                supplier_row.name or "",
                supplier_row.description or "",
                " ".join(supplier_row.categories or []),
                " ".join(supplier_row.certifications or []),
            ]
        )
        if not _matches_product_anchors(text, anchor_terms):
            continue
        relevance = _memory_relevance_score(
            supplier_text=text,
            base_verification_score=supplier_row.verification_score or 0.0,
            interaction_count=interaction_count,
            is_verified=bool(supplier_row.is_verified),
            terms=terms,
            anchor_terms=anchor_terms,
        )
        suppliers.append(
            DiscoveredSupplier(
                supplier_id=str(supplier_row.id),
                name=supplier_row.name,
                website=supplier_row.website,
                email=supplier_row.email,
                phone=supplier_row.phone,
                address=supplier_row.address,
                city=supplier_row.city,
                country=supplier_row.country,
                description=supplier_row.description,
                categories=supplier_row.categories or [],
                certifications=supplier_row.certifications or [],
                source="supplier_memory",
                relevance_score=relevance,
                google_rating=supplier_row.google_rating,
                google_review_count=supplier_row.google_review_count,
                raw_data={
                    "memory_source": supplier_row.source,
                    "interaction_count": interaction_count,
                    "verification_score": supplier_row.verification_score,
                    "is_verified": supplier_row.is_verified,
                },
            )
        )

    return suppliers


async def persist_discovered_suppliers(
    project_id: str,
    discovery_results: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Persist discovered suppliers into supplier memory and backfill supplier IDs."""
    if not discovery_results or not _database_memory_enabled():
        return discovery_results

    raw_suppliers = discovery_results.get("suppliers") or []
    suppliers: list[DiscoveredSupplier] = []
    for raw in raw_suppliers:
        try:
            suppliers.append(DiscoveredSupplier(**raw))
        except Exception:  # noqa: BLE001
            continue

    if not suppliers:
        return discovery_results

    try:
        async with async_session_factory() as session:
            supplier_ids = await repo.upsert_discovered_suppliers(
                session=session,
                suppliers=suppliers,
                project_id=project_id,
                source_context="pipeline_discovery",
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("Failed to persist discovered suppliers", exc_info=True)
        return discovery_results

    for supplier, supplier_id in zip(suppliers, supplier_ids):
        supplier.supplier_id = supplier_id

    discovery_results["suppliers"] = [s.model_dump(mode="json") for s in suppliers]
    return discovery_results


async def persist_verification_feedback(
    project_id: str,
    discovery_results: dict[str, Any] | None,
    verification_results: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Update supplier memory with verification outcomes and capture verified events."""
    if not discovery_results or not verification_results or not _database_memory_enabled():
        return discovery_results

    verifications = verification_results.get("verifications") or []
    if not verifications:
        return discovery_results

    suppliers: list[DiscoveredSupplier] = []
    for raw in discovery_results.get("suppliers") or []:
        try:
            suppliers.append(DiscoveredSupplier(**raw))
        except Exception:  # noqa: BLE001
            continue
    if not suppliers:
        return discovery_results

    try:
        async with async_session_factory() as session:
            await repo.apply_verification_feedback(
                session=session,
                project_id=project_id,
                discovery_suppliers=suppliers,
                verification_payload=verifications,
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("Failed to persist verification feedback to supplier memory", exc_info=True)
        return discovery_results

    discovery_results["suppliers"] = [s.model_dump(mode="json") for s in suppliers]
    return discovery_results


async def record_supplier_interaction(
    project: dict[str, Any],
    supplier_index: int,
    interaction_type: str,
    source: str,
    details: dict[str, Any] | None = None,
) -> bool:
    changed = await record_supplier_interactions(
        project=project,
        supplier_indices=[supplier_index],
        interaction_type=interaction_type,
        source=source,
        details=details,
    )
    return changed


async def record_supplier_interactions(
    project: dict[str, Any],
    supplier_indices: list[int],
    interaction_type: str,
    source: str,
    details: dict[str, Any] | None = None,
) -> bool:
    """Write supplier interaction events and backfill supplier IDs if missing.

    Returns True when the project payload was mutated (supplier IDs backfilled).
    """
    if not _database_memory_enabled():
        return False

    if not supplier_indices:
        return False

    discovery = project.get("discovery_results") or {}
    raw_suppliers = discovery.get("suppliers") or []
    if not raw_suppliers:
        return False

    project_id = str(project.get("id") or "")
    if not project_id:
        return False

    changed = False
    try:
        async with async_session_factory() as session:
            for idx in supplier_indices:
                if idx < 0 or idx >= len(raw_suppliers):
                    continue
                supplier_payload = raw_suppliers[idx]
                try:
                    supplier = DiscoveredSupplier(**supplier_payload)
                except Exception:  # noqa: BLE001
                    continue

                supplier_id = supplier.supplier_id
                if not supplier_id:
                    ids = await repo.upsert_discovered_suppliers(
                        session=session,
                        suppliers=[supplier],
                        project_id=project_id,
                        source_context="interaction_backfill",
                    )
                    supplier_id = ids[0] if ids else None
                    if supplier_id:
                        raw_suppliers[idx]["supplier_id"] = supplier_id
                        changed = True

                if not supplier_id:
                    continue

                await repo.create_supplier_interaction(
                    session=session,
                    supplier_id=supplier_id,
                    project_id=project_id,
                    interaction_type=interaction_type,
                    source=source,
                    details={"supplier_index": idx, **(details or {})},
                )

            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to record supplier interaction (%s, %s)",
            interaction_type,
            source,
            exc_info=True,
        )
        return False

    if changed:
        discovery["suppliers"] = raw_suppliers
        project["discovery_results"] = discovery
    return changed
