"""Ingestion axis scoring: entity recall, backlink F1, citation accuracy, schema completeness.

BW-009 through BW-013: implementation target for Phase 2.
"""

from brain_wrought_engine.ingestion.citation_accuracy import (
    CitationAccuracyInput,
    CitationCounters,
    SubmissionCitation,
    compute_citation_counters,
    score_citation_accuracy,
)
from brain_wrought_engine.ingestion.entity_recall import EntityRecallInput, score_entity_recall
from brain_wrought_engine.ingestion.setup_friction import SetupBlock, score_setup_friction

__all__ = [
    "CitationAccuracyInput",
    "CitationCounters",
    "EntityRecallInput",
    "SetupBlock",
    "SubmissionCitation",
    "compute_citation_counters",
    "score_citation_accuracy",
    "score_entity_recall",
    "score_setup_friction",
]
