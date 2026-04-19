"""Schema completeness scorer for the ingestion axis (BW-012).

Measures what fraction of required frontmatter keys each submission note has
populated, averaged across all gold nodes.

Scoring formula:

    per_note_completeness = |submission_keys ∩ required_keys| / |required_keys|

    completeness = mean(per_note_completeness across all gold nodes)

where ``required_keys`` comes from ``REQUIRED_FRONTMATTER_KEYS[node.note_type]``
and a gold node with no matching submission note contributes 0.0.

Score range: [0.0, 1.0].
Determinism class: FULLY_DETERMINISTIC — pure function of inputs.
"""

from __future__ import annotations

from pydantic import BaseModel

from brain_wrought_engine.fixtures.gold_graph import REQUIRED_FRONTMATTER_KEYS, GoldGraph
from brain_wrought_engine.text_utils import slug


class SubmissionNoteSchema(BaseModel):
    note_id: str  # stem of the note
    frontmatter_keys: frozenset[str]  # keys present in the note's YAML

    model_config = {"frozen": True}


class SchemaCompletenessInput(BaseModel):
    gold_graph: GoldGraph
    submission_schemas: frozenset[SubmissionNoteSchema]

    model_config = {"frozen": True}


class CompletenessBreakdown(BaseModel):
    total_gold_notes: int
    matched_notes: int  # gold nodes with a submission match
    missing_notes: int  # gold nodes with no submission match
    mean_per_note_completeness: float  # across matched notes only
    overall_score: float  # across all gold nodes

    model_config = {"frozen": True}


def _build_submission_lookup(schemas: frozenset[SubmissionNoteSchema]) -> dict[str, frozenset[str]]:
    return {slug(s.note_id): s.frontmatter_keys for s in schemas}


def score_schema_completeness(
    input: SchemaCompletenessInput,  # noqa: A002
) -> float:
    """Return [0.0, 1.0] mean per-note completeness across all gold nodes.

    Missing notes contribute 0.0.

    Raises
    ------
    ValueError
        If ``gold_graph`` contains no nodes (denominator is undefined).
    """
    if not input.gold_graph.nodes:
        raise ValueError("gold_graph has no nodes — completeness denominator is undefined")

    lookup = _build_submission_lookup(input.submission_schemas)

    total = 0.0
    for node in input.gold_graph.nodes.values():
        required_keys = REQUIRED_FRONTMATTER_KEYS[node.note_type]
        sub_keys = lookup.get(slug(node.note_id), frozenset())
        total += len(sub_keys & required_keys) / len(required_keys)

    return total / len(input.gold_graph.nodes)


def compute_completeness_breakdown(
    input: SchemaCompletenessInput,  # noqa: A002
) -> CompletenessBreakdown:
    """Return detailed metrics for inspection.

    Raises
    ------
    ValueError
        If ``gold_graph`` contains no nodes.
    """
    if not input.gold_graph.nodes:
        raise ValueError("gold_graph has no nodes — completeness denominator is undefined")

    lookup = _build_submission_lookup(input.submission_schemas)

    matched_count = 0
    matched_total = 0.0
    overall_total = 0.0

    for node in input.gold_graph.nodes.values():
        required_keys = REQUIRED_FRONTMATTER_KEYS[node.note_type]
        gold_slug = slug(node.note_id)
        sub_keys = lookup.get(gold_slug, frozenset())
        per_note = len(sub_keys & required_keys) / len(required_keys)
        overall_total += per_note
        if gold_slug in lookup:
            matched_count += 1
            matched_total += per_note

    total_gold = len(input.gold_graph.nodes)
    missing_count = total_gold - matched_count
    mean_matched = matched_total / matched_count if matched_count > 0 else 0.0

    return CompletenessBreakdown(
        total_gold_notes=total_gold,
        matched_notes=matched_count,
        missing_notes=missing_count,
        mean_per_note_completeness=mean_matched,
        overall_score=overall_total / total_gold,
    )
