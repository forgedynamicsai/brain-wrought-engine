"""Tests for BW-002b model additions: query_type and expected_abstain constraints."""

from __future__ import annotations

import pytest

from brain_wrought_engine.retrieval.models import QrelEntry


def _make_entry(**kwargs: object) -> QrelEntry:
    """Convenience wrapper with default fields filled in."""
    defaults: dict[str, object] = {
        "query_id": "q0000",
        "query_text": "What does Alice think about the project?",
        "relevant_note_ids": frozenset({"alice"}),
        "query_type": "factual",
        "expected_abstain": False,
    }
    defaults.update(kwargs)
    return QrelEntry(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Abstention invariants
# ---------------------------------------------------------------------------


def test_abstention_requires_empty_relevant() -> None:
    """QrelEntry with query_type=abstention must have relevant_note_ids=frozenset()."""
    with pytest.raises(ValueError, match="relevant_note_ids"):
        _make_entry(
            query_type="abstention",
            relevant_note_ids=frozenset({"some_note"}),
            expected_abstain=True,
        )


def test_abstention_requires_expected_abstain() -> None:
    """QrelEntry with query_type=abstention must have expected_abstain=True."""
    with pytest.raises(ValueError, match="expected_abstain"):
        _make_entry(
            query_type="abstention",
            relevant_note_ids=frozenset(),
            expected_abstain=False,
        )


def test_non_abstention_forbids_expected_abstain() -> None:
    """QrelEntry with query_type=factual must have expected_abstain=False."""
    with pytest.raises(ValueError, match="expected_abstain"):
        _make_entry(
            query_type="factual",
            relevant_note_ids=frozenset({"alice"}),
            expected_abstain=True,
        )


def test_valid_abstention_entry() -> None:
    """A well-formed abstention entry constructs without error."""
    entry = _make_entry(
        query_type="abstention",
        relevant_note_ids=frozenset(),
        expected_abstain=True,
        query_text="What is Alice's relationship with Project Aurora?",
    )
    assert entry.expected_abstain is True
    assert entry.relevant_note_ids == frozenset()


def test_valid_factual_entry() -> None:
    """A well-formed factual entry constructs without error."""
    entry = _make_entry(
        query_type="factual",
        relevant_note_ids=frozenset({"note_a"}),
        expected_abstain=False,
    )
    assert entry.query_type == "factual"
    assert entry.expected_abstain is False


def test_valid_temporal_entry() -> None:
    """A well-formed temporal entry constructs without error."""
    entry = _make_entry(
        query_type="temporal",
        relevant_note_ids=frozenset({"note_a"}),
        expected_abstain=False,
        query_text="Who did I meet in January?",
    )
    assert entry.query_type == "temporal"


def test_valid_personalization_entry() -> None:
    """A well-formed personalization entry constructs without error."""
    entry = _make_entry(
        query_type="personalization",
        relevant_note_ids=frozenset({"note_b"}),
        expected_abstain=False,
        query_text="Show me my notes about the project",
    )
    assert entry.query_type == "personalization"


def test_qrel_version_default_v1() -> None:
    """QrelSet default qrel_version should now be 'v1'."""
    from brain_wrought_engine.retrieval.models import QrelSet

    entry = _make_entry()
    qset = QrelSet(seed=42, entries=(entry,))
    assert qset.qrel_version == "v1"
