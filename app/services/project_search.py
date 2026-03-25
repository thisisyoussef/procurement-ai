"""Shared project search helpers for list and dashboard endpoints."""

from __future__ import annotations

from typing import Any


def query_terms(query: str | None) -> list[str]:
    """Return normalized, non-empty search terms from user query text."""
    normalized = str(query or "").strip().lower()
    if not normalized:
        return []
    return [term for term in normalized.split() if term]


def project_matches_query_terms(project: dict[str, Any], terms: list[str]) -> bool:
    """Return True when all search terms appear in title/description text."""
    if not terms:
        return True

    haystack = " ".join(
        [
            str(project.get("title") or "").strip().lower(),
            str(project.get("product_description") or "").strip().lower(),
        ]
    )
    return all(term in haystack for term in terms)
