"""Tests for BW-002b typed query generation and LLM verification.

Six tests:
  1. test_distribution_enforcement  — 100 qrels → 30/20/20/30 distribution
  2. test_query_text_not_title      — query_text must not equal any note title
  3. test_abstention_invariant      — abstention entries have empty relevant_note_ids
  4. test_verifier_mock_agreement   — matching LLM response → (True, entry)
  5. test_verifier_mock_disagreement — non-matching LLM response → 3 retries → (False, None)
  6. test_determinism_preserved     — same seed → identical QrelSet
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from brain_wrought_engine.retrieval.models import QrelEntry
from brain_wrought_engine.retrieval.qrel_generator import _compute_distribution, generate_qrels
from brain_wrought_engine.retrieval.verifier import verify_qrel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_notes(brain_dir: Path, notes: dict[str, str]) -> None:
    """Write {stem: content} into brain_dir."""
    brain_dir.mkdir(parents=True, exist_ok=True)
    for stem, content in notes.items():
        (brain_dir / f"{stem}.md").write_text(content, encoding="utf-8")


def _note_with_entities(name: str, entities: list[str]) -> str:
    """Return note content with YAML frontmatter including an entities: list."""
    if entities:
        ent_lines = "\n".join(f"  - {e}" for e in entities)
        ent_block = f"\n{ent_lines}"
    else:
        ent_block = " []"
    return (
        f"---\ntype: person\ncreated: 2024-01-01T00:00:00Z\n"
        f"updated: 2024-01-01T00:00:00Z\ntags:\n  - person\n"
        f"entities:{ent_block}\nstate: active\n---\n"
        f"# {name}\n\nBody text for {name}.\n"
    )


def _vault_with_titles(brain_dir: Path, count: int = 20) -> dict[str, str]:
    """Create a vault where each note has a unique H1 title; return stem→title map."""
    notes: dict[str, str] = {}
    title_map: dict[str, str] = {}
    all_names = [f"Note Number {i}" for i in range(count)]
    for i in range(count):
        stem = f"note_{i:02d}"
        title = all_names[i]
        others = all_names[:i] + all_names[i + 1 :]
        linked = others[:3]
        notes[stem] = _note_with_entities(title, linked)
        title_map[stem] = title
    _write_notes(brain_dir, notes)
    return title_map


# ---------------------------------------------------------------------------
# 1. Distribution enforcement
# ---------------------------------------------------------------------------


def test_distribution_enforcement(tmp_path: Path) -> None:
    """100 qrels → exactly 30 factual, 20 temporal, 20 personalization, 30 abstention."""
    brain_dir = tmp_path / "brain"
    all_names = [f"Entity {i:03d}" for i in range(100)]
    notes: dict[str, str] = {}
    for i, name in enumerate(all_names):
        others = all_names[:i] + all_names[i + 1 :]
        notes[f"note_{i:03d}"] = _note_with_entities(name, others[:3])
    _write_notes(brain_dir, notes)

    qrels = generate_qrels(brain_dir=brain_dir, seed=42, query_count=100)
    assert len(qrels.entries) == 100

    counts = {qt: 0 for qt in ("factual", "temporal", "personalization", "abstention")}
    for entry in qrels.entries:
        counts[entry.query_type] += 1

    assert counts["factual"] == 30, f"Expected 30 factual, got {counts['factual']}"
    assert counts["temporal"] == 20, f"Expected 20 temporal, got {counts['temporal']}"
    assert counts["personalization"] == 20, (
        f"Expected 20 personalization, got {counts['personalization']}"
    )
    assert counts["abstention"] == 30, f"Expected 30 abstention, got {counts['abstention']}"


def test_compute_distribution_small() -> None:
    """_compute_distribution returns correct counts for small inputs."""
    f, t, p, a = _compute_distribution(10)
    assert f + t + p + a == 10
    # With n=10: ceil(3)=3, ceil(2)=2, ceil(2)=2, ceil(3)=3 → sum=10, no trim
    assert f == 3
    assert t == 2
    assert p == 2
    assert a == 3


def test_compute_distribution_1() -> None:
    """_compute_distribution with n=1 sums to 1."""
    counts = _compute_distribution(1)
    assert sum(counts) == 1


def test_compute_distribution_sum_equals_query_count() -> None:
    """_compute_distribution always sums to query_count for a range of values."""
    for n in range(1, 50):
        counts = _compute_distribution(n)
        assert sum(counts) == n, f"n={n}: counts={counts} sum={sum(counts)}"


# ---------------------------------------------------------------------------
# 2. Query text is not a note title
# ---------------------------------------------------------------------------


def test_query_text_not_title(tmp_path: Path) -> None:
    """For every qrel, query_text must not equal any note title in the vault."""
    brain_dir = tmp_path / "brain"
    title_map = _vault_with_titles(brain_dir, count=20)
    all_titles = set(title_map.values())

    qrels = generate_qrels(brain_dir=brain_dir, seed=7, query_count=20)

    for entry in qrels.entries:
        assert entry.query_text not in all_titles, (
            f"Entry {entry.query_id!r} has query_text equal to a note title: "
            f"{entry.query_text!r}"
        )


# ---------------------------------------------------------------------------
# 3. Abstention invariant
# ---------------------------------------------------------------------------


def test_abstention_invariant(tmp_path: Path) -> None:
    """Abstention qrels must have relevant_note_ids=frozenset() and expected_abstain=True."""
    brain_dir = tmp_path / "brain"
    names = [f"Entity {i}" for i in range(10)]
    notes = {
        f"note_{i}": _note_with_entities(name, [n for n in names if n != name][:3])
        for i, name in enumerate(names)
    }
    _write_notes(brain_dir, notes)

    qrels = generate_qrels(brain_dir=brain_dir, seed=99, query_count=20)
    abstention_entries = [e for e in qrels.entries if e.query_type == "abstention"]
    assert abstention_entries, "Expected at least one abstention entry"

    for entry in abstention_entries:
        assert entry.relevant_note_ids == frozenset(), (
            f"Abstention entry {entry.query_id!r} has non-empty relevant_note_ids: "
            f"{entry.relevant_note_ids!r}"
        )
        assert entry.expected_abstain is True, (
            f"Abstention entry {entry.query_id!r} has expected_abstain=False"
        )


def test_non_abstention_has_nonempty_relevant(tmp_path: Path) -> None:
    """Non-abstention qrels must have non-empty relevant_note_ids."""
    brain_dir = tmp_path / "brain"
    names = [f"Entity {i}" for i in range(10)]
    notes = {
        f"note_{i}": _note_with_entities(name, [n for n in names if n != name][:3])
        for i, name in enumerate(names)
    }
    _write_notes(brain_dir, notes)

    qrels = generate_qrels(brain_dir=brain_dir, seed=5, query_count=20)
    for entry in qrels.entries:
        if entry.query_type != "abstention":
            assert entry.relevant_note_ids, (
                f"Non-abstention entry {entry.query_id!r} has empty relevant_note_ids"
            )
            assert entry.expected_abstain is False


# ---------------------------------------------------------------------------
# 4. Verifier — mock agreement
# ---------------------------------------------------------------------------


def _make_mock_response(relevant_ids: list[str], answerable: bool) -> MagicMock:
    """Build a MagicMock that looks like a litellm completion response."""
    response = MagicMock()
    response.choices[0].message.content = json.dumps(
        {"relevant_ids": relevant_ids, "answerable": answerable}
    )
    return response


def test_verifier_mock_agreement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mocked LiteLLM returning matching IDs → verify_qrel returns (True, entry)."""
    entry = QrelEntry(
        query_id="q0000",
        query_text="What projects is Alice working on?",
        relevant_note_ids=frozenset({"alice", "bob"}),
        query_type="factual",
        expected_abstain=False,
    )
    vault_summary = {"alice": "Alice manages the Chrysalis rollout", "bob": "Bob assists Alice"}

    call_count = 0

    def mock_completion(**kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        return _make_mock_response(["alice", "bob"], answerable=True)

    monkeypatch.setattr("brain_wrought_engine.retrieval.verifier.completion", mock_completion)

    valid, returned_entry = verify_qrel(entry, vault_summary, base_seed=42)

    assert valid is True
    assert returned_entry is entry
    assert call_count == 1  # No retries needed


def test_verifier_mock_agreement_abstention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mocked LLM returning answerable=false for abstention → (True, entry)."""
    entry = QrelEntry(
        query_id="q0001",
        query_text="What is Alice's relationship with the Xenotopia initiative?",
        relevant_note_ids=frozenset(),
        query_type="abstention",
        expected_abstain=True,
    )
    vault_summary = {"alice": "Alice manages Project Aurora"}

    def mock_completion(**kwargs: Any) -> MagicMock:
        return _make_mock_response([], answerable=False)

    monkeypatch.setattr("brain_wrought_engine.retrieval.verifier.completion", mock_completion)

    valid, returned_entry = verify_qrel(entry, vault_summary, base_seed=10)

    assert valid is True
    assert returned_entry is entry


# ---------------------------------------------------------------------------
# 5. Verifier — mock disagreement (retries exhausted)
# ---------------------------------------------------------------------------


def test_verifier_mock_disagreement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mocked LiteLLM returning wrong IDs → retries 3x then returns (False, None)."""
    entry = QrelEntry(
        query_id="q0002",
        query_text="What projects is Alice working on?",
        relevant_note_ids=frozenset({"alice"}),
        query_type="factual",
        expected_abstain=False,
    )
    vault_summary = {"alice": "Alice manages things", "bob": "Bob helps"}

    call_count = 0

    def mock_completion(**kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        # Always return wrong IDs
        return _make_mock_response(["bob"], answerable=True)

    monkeypatch.setattr("brain_wrought_engine.retrieval.verifier.completion", mock_completion)

    valid, returned_entry = verify_qrel(entry, vault_summary, base_seed=0)

    assert valid is False
    assert returned_entry is None
    assert call_count == 3, f"Expected exactly 3 calls, got {call_count}"


def test_verifier_mock_disagreement_abstention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Abstention: LLM always says answerable=True → 3 retries → (False, None)."""
    entry = QrelEntry(
        query_id="q0003",
        query_text="What is Alice's relationship with Dr. Zephyr Ixion?",
        relevant_note_ids=frozenset(),
        query_type="abstention",
        expected_abstain=True,
    )
    vault_summary = {"alice": "Alice manages things"}

    call_count = 0

    def mock_completion(**kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        return _make_mock_response(["alice"], answerable=True)

    monkeypatch.setattr("brain_wrought_engine.retrieval.verifier.completion", mock_completion)

    valid, returned_entry = verify_qrel(entry, vault_summary, base_seed=5)

    assert valid is False
    assert returned_entry is None
    assert call_count == 3


# ---------------------------------------------------------------------------
# 6. Determinism preserved
# ---------------------------------------------------------------------------


def test_determinism_preserved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same seed with mocked verifier → identical QrelSet."""
    brain_dir = tmp_path / "brain"
    names = [f"Entity {i}" for i in range(10)]
    notes = {
        f"note_{i}": _note_with_entities(name, [n for n in names if n != name][:3])
        for i, name in enumerate(names)
    }
    _write_notes(brain_dir, notes)

    qrels_a = generate_qrels(brain_dir=brain_dir, seed=42, query_count=10)
    qrels_b = generate_qrels(brain_dir=brain_dir, seed=42, query_count=10)

    assert qrels_a == qrels_b, "QrelSets from identical seeds differ"

    # Also verify different seeds produce different outputs
    qrels_c = generate_qrels(brain_dir=brain_dir, seed=99, query_count=10)
    assert qrels_a != qrels_c, "QrelSets from different seeds should differ"


def test_query_ids_sequential(tmp_path: Path) -> None:
    """Query IDs must be q0000, q0001, … in order."""
    brain_dir = tmp_path / "brain"
    names = [f"Entity {i}" for i in range(10)]
    notes = {
        f"note_{i}": _note_with_entities(name, [n for n in names if n != name][:3])
        for i, name in enumerate(names)
    }
    _write_notes(brain_dir, notes)

    qrels = generate_qrels(brain_dir=brain_dir, seed=1, query_count=5)
    for i, entry in enumerate(qrels.entries):
        expected = f"q{i:04d}"
        assert entry.query_id == expected, (
            f"Entry {i} has query_id={entry.query_id!r}, expected {expected!r}"
        )
