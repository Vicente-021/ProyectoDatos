"""Word-shingle construction for preprocessed documents."""

from __future__ import annotations


def word_shingles(tokens: list[str], k: int = 5) -> set[tuple[str, ...]]:
    """Return the set of distinct contiguous k-token shingles."""
    if k < 1:
        raise ValueError("k debe ser al menos 1")
    if len(tokens) < k:
        return set()
    return {tuple(tokens[start : start + k]) for start in range(len(tokens) - k + 1)}
