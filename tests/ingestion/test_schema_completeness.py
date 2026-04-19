"""Tests for brain_wrought_engine.ingestion.schema_completeness (BW-012).

Unit tests:
  1. test_perfect_completeness           — all gold nodes present, all keys filled → 1.0
  2. test_zero_completeness              — all gold nodes present, no keys filled → 0.0
  3. test_half_keys_filled               — all gold nodes present, half keys filled → 0.5
  4. test_half_nodes_missing             — half gold nodes missing → 0.5 * per_note_completeness
  5. test_empty_gold_graph_raises        — ValueError when gold_graph has no nodes
  6. test_extra_submission_notes_ignored — extra submission notes don't affect score
  7. test_extra_submission_keys_ignored  — extra keys beyond required don't affect score
  8. test_breakdown_consistent_counts    — compute_completeness_breakdown returns consistent counts

Property tests (hypothesis):
  P1. test_score_always_in_unit_interval      — 0.0 <= score <= 1.0
  P2. test_adding_notes_cannot_decrease_score — monotonic w.r.t. submission note set
  P3. test_adding_keys_cannot_decrease_score  — monotonic w.r.t. keys in matched note
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from brain_wrought_engine.fixtures.gold_graph import (
    REQUIRED_FRONTMATTER_KEYS,
    GoldGraph,
    GoldNode,
)
from brain_wrought_engine.ingestion.schema_completeness import (
    CompletenessBreakdown,
    SchemaCompletenessInput,
    SubmissionNoteSchema,
    compute_completeness_breakdown,
    score_schema_completeness,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Use "topic" notes (required: {"type", "tags"}) for most tests — 2 required
# keys make half/full arithmetic clean and deterministic.
_TOPIC_REQUIRED = REQUIRED_FRONTMATTER_KEYS["topic"]  # frozenset({"type", "tags"})
# frozenset({"type", "date", "attendees", "project"})
_MEETING_REQUIRED = REQUIRED_FRONTMATTER_KEYS["meeting"]


def _topic_node(note_id: str) -> GoldNode:
    return GoldNode(
        note_id=note_id,
        title=note_id,
        note_type="topic",
        frontmatter={"type": "topic", "tags": "test"},
        expected_content_facets=[f"Topic {note_id}."],
        source_inbox_items=[],
    )


def _make_graph(note_ids: list[str], note_type: str = "topic") -> GoldGraph:
    """Return a graph with homogeneous note_type nodes."""
    nodes = {
        nid: _topic_node(nid) if note_type == "topic" else _meeting_node(nid) for nid in note_ids
    }
    return GoldGraph(seed=42, nodes=nodes, edges=())


def _meeting_node(note_id: str) -> GoldNode:
    return GoldNode(
        note_id=note_id,
        title=note_id,
        note_type="meeting",
        frontmatter={
            "type": "meeting",
            "date": "2026-01-01",
            "attendees": "alice",
            "project": "helios",
        },
        expected_content_facets=[f"Meeting {note_id}."],
        source_inbox_items=[],
    )


def _schema(note_id: str, keys: frozenset[str]) -> SubmissionNoteSchema:
    return SubmissionNoteSchema(note_id=note_id, frontmatter_keys=keys)


# ---------------------------------------------------------------------------
# 1. Perfect completeness
# ---------------------------------------------------------------------------


def test_perfect_completeness() -> None:
    """All gold nodes matched with full required key sets → 1.0."""
    graph = _make_graph(["note_a", "note_b", "note_c"])
    schemas = frozenset(_schema(nid, _TOPIC_REQUIRED) for nid in ["note_a", "note_b", "note_c"])
    inp = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas)
    assert score_schema_completeness(inp) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 2. Zero completeness
# ---------------------------------------------------------------------------


def test_zero_completeness() -> None:
    """All gold nodes matched but zero required keys provided → 0.0."""
    graph = _make_graph(["note_a", "note_b"])
    schemas = frozenset(_schema(nid, frozenset()) for nid in ["note_a", "note_b"])
    inp = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas)
    assert score_schema_completeness(inp) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 3. Half keys filled
# ---------------------------------------------------------------------------


def test_half_keys_filled() -> None:
    """All gold nodes matched; each note provides exactly half of required keys → 0.5.

    Uses topic notes with 2 required keys; provides 1 of 2 → 0.5 per note.
    """
    assert len(_TOPIC_REQUIRED) == 2, "test assumes topic has exactly 2 required keys"
    half_keys = frozenset(sorted(_TOPIC_REQUIRED)[:1])  # exactly 1 of 2

    graph = _make_graph(["note_a", "note_b"])
    schemas = frozenset(_schema(nid, half_keys) for nid in ["note_a", "note_b"])
    inp = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas)
    assert score_schema_completeness(inp) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 4. Half gold nodes missing
# ---------------------------------------------------------------------------


def test_half_nodes_missing() -> None:
    """Half gold nodes absent from submission; present nodes have all keys → 0.5."""
    graph = _make_graph(["note_a", "note_b"])
    # Only provide schema for note_a; note_b is missing → contributes 0.0
    schemas = frozenset([_schema("note_a", _TOPIC_REQUIRED)])
    inp = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas)
    assert score_schema_completeness(inp) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 5. Empty gold graph raises ValueError
# ---------------------------------------------------------------------------


def test_empty_gold_graph_raises() -> None:
    """A GoldGraph with no nodes raises ValueError (undefined denominator)."""
    empty_graph = GoldGraph(seed=42, nodes={}, edges=())
    inp = SchemaCompletenessInput(
        gold_graph=empty_graph,
        submission_schemas=frozenset(),
    )
    with pytest.raises(ValueError, match="no nodes"):
        score_schema_completeness(inp)


def test_empty_gold_graph_raises_breakdown() -> None:
    """compute_completeness_breakdown also raises on empty graph."""
    empty_graph = GoldGraph(seed=42, nodes={}, edges=())
    inp = SchemaCompletenessInput(gold_graph=empty_graph, submission_schemas=frozenset())
    with pytest.raises(ValueError, match="no nodes"):
        compute_completeness_breakdown(inp)


# ---------------------------------------------------------------------------
# 6. Extra submission notes don't affect score
# ---------------------------------------------------------------------------


def test_extra_submission_notes_ignored() -> None:
    """Submission notes not in gold graph are silently ignored."""
    graph = _make_graph(["note_a"])
    schemas_without_extra = frozenset([_schema("note_a", _TOPIC_REQUIRED)])
    schemas_with_extra = frozenset(
        [
            _schema("note_a", _TOPIC_REQUIRED),
            _schema("bonus_note_x", _TOPIC_REQUIRED),
            _schema("bonus_note_y", frozenset({"irrelevant"})),
        ]
    )
    inp_base = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas_without_extra)
    inp_extra = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas_with_extra)
    score_base = score_schema_completeness(inp_base)
    score_extra = score_schema_completeness(inp_extra)
    assert score_base == pytest.approx(score_extra)


# ---------------------------------------------------------------------------
# 7. Extra submission keys don't affect score
# ---------------------------------------------------------------------------


def test_extra_submission_keys_ignored() -> None:
    """Keys beyond the required set don't penalise or boost the score."""
    graph = _make_graph(["note_a"])
    keys_exact = _TOPIC_REQUIRED
    keys_with_extras = _TOPIC_REQUIRED | frozenset({"custom_field", "another_field"})

    inp_exact = SchemaCompletenessInput(
        gold_graph=graph,
        submission_schemas=frozenset([_schema("note_a", keys_exact)]),
    )
    inp_extras = SchemaCompletenessInput(
        gold_graph=graph,
        submission_schemas=frozenset([_schema("note_a", keys_with_extras)]),
    )
    score_exact = score_schema_completeness(inp_exact)
    assert score_exact == pytest.approx(score_schema_completeness(inp_extras))
    assert score_exact == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 8. compute_completeness_breakdown returns consistent counts
# ---------------------------------------------------------------------------


def test_breakdown_consistent_counts() -> None:
    """Breakdown fields are internally consistent and match scorer output."""
    graph = _make_graph(["note_a", "note_b", "note_c"])
    # note_a: all keys; note_b: no keys; note_c: missing from submission
    schemas = frozenset(
        [
            _schema("note_a", _TOPIC_REQUIRED),
            _schema("note_b", frozenset()),
        ]
    )
    inp = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas)

    bd: CompletenessBreakdown = compute_completeness_breakdown(inp)

    assert bd.total_gold_notes == 3
    assert bd.matched_notes == 2  # note_a and note_b
    assert bd.missing_notes == 1  # note_c
    assert bd.matched_notes + bd.missing_notes == bd.total_gold_notes

    # mean_per_note_completeness is over matched notes only: (1.0 + 0.0) / 2 = 0.5
    assert bd.mean_per_note_completeness == pytest.approx(0.5)

    # overall_score is over all gold nodes: (1.0 + 0.0 + 0.0) / 3
    assert bd.overall_score == pytest.approx(1.0 / 3.0)

    # Must match the main scorer
    assert bd.overall_score == pytest.approx(score_schema_completeness(inp))


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

_NOTE_IDS = ["alpha", "beta", "gamma", "delta", "epsilon"]

# All possible keys across all note types (for generating arbitrary key subsets)
_ALL_REQUIRED_KEYS: frozenset[str] = frozenset().union(*REQUIRED_FRONTMATTER_KEYS.values())
_SORTED_KEYS = sorted(_ALL_REQUIRED_KEYS)


def _make_parametric_graph(note_ids: list[str]) -> GoldGraph:
    nodes = {nid: _topic_node(nid) for nid in note_ids}
    return GoldGraph(seed=0, nodes=nodes, edges=())


@given(
    note_ids=st.lists(
        st.sampled_from(_NOTE_IDS),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    keys_per_note=st.lists(
        st.frozensets(st.sampled_from(_SORTED_KEYS)),
        min_size=0,
        max_size=5,
    ),
)
@settings(max_examples=200)
def test_score_always_in_unit_interval(
    note_ids: list[str],
    keys_per_note: list[frozenset[str]],
) -> None:
    """0.0 <= score <= 1.0 for any valid non-empty graph."""
    graph = _make_parametric_graph(note_ids)
    schemas = frozenset(
        _schema(nid, keys) for nid, keys in zip(note_ids[: len(keys_per_note)], keys_per_note)
    )
    inp = SchemaCompletenessInput(gold_graph=graph, submission_schemas=schemas)
    score = score_schema_completeness(inp)
    assert 0.0 <= score <= 1.0


@given(
    note_ids=st.lists(
        st.sampled_from(_NOTE_IDS),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    base_ids=st.frozensets(st.sampled_from(_NOTE_IDS), max_size=3),
    extra_ids=st.frozensets(st.sampled_from(_NOTE_IDS), max_size=3),
)
@settings(max_examples=200)
def test_adding_notes_cannot_decrease_score(
    note_ids: list[str],
    base_ids: frozenset[str],
    extra_ids: frozenset[str],
) -> None:
    """Adding more matching submission notes cannot decrease the score."""
    graph = _make_parametric_graph(note_ids)

    base_schemas = frozenset(_schema(nid, _TOPIC_REQUIRED) for nid in base_ids)
    augmented_schemas = frozenset(_schema(nid, _TOPIC_REQUIRED) for nid in (base_ids | extra_ids))

    inp_base = SchemaCompletenessInput(gold_graph=graph, submission_schemas=base_schemas)
    inp_aug = SchemaCompletenessInput(gold_graph=graph, submission_schemas=augmented_schemas)

    assert score_schema_completeness(inp_aug) >= score_schema_completeness(inp_base)


@given(
    base_keys=st.frozensets(st.sampled_from(_SORTED_KEYS), max_size=4),
    extra_keys=st.frozensets(st.sampled_from(_SORTED_KEYS), max_size=4),
)
@settings(max_examples=200)
def test_adding_keys_cannot_decrease_score(
    base_keys: frozenset[str],
    extra_keys: frozenset[str],
) -> None:
    """Adding keys to a matched submission note cannot decrease the score."""
    graph = _make_parametric_graph(["note_a"])

    inp_base = SchemaCompletenessInput(
        gold_graph=graph,
        submission_schemas=frozenset([_schema("note_a", base_keys)]),
    )
    inp_aug = SchemaCompletenessInput(
        gold_graph=graph,
        submission_schemas=frozenset([_schema("note_a", base_keys | extra_keys)]),
    )

    assert score_schema_completeness(inp_aug) >= score_schema_completeness(inp_base)
