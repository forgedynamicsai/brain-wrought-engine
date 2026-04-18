"""Retrieval axis: scoring metrics and qrel generation.

Determinism class: FULLY_DETERMINISTIC (scorers) / SEEDED_STOCHASTIC (qrels).

BW-003: P@k, Recall@k, MRR, nDCG@k scorers.
BW-002: deterministic qrel generator.
"""

from brain_wrought_engine.retrieval.models import (
    QrelEntry,
    QrelSet,
    RetrievalInput,
    RetrievalInputNoK,
    ScoreOutput,
)
from brain_wrought_engine.retrieval.qrel_generator import generate_qrels
from brain_wrought_engine.retrieval.scorer import (
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

__all__ = [
    "QrelEntry",
    "QrelSet",
    "RetrievalInput",
    "RetrievalInputNoK",
    "ScoreOutput",
    "generate_qrels",
    "mrr",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
]
