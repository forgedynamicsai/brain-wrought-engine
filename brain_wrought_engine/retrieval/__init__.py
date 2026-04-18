"""Retrieval axis scoring: P@k, Recall@k, MRR, nDCG@k.

Determinism class: FULLY_DETERMINISTIC — all functions produce bit-identical output
for the same input (IEEE 754 float caveats apply beyond 4 decimal places).

BW-003: implementation target for Phase 1.
"""

from brain_wrought_engine.retrieval.scorer import (
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

__all__ = ["mrr", "ndcg_at_k", "precision_at_k", "recall_at_k"]
