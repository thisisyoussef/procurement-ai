"""Helpers for project list/dashboard query filtering."""

from __future__ import annotations

from typing import Any


def _query_terms(query: str | None) -> list[str]:
    return [token for token in str(query or "").strip().lower().split() if token]


def project_matches_query(project: dict[str, Any], query: str | None) -> bool:
    """Return True when every query term appears in project title/description text."""
    terms = _query_terms(query)
    if not terms:
        return True

    haystack = (
        f"{str(project.get('title') or '').strip().lower()} "
        f"{str(project.get('product_description') or '').strip().lower()}"
    )
    return all(term in haystack for term in terms)
