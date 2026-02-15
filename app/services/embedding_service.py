"""Embedding utilities for supplier semantic search.

This implementation is intentionally lightweight and deterministic so the
feature can run without external embedding providers during local/dev runs.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

EMBEDDING_DIM = 1536


def _hash_chunk(seed: str, index: int) -> float:
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).hexdigest()  # noqa: S324
    # Map hex to [-1, 1]
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return (value * 2.0) - 1.0


async def embed_text(text: str, *, dim: int = EMBEDDING_DIM) -> list[float]:
    """Return a deterministic pseudo-embedding vector for text."""
    seed = (text or "").strip().lower()
    if not seed:
        seed = "empty"
    return [_hash_chunk(seed, i) for i in range(dim)]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """Compute cosine similarity for two vectors."""
    av = list(a)
    bv = list(b)
    if not av or not bv or len(av) != len(bv):
        return 0.0
    dot = sum(x * y for x, y in zip(av, bv))
    na = sum(x * x for x in av) ** 0.5
    nb = sum(y * y for y in bv) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
