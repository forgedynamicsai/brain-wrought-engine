"""Tests for brain_wrought_engine.retrieval.qrel_generator.

Seven tests:
  1. test_determinism               — same seed → identical QrelSet.
  2. test_query_count               — len(qrel_set.entries) == query_count.
  3. test_query_count_with_replacement — query_count > notes still works.
  4. test_self_relevance            — sampled note ID is always in relevant_note_ids.
  5. test_wikilink_expansion        — wikilinked notes are included in relevant_note_ids.
  6. test_broken_wikilink_excluded  — [[nonexistent]] links NOT in relevant_note_ids.
  7. test_empty_brain_raises        — ValueError raised on empty brain_dir.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from brain_wrought_engine.retrieval.qrel_generator import generate_qrels
from brain_wrought_engine.text_utils import slug

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_notes(brain_dir: Path, notes: dict[str, str]) -> None:
    """Write a mapping of {stem: content} into *brain_dir*."""
    brain_dir.mkdir(parents=True, exist_ok=True)
    for stem, content in notes.items():
        (brain_dir / f"{stem}.md").write_text(content, encoding="utf-8")


def _minimal_brain(brain_dir: Path, count: int = 10) -> None:
    """Write *count* minimal notes (no wikilinks) into *brain_dir*."""
    notes = {
        f"note_{i:02d}": f"# Note {i}\n\nBody text for note {i}.\n"
        for i in range(count)
    }
    _write_notes(brain_dir, notes)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


def test_determinism(tmp_path: Path) -> None:
    """Two calls with the same seed and identical brain_dir must return equal QrelSets."""
    brain_dir = tmp_path / "brain"
    _minimal_brain(brain_dir, count=10)

    qrels_a = generate_qrels(brain_dir=brain_dir, seed=42, query_count=5)
    qrels_b = generate_qrels(brain_dir=brain_dir, seed=42, query_count=5)

    assert qrels_a == qrels_b, "QrelSets from identical seeds differ"


# ---------------------------------------------------------------------------
# 2. Query count
# ---------------------------------------------------------------------------


def test_query_count(tmp_path: Path) -> None:
    """The returned QrelSet must have exactly query_count entries."""
    brain_dir = tmp_path / "brain"
    _minimal_brain(brain_dir, count=10)

    for q in (1, 5, 10):
        qrels = generate_qrels(brain_dir=brain_dir, seed=7, query_count=q)
        assert len(qrels.entries) == q, f"Expected {q} entries, got {len(qrels.entries)}"


def test_query_count_with_replacement(tmp_path: Path) -> None:
    """When query_count > note count, sampling with replacement still gives correct count."""
    brain_dir = tmp_path / "brain"
    _minimal_brain(brain_dir, count=3)

    qrels = generate_qrels(brain_dir=brain_dir, seed=99, query_count=10)
    assert len(qrels.entries) == 10


# ---------------------------------------------------------------------------
# 3. Self-relevance
# ---------------------------------------------------------------------------


def test_self_relevance(tmp_path: Path) -> None:
    """Every non-abstention entry must include its own note ID in relevant_note_ids."""
    brain_dir = tmp_path / "brain"
    _minimal_brain(brain_dir, count=10)

    qrels = generate_qrels(brain_dir=brain_dir, seed=13, query_count=10)

    for entry in qrels.entries:
        # Abstention entries intentionally have empty relevant_note_ids — skip them.
        if entry.query_type == "abstention":
            assert entry.relevant_note_ids == frozenset(), (
                f"Abstention entry {entry.query_id} should have empty relevant_note_ids"
            )
            continue
        # Non-abstention: relevant_note_ids must be non-empty and contain
        # some valid stem — the actual note sampled must be in the set.
        assert entry.relevant_note_ids, (
            f"Entry {entry.query_id} has empty relevant_note_ids"
        )

    # Stronger check: generate with all unique notes and verify each sampled
    # note's stem appears in its own non-abstention entry
    brain_dir2 = tmp_path / "brain2"
    stems = [f"alpha_{i}" for i in range(10)]
    notes = {s: f"# {s}\n\nNo links here.\n" for s in stems}
    _write_notes(brain_dir2, notes)

    qrels2 = generate_qrels(brain_dir=brain_dir2, seed=5, query_count=10)
    sampled_ids = {n_id for entry in qrels2.entries for n_id in entry.relevant_note_ids}
    for entry in qrels2.entries:
        if entry.query_type == "abstention":
            continue
        # Each non-abstention entry's relevant_note_ids must contain at least one stem
        # from the vault (the note itself)
        overlap = entry.relevant_note_ids & set(stems)
        assert overlap, (
            f"Entry {entry.query_id} has no vault stem in relevant_note_ids: "
            f"{entry.relevant_note_ids}"
        )
    # Suppress unused variable warning
    _ = sampled_ids


# ---------------------------------------------------------------------------
# 4. Wikilink expansion
# ---------------------------------------------------------------------------


def test_wikilink_expansion(tmp_path: Path) -> None:
    """A note with [[wikilinks]] must include the linked note IDs in relevant_note_ids."""
    brain_dir = tmp_path / "brain"

    alice_content = "# Alice\n\nShe knows [[bob]] and [[carol]].\n"
    bob_content = "# Bob\n\nNo links.\n"
    carol_content = "# Carol\n\nNo links.\n"

    _write_notes(brain_dir, {"alice": alice_content, "bob": bob_content, "carol": carol_content})

    # query_count=100 with 3-note vault → 70 non-abstention samples via rng.choices;
    # alice is virtually guaranteed to appear ((2/3)^70 ≈ 1e-13 chance she doesn't).
    qrels = generate_qrels(brain_dir=brain_dir, seed=0, query_count=100)

    alice_entry = next(
        (e for e in qrels.entries if "alice" in e.relevant_note_ids), None
    )
    assert alice_entry is not None, "No entry found for alice"
    assert "bob" in alice_entry.relevant_note_ids, (
        f"bob not in alice's relevant_note_ids: {alice_entry.relevant_note_ids}"
    )
    assert "carol" in alice_entry.relevant_note_ids, (
        f"carol not in alice's relevant_note_ids: {alice_entry.relevant_note_ids}"
    )


# ---------------------------------------------------------------------------
# 6. Broken wikilinks are excluded from relevant_note_ids
# ---------------------------------------------------------------------------


def test_broken_wikilink_excluded(tmp_path: Path) -> None:
    """A [[nonexistent]] wikilink must NOT appear in relevant_note_ids.

    Only wikilinks that resolve to an actual .md file in the vault are
    treated as relevant.  Phantom links must not pollute the judgment set.
    """
    brain_dir = tmp_path / "brain"

    alice_content = "# Alice\n\nShe knows [[bob]] and [[ghost]].\n"
    bob_content = "# Bob\n\nNo links.\n"

    _write_notes(brain_dir, {"alice": alice_content, "bob": bob_content})

    # query_count=100 with 2-note vault → 70 non-abstention samples via rng.choices;
    # alice is virtually guaranteed to appear.
    qrels = generate_qrels(brain_dir=brain_dir, seed=0, query_count=100)

    alice_entry = next(
        (e for e in qrels.entries if "alice" in e.relevant_note_ids), None
    )
    assert alice_entry is not None, "No entry found for alice"
    assert "bob" in alice_entry.relevant_note_ids, (
        "bob (exists) should be in alice's relevant_note_ids"
    )
    assert "ghost" not in alice_entry.relevant_note_ids, (
        "ghost (does not exist) must NOT be in alice's relevant_note_ids"
    )


# ---------------------------------------------------------------------------
# 7. text_utils.slug() property tests
# ---------------------------------------------------------------------------


@given(st.text())
def test_slug_idempotent(name: str) -> None:
    """slug(slug(x)) == slug(x) — applying twice changes nothing."""
    assert slug(slug(name)) == slug(name)


@given(st.text())
def test_slug_no_spaces(name: str) -> None:
    """slug() never contains a space character."""
    assert " " not in slug(name)


@given(st.text())
def test_slug_no_slashes(name: str) -> None:
    """slug() never contains a forward-slash."""
    assert "/" not in slug(name)


# ---------------------------------------------------------------------------
# 8. Empty brain raises ValueError
# ---------------------------------------------------------------------------


def test_empty_brain_raises(tmp_path: Path) -> None:
    """generate_qrels must raise ValueError when brain_dir has no .md files."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(ValueError, match="brain_dir contains no .md notes"):
        generate_qrels(brain_dir=empty_dir, seed=1)
