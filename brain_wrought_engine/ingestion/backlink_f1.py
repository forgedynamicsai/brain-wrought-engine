"""Backlink F1 scorer for the ingestion axis.

Measures how accurately a submission reproduces the directed edge topology of
the gold graph.  Edge *type* is ignored in v1 — only (source, target) pairs
are compared after slug normalisation.

Scoring formula:
    precision = |gold ∩ submission| / |submission|
    recall    = |gold ∩ submission| / |gold|
    f1        = 2 * precision * recall / (precision + recall)

Worked example:
    gold edges (slugged):       {(alice, project_helios), (bob, project_helios)}
    submission edges (slugged): {(alice, project_helios), (carol, project_helios)}

    intersection = {(alice, project_helios)}  → size 1
    precision = 1/2 = 0.5
    recall    = 1/2 = 0.5
    f1        = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5

Edge cases:
    - gold == {} and submission == {}  → f1 = 1.0 (vacuous perfect match)
    - gold == {} and submission != {}  → f1 = 0.0
    - gold != {} and submission == {}  → f1 = 0.0
    - precision == 0 and recall == 0   → f1 = 0.0

Match rule: submission edge (A, B) matches gold edge (C, D) iff
    slug(A).lower() == slug(C).lower() and slug(B).lower() == slug(D).lower()

Direction matters: (A, B) and (B, A) are distinct edges.

Determinism class: FULLY_DETERMINISTIC — pure function of inputs, no LLM calls.
"""

from __future__ import annotations

from pydantic import BaseModel

from brain_wrought_engine.fixtures.gold_graph import GoldGraph
from brain_wrought_engine.text_utils import slug


class SubmissionEdge(BaseModel):
    source_note_id: str
    target_note_id: str

    model_config = {"frozen": True}


class BacklinkF1Input(BaseModel):
    gold_graph: GoldGraph
    submission_edges: frozenset[SubmissionEdge]

    model_config = {"frozen": True}


def _normalise(note_id: str) -> str:
    return slug(note_id).lower()


def _gold_pairs(input: BacklinkF1Input) -> frozenset[tuple[str, str]]:
    return frozenset(
        (_normalise(e.source_id), _normalise(e.target_id)) for e in input.gold_graph.edges
    )


def _submission_pairs(input: BacklinkF1Input) -> frozenset[tuple[str, str]]:
    return frozenset(
        (_normalise(e.source_note_id), _normalise(e.target_note_id)) for e in input.submission_edges
    )


def compute_f1_components(input: BacklinkF1Input) -> tuple[float, float, float]:
    """Return (precision, recall, f1) for the given input.

    All three values are in [0.0, 1.0].
    """
    gold = _gold_pairs(input)
    submission = _submission_pairs(input)

    if not gold and not submission:
        return 1.0, 1.0, 1.0

    if not gold or not submission:
        return 0.0, 0.0, 0.0

    intersection_size = len(gold & submission)
    precision = intersection_size / len(submission)
    recall = intersection_size / len(gold)

    if precision == 0.0 and recall == 0.0:
        f1 = 0.0
    else:
        f1 = 2.0 * precision * recall / (precision + recall)

    return precision, recall, f1


def score_backlink_f1(input: BacklinkF1Input) -> float:
    """Return [0.0, 1.0] F1 over directed edges.

    See module docstring for the full formula and edge-case handling.
    """
    _, _, f1 = compute_f1_components(input)
    return f1
