"""Tests for brain_wrought_engine.ingestion.backlink_f1.

Unit tests:
  1. Perfect match → f1 = 1.0
  2. Submission is a strict subset of gold → p=1.0, r<1.0, f1 in (0, 1)
  3. Submission is a strict superset of gold → p<1.0, r=1.0, f1 in (0, 1)
  4. Zero overlap → f1 = 0.0
  5. Vacuous empty/empty → f1 = 1.0
  6. compute_f1_components returns matching (p, r, f1)
  7. Direction matters: (A, B) != (B, A)
  8. Slug normalisation: spaces and case differences are unified

Property tests:
  - f1 always in [0.0, 1.0]
  - f1 == 1.0 iff submission edge set equals gold edge set (after normalisation)
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from brain_wrought_engine.fixtures.gold_graph import GoldEdge, GoldGraph, GoldNode
from brain_wrought_engine.ingestion.backlink_f1 import (
    BacklinkF1Input,
    SubmissionEdge,
    _gold_pairs,
    _submission_pairs,
    compute_f1_components,
    score_backlink_f1,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_node(note_id: str) -> GoldNode:
    return GoldNode(
        note_id=note_id,
        title=note_id,
        note_type="topic",
        frontmatter={"type": "topic", "tags": "topic"},
        expected_content_facets=[],
        source_inbox_items=[],
    )


def _make_graph(*edge_pairs: tuple[str, str], seed: int = 0) -> GoldGraph:
    """Build a minimal GoldGraph from a list of (source_id, target_id) pairs."""
    node_ids: set[str] = set()
    for src, tgt in edge_pairs:
        node_ids.add(src)
        node_ids.add(tgt)

    nodes = {nid: _minimal_node(nid) for nid in node_ids}
    raw = (GoldEdge(source_id=src, target_id=tgt, edge_type="mentions") for src, tgt in edge_pairs)
    edges = tuple(sorted(raw, key=lambda e: (e.source_id, e.target_id, e.edge_type)))
    return GoldGraph(seed=seed, nodes=nodes, edges=edges)


def _sub(*edge_pairs: tuple[str, str]) -> frozenset[SubmissionEdge]:
    return frozenset(
        SubmissionEdge(source_note_id=src, target_note_id=tgt) for src, tgt in edge_pairs
    )


def _inp(graph: GoldGraph, submission: frozenset[SubmissionEdge]) -> BacklinkF1Input:
    return BacklinkF1Input(gold_graph=graph, submission_edges=submission)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_perfect_match_f1_is_one() -> None:
    """Submission exactly equals gold → f1 = 1.0."""
    graph = _make_graph(("alice", "project_helios"), ("bob", "project_helios"))
    sub = _sub(("alice", "project_helios"), ("bob", "project_helios"))
    assert score_backlink_f1(_inp(graph, sub)) == 1.0


def test_subset_submission_high_precision_low_recall() -> None:
    """Submission is a strict subset of gold: p=1.0, r<1.0, 0<f1<1."""
    graph = _make_graph(
        ("alice", "project_helios"),
        ("bob", "project_helios"),
        ("carol", "project_helios"),
    )
    sub = _sub(("alice", "project_helios"), ("bob", "project_helios"))
    p, r, f1 = compute_f1_components(_inp(graph, sub))
    assert p == 1.0
    assert math.isclose(r, 2 / 3)
    assert 0.0 < f1 < 1.0


def test_superset_submission_low_precision_high_recall() -> None:
    """Submission is a strict superset of gold: p<1.0, r=1.0, 0<f1<1."""
    graph = _make_graph(("alice", "project_helios"), ("bob", "project_helios"))
    sub = _sub(
        ("alice", "project_helios"),
        ("bob", "project_helios"),
        ("carol", "project_helios"),
    )
    p, r, f1 = compute_f1_components(_inp(graph, sub))
    assert math.isclose(p, 2 / 3)
    assert r == 1.0
    assert 0.0 < f1 < 1.0


def test_zero_overlap_f1_is_zero() -> None:
    """No edges in common → f1 = 0.0."""
    graph = _make_graph(("alice", "project_helios"))
    sub = _sub(("bob", "project_apollo"))
    assert score_backlink_f1(_inp(graph, sub)) == 0.0


def test_vacuous_empty_f1_is_one() -> None:
    """Empty gold + empty submission → f1 = 1.0."""
    graph = GoldGraph(seed=0, nodes={}, edges=())
    sub: frozenset[SubmissionEdge] = frozenset()
    assert score_backlink_f1(_inp(graph, sub)) == 1.0


def test_empty_gold_nonempty_submission_f1_zero() -> None:
    """Empty gold + non-empty submission → f1 = 0.0."""
    graph = GoldGraph(seed=0, nodes={}, edges=())
    sub = _sub(("alice", "project_helios"))
    assert score_backlink_f1(_inp(graph, sub)) == 0.0


def test_nonempty_gold_empty_submission_f1_zero() -> None:
    """Non-empty gold + empty submission → f1 = 0.0."""
    graph = _make_graph(("alice", "project_helios"))
    sub: frozenset[SubmissionEdge] = frozenset()
    assert score_backlink_f1(_inp(graph, sub)) == 0.0


def test_compute_f1_components_consistent_with_score() -> None:
    """compute_f1_components f1 component matches score_backlink_f1."""
    graph = _make_graph(("a", "b"), ("b", "c"), ("c", "d"))
    sub = _sub(("a", "b"), ("b", "c"), ("x", "y"))
    inp = _inp(graph, sub)
    p, r, f1 = compute_f1_components(inp)
    assert math.isclose(f1, score_backlink_f1(inp))
    assert math.isclose(p, 2 / 3)
    assert math.isclose(r, 2 / 3)


def test_direction_matters() -> None:
    """(A, B) and (B, A) are distinct edges; reversing submission yields f1 = 0.0."""
    graph = _make_graph(("alice", "bob"))
    sub_correct = _sub(("alice", "bob"))
    sub_reversed = _sub(("bob", "alice"))
    assert score_backlink_f1(_inp(graph, sub_correct)) == 1.0
    assert score_backlink_f1(_inp(graph, sub_reversed)) == 0.0


def test_slug_normalisation_case_insensitive() -> None:
    """Submission using 'Alice Chen' matches gold note_id 'alice_chen' after slug+lower."""
    graph = _make_graph(("alice_chen", "project_helios"))
    sub = _sub(("Alice Chen", "Project Helios"))
    assert score_backlink_f1(_inp(graph, sub)) == 1.0


def test_slug_normalisation_spaces_to_underscores() -> None:
    """Spaces in submission note IDs are converted to underscores for matching."""
    graph = _make_graph(("project_helios", "alice_chen"))
    sub = _sub(("project helios", "alice chen"))
    assert score_backlink_f1(_inp(graph, sub)) == 1.0


def test_f1_formula_exact() -> None:
    """Worked example: gold={AB, BC}, sub={AB, CD} → p=0.5, r=0.5, f1=0.5."""
    graph = _make_graph(("a", "b"), ("b", "c"))
    sub = _sub(("a", "b"), ("c", "d"))
    p, r, f1 = compute_f1_components(_inp(graph, sub))
    assert math.isclose(p, 0.5)
    assert math.isclose(r, 0.5)
    assert math.isclose(f1, 0.5)


def test_idempotent() -> None:
    """Calling scorer twice with the same input returns the same result."""
    graph = _make_graph(("a", "b"), ("b", "c"))
    sub = _sub(("a", "b"))
    inp = _inp(graph, sub)
    assert score_backlink_f1(inp) == score_backlink_f1(inp)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

_SLUG_CHARS = st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
_EDGE_PAIR = st.tuples(_SLUG_CHARS, _SLUG_CHARS)


@st.composite
def _backlink_input(draw: st.DrawFn) -> BacklinkF1Input:
    gold_pairs = draw(st.lists(_EDGE_PAIR, min_size=0, max_size=8, unique=True))
    sub_pairs = draw(st.lists(_EDGE_PAIR, min_size=0, max_size=8, unique=True))

    node_ids: set[str] = set()
    for src, tgt in gold_pairs + sub_pairs:
        node_ids.add(src)
        node_ids.add(tgt)

    nodes = {nid: _minimal_node(nid) for nid in node_ids}
    edges = tuple(
        sorted(
            (GoldEdge(source_id=s, target_id=t, edge_type="mentions") for s, t in gold_pairs),
            key=lambda e: (e.source_id, e.target_id, e.edge_type),
        )
    )
    graph = GoldGraph(seed=0, nodes=nodes, edges=edges)
    submission = frozenset(SubmissionEdge(source_note_id=s, target_note_id=t) for s, t in sub_pairs)
    return BacklinkF1Input(gold_graph=graph, submission_edges=submission)


@given(_backlink_input())
@settings(max_examples=200)
def test_f1_always_in_unit_interval(inp: BacklinkF1Input) -> None:
    """F1 is always in [0.0, 1.0]."""
    f1 = score_backlink_f1(inp)
    assert 0.0 <= f1 <= 1.0


@given(_backlink_input())
@settings(max_examples=200)
def test_f1_one_iff_sets_equal(inp: BacklinkF1Input) -> None:
    """F1 == 1.0 iff gold and submission edge sets are equal after normalisation."""
    f1 = score_backlink_f1(inp)
    sets_equal = _gold_pairs(inp) == _submission_pairs(inp)
    if sets_equal:
        assert f1 == 1.0
    else:
        assert f1 < 1.0
