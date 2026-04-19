"""Tests for brain_wrought_engine.ingestion.entity_recall (BW-009).

Unit tests:
  1. test_perfect_recall            — all gold entities matched → 1.0
  2. test_zero_recall               — no matching notes → 0.0
  3. test_half_recall               — half of gold entities matched → 0.5
  4. test_case_insensitive_slug_match — slug normalisation is applied on both sides
  5. test_extra_submission_notes_ignored — recall only; extras don't inflate score
  6. test_empty_gold_graph_raises   — ValueError when gold_graph has no nodes
  7. test_empty_submission_returns_zero — empty submission_note_ids → 0.0

Property tests (hypothesis):
  P1. test_score_always_in_unit_interval  — 0.0 <= score <= 1.0
  P2. test_adding_notes_cannot_decrease_score — monotonic w.r.t. submission set
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from brain_wrought_engine.fixtures.gold_graph import (
    CrossReference,
    GoldGraph,
    GoldNode,
    PersonEntity,
    ProjectEntity,
    generate_gold_graph,
)
from brain_wrought_engine.ingestion.entity_recall import EntityRecallInput, score_entity_recall
from brain_wrought_engine.text_utils import slug

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_graph(seed: int = 42) -> GoldGraph:
    """Return a small but non-trivial gold graph for testing."""
    people = [
        PersonEntity(name="Alice Chen", role="engineer", email="alice.chen@example.com"),
        PersonEntity(name="Bob Park", role="manager", email="bob.park@example.com"),
    ]
    projects = [
        ProjectEntity(name="Project Helios", status="active", owner="Alice Chen"),
    ]
    cross_references = [
        CrossReference(
            source_item_id="email_0001",
            mentioned_people=["Alice Chen", "Bob Park"],
            mentioned_projects=["Project Helios"],
            event_date=None,
            attendees=None,
        ),
        CrossReference(
            source_item_id="calendar_0001",
            mentioned_people=["Alice Chen", "Bob Park"],
            mentioned_projects=["Project Helios"],
            event_date="2026-01-15",
            attendees=["Alice Chen", "Bob Park"],
        ),
    ]
    return generate_gold_graph(
        seed=seed,
        people=people,
        projects=projects,
        cross_references=cross_references,
    )


def _all_gold_slugs(graph: GoldGraph) -> frozenset[str]:
    return frozenset(slug(node.title) for node in graph.nodes.values())


# ---------------------------------------------------------------------------
# 1. Perfect recall
# ---------------------------------------------------------------------------


def test_perfect_recall() -> None:
    """All gold entity slugs present in submission → 1.0."""
    graph = _make_graph()
    all_slugs = _all_gold_slugs(graph)
    inp = EntityRecallInput(gold_graph=graph, submission_note_ids=all_slugs)
    assert score_entity_recall(inp) == 1.0


# ---------------------------------------------------------------------------
# 2. Zero recall
# ---------------------------------------------------------------------------


def test_zero_recall() -> None:
    """No matching notes → 0.0."""
    graph = _make_graph()
    inp = EntityRecallInput(
        gold_graph=graph,
        submission_note_ids=frozenset({"totally_unrelated_note", "another_note"}),
    )
    assert score_entity_recall(inp) == 0.0


# ---------------------------------------------------------------------------
# 3. Half recall
# ---------------------------------------------------------------------------


def test_half_recall() -> None:
    """Exactly half of gold entity slugs present → 0.5."""
    graph = _make_graph()
    all_slugs = sorted(_all_gold_slugs(graph))
    assert len(all_slugs) >= 2, "Need at least 2 gold nodes for this test"

    half_count = len(all_slugs) // 2
    submission = frozenset(all_slugs[:half_count])
    inp = EntityRecallInput(gold_graph=graph, submission_note_ids=submission)
    score = score_entity_recall(inp)
    assert score == pytest.approx(half_count / len(all_slugs))


# ---------------------------------------------------------------------------
# 4. Case-insensitive slug match
# ---------------------------------------------------------------------------


def test_slug_match_normalisation() -> None:
    """slug() is applied to gold entity titles; submission_note_ids must match that form.

    "Alice Chen" → slug → "Alice_Chen"; a submission note_id of "Alice_Chen" matches.
    """
    graph = _make_graph()
    alice_slug = slug("Alice Chen")
    assert alice_slug in _all_gold_slugs(graph), "Expected Alice_Chen to be a gold entity slug"
    inp = EntityRecallInput(
        gold_graph=graph,
        submission_note_ids=frozenset({alice_slug}),
    )
    score = score_entity_recall(inp)
    assert score > 0.0


# ---------------------------------------------------------------------------
# 5. Extra submission notes do not inflate score
# ---------------------------------------------------------------------------


def test_extra_submission_notes_ignored() -> None:
    """Recall only: extra notes in submission beyond gold are silently ignored."""
    graph = _make_graph()
    all_slugs = _all_gold_slugs(graph)
    extra = frozenset({"bonus_note_1", "bonus_note_2", "bonus_note_3"})
    inp_without = EntityRecallInput(gold_graph=graph, submission_note_ids=all_slugs)
    inp_with = EntityRecallInput(gold_graph=graph, submission_note_ids=all_slugs | extra)
    assert score_entity_recall(inp_with) == score_entity_recall(inp_without) == 1.0


# ---------------------------------------------------------------------------
# 6. Empty gold_graph raises ValueError
# ---------------------------------------------------------------------------


def test_empty_gold_graph_raises() -> None:
    """A GoldGraph with no nodes raises ValueError (undefined denominator)."""
    empty_graph = GoldGraph(seed=42, nodes={}, edges=())
    inp = EntityRecallInput(
        gold_graph=empty_graph,
        submission_note_ids=frozenset({"some_note"}),
    )
    with pytest.raises(ValueError, match="no nodes"):
        score_entity_recall(inp)


# ---------------------------------------------------------------------------
# 7. Empty submission_note_ids → 0.0
# ---------------------------------------------------------------------------


def test_empty_submission_returns_zero() -> None:
    """Empty submission set → 0.0 (nothing was ingested)."""
    graph = _make_graph()
    inp = EntityRecallInput(gold_graph=graph, submission_note_ids=frozenset())
    assert score_entity_recall(inp) == 0.0


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


def _make_minimal_node(note_id: str, title: str) -> GoldNode:
    return GoldNode(
        note_id=note_id,
        title=title,
        note_type="person",
        frontmatter={
            "type": "person",
            "created": "2026-01-01",
            "updated": "2026-01-01",
            "tags": "person",
            "role": "engineer",
        },
        expected_content_facets=[f"{title} is a person."],
        source_inbox_items=[],
    )


_NODE_TITLES = ["Alpha One", "Beta/Two", "Gamma Three", "Delta Four", "Epsilon Five"]
_VALID_SLUGS = frozenset(slug(t) for t in _NODE_TITLES)


def _make_parametric_graph(titles: list[str]) -> GoldGraph:
    nodes = {slug(t): _make_minimal_node(slug(t), t) for t in titles}
    return GoldGraph(seed=0, nodes=nodes, edges=())


@given(
    titles=st.lists(
        st.sampled_from(_NODE_TITLES),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    submission=st.frozensets(st.sampled_from(sorted(_VALID_SLUGS)), max_size=8),
)
@settings(max_examples=200)
def test_score_always_in_unit_interval(titles: list[str], submission: frozenset[str]) -> None:
    """0.0 <= score <= 1.0 for any valid non-empty graph."""
    graph = _make_parametric_graph(titles)
    inp = EntityRecallInput(gold_graph=graph, submission_note_ids=submission)
    score = score_entity_recall(inp)
    assert 0.0 <= score <= 1.0


@given(
    titles=st.lists(
        st.sampled_from(_NODE_TITLES),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    base_submission=st.frozensets(st.sampled_from(sorted(_VALID_SLUGS)), max_size=4),
    extra=st.frozensets(st.sampled_from(sorted(_VALID_SLUGS)), max_size=4),
)
@settings(max_examples=200)
def test_adding_notes_cannot_decrease_score(
    titles: list[str],
    base_submission: frozenset[str],
    extra: frozenset[str],
) -> None:
    """Adding more note stems to submission cannot reduce recall score."""
    graph = _make_parametric_graph(titles)
    inp_base = EntityRecallInput(gold_graph=graph, submission_note_ids=base_submission)
    inp_augmented = EntityRecallInput(gold_graph=graph, submission_note_ids=base_submission | extra)
    assert score_entity_recall(inp_augmented) >= score_entity_recall(inp_base)
