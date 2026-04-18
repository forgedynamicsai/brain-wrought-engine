"""Retrieval metric scorers: P@k, Recall@k, MRR, nDCG@k.

All functions are pure, stateless, and produce bit-identical results for the
same inputs.  No external eval libraries are used.

Determinism class: FULLY_DETERMINISTIC

BW-003
"""

from __future__ import annotations

import math


def precision_at_k(
    relevant: frozenset[str],
    retrieved: tuple[str, ...],
    k: int,
) -> float:
    """P@k: fraction of top-k retrieved items that are relevant.

    Determinism class: FULLY_DETERMINISTIC

    Formula: |relevant ∩ retrieved[:k]| / k

    When k exceeds the length of *retrieved*, the missing positions are treated
    as non-relevant (so the denominator is still k, not len(retrieved)).

    Args:
        relevant:  Frozen set of relevant document IDs.
        retrieved: Ordered tuple of retrieved document IDs (rank 1 first).
        k:         Cut-off depth (must be >= 1).

    Returns:
        Precision at k in [0.0, 1.0].

    Raises:
        ValueError: If k < 1.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / k


def recall_at_k(
    relevant: frozenset[str],
    retrieved: tuple[str, ...],
    k: int,
) -> float:
    """Recall@k: fraction of relevant items found in top-k.

    Determinism class: FULLY_DETERMINISTIC

    Formula: |relevant ∩ retrieved[:k]| / |relevant|
    Returns 0.0 if relevant is empty.

    When k exceeds the length of *retrieved*, the missing positions are treated
    as non-retrieved.

    Args:
        relevant:  Frozen set of relevant document IDs.
        retrieved: Ordered tuple of retrieved document IDs (rank 1 first).
        k:         Cut-off depth (must be >= 1).

    Returns:
        Recall at k in [0.0, 1.0].

    Raises:
        ValueError: If k < 1.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    if not relevant:
        return 0.0

    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(relevant)


def mrr(
    relevant: frozenset[str],
    retrieved: tuple[str, ...],
) -> float:
    """MRR for a single query: reciprocal rank of first relevant item.

    Determinism class: FULLY_DETERMINISTIC

    Formula: 1/rank of first relevant item, or 0.0 if none found.

    Ranks are 1-indexed.  To obtain the mean over multiple queries, average
    the per-query MRR values returned by this function.

    Args:
        relevant:  Frozen set of relevant document IDs.
        retrieved: Ordered tuple of retrieved document IDs (rank 1 first).

    Returns:
        Reciprocal rank in (0.0, 1.0], or 0.0 if no relevant item is found.
    """
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    relevant: frozenset[str],
    retrieved: tuple[str, ...],
    k: int,
) -> float:
    """nDCG@k: normalized discounted cumulative gain at k (binary relevance).

    Determinism class: FULLY_DETERMINISTIC

    Formula: DCG@k / IDCG@k
    DCG@k  = Σ_{i=1}^{k} rel_i / log2(i+1)
    IDCG@k = DCG@k of ideal ranking (all relevant items first)
    Returns 1.0 if relevant is empty (vacuously perfect).

    Binary relevance: rel_i = 1 if retrieved[i-1] ∈ relevant, else 0.

    Reference: Järvelin & Kekäläinen 2002.

    Args:
        relevant:  Frozen set of relevant document IDs.
        retrieved: Ordered tuple of retrieved document IDs (rank 1 first).
        k:         Cut-off depth (must be >= 1).

    Returns:
        nDCG at k in [0.0, 1.0].

    Raises:
        ValueError: If k < 1.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    if not relevant:
        return 1.0

    # DCG@k over the actual ranking
    dcg: float = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(i + 1)

    # IDCG@k: ideal DCG — place min(|relevant|, k) relevant docs at top positions
    ideal_hits = min(len(relevant), k)
    idcg: float = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))

    # clamp: floating-point DCG/IDCG can exceed 1.0 by a ULP for perfect rankings
    return min(dcg / idcg, 1.0)
