"""Tests for brain_wrought_engine.retrieval.qrel_generator.

Seven tests:
  1. test_determinism               — same seed → identical QrelSet.
  2. test_query_count               — len(qrel_set.entries) == query_count.
  3. test_query_count_with_replacement — query_count > notes still works.
  4. test_relevance_is_entity_based — non-abstention entries have valid non-empty
                                       relevant_note_ids; abstention entries have empty set.
  5. test_wikilink_expansion        — body [[wikilink]] mention of entity E → note is relevant.
  6. test_broken_wikilink_excluded  — phantom [[links]] never produce invalid note IDs.
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
        f"# {name}\n\nBody text.\n"
    )


def _minimal_brain(brain_dir: Path, count: int = 10) -> None:
    """Write *count* notes with frontmatter entities into *brain_dir*.

    Each note declares up to three other notes in its entities: list, giving
    the generator a non-empty entity pool to draw queries from.
    """
    brain_dir.mkdir(parents=True, exist_ok=True)
    names = [f"Entity {i:02d}" for i in range(count)]
    for i, name in enumerate(names):
        others = names[:i] + names[i + 1 :]
        linked = others[:3]
        stem = f"note_{i:02d}"
        content = _note_with_entities(name, linked)
        (brain_dir / f"{stem}.md").write_text(content, encoding="utf-8")


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
    """When query_count > note count, the generator still produces correct count."""
    brain_dir = tmp_path / "brain"
    _minimal_brain(brain_dir, count=3)

    qrels = generate_qrels(brain_dir=brain_dir, seed=99, query_count=10)
    assert len(qrels.entries) == 10


# ---------------------------------------------------------------------------
# 3. Entity-based relevance
# ---------------------------------------------------------------------------


def test_relevance_is_entity_based(tmp_path: Path) -> None:
    """Non-abstention entries must have non-empty relevant_note_ids consisting of real vault IDs.
    Abstention entries must have empty relevant_note_ids.
    """
    brain_dir = tmp_path / "brain"
    _minimal_brain(brain_dir, count=10)

    vault_ids = frozenset(p.stem for p in brain_dir.glob("*.md"))
    qrels = generate_qrels(brain_dir=brain_dir, seed=13, query_count=20)

    for entry in qrels.entries:
        if entry.query_type == "abstention":
            assert entry.relevant_note_ids == frozenset(), (
                f"Abstention entry {entry.query_id} should have empty relevant_note_ids"
            )
        else:
            assert entry.relevant_note_ids, (
                f"Non-abstention entry {entry.query_id} has empty relevant_note_ids"
            )
            invalid = entry.relevant_note_ids - vault_ids
            assert not invalid, (
                f"Entry {entry.query_id} has note IDs not in vault: {invalid}"
            )


# ---------------------------------------------------------------------------
# 4. Wikilink expansion
# ---------------------------------------------------------------------------


def test_wikilink_expansion(tmp_path: Path) -> None:
    """A note with [[Entity]] in the body must be in the relevant set for queries about Entity,
    even if Entity is not in that note's own frontmatter entities: list."""
    brain_dir = tmp_path / "brain"

    # alice: declares "Bob" in frontmatter entities
    alice_content = (
        "---\ntype: person\ncreated: 2024-01-01T00:00:00Z\n"
        "updated: 2024-01-01T00:00:00Z\ntags:\n  - person\n"
        "entities:\n  - Bob\nstate: active\n---\n"
        "# Alice\n\nBody.\n"
    )
    # dave: mentions "Bob" ONLY via body wikilink — not in frontmatter entities
    dave_content = (
        "---\ntype: person\ncreated: 2024-01-01T00:00:00Z\n"
        "updated: 2024-01-01T00:00:00Z\ntags:\n  - person\n"
        "entities:\n  - Alice\nstate: active\n---\n"
        "# Dave\n\nI work with [[Bob]].\n"
    )
    # bob: plain note so "Bob" is in the entity pool (alice's frontmatter)
    bob_content = (
        "---\ntype: person\ncreated: 2024-01-01T00:00:00Z\n"
        "updated: 2024-01-01T00:00:00Z\ntags:\n  - person\n"
        "entities:\n  - Alice\nstate: active\n---\n"
        "# Bob\n\nBody.\n"
    )

    _write_notes(brain_dir, {"alice": alice_content, "dave": dave_content, "bob": bob_content})

    # Entity pool: {"Bob" (alice's fm), "Alice" (dave+bob fm)}
    # entity_to_notes["Bob"] = {alice (frontmatter), dave (body wikilink)}
    # Any entry with relevant_note_ids == {alice, dave} is a Bob-entity query.
    qrels = generate_qrels(brain_dir=brain_dir, seed=0, query_count=100)

    bob_queries = [
        e for e in qrels.entries if e.relevant_note_ids == frozenset({"alice", "dave"})
    ]
    assert bob_queries, (
        "Expected at least one query with relevant_note_ids={alice, dave}. "
        "dave should be relevant via body [[Bob]] wikilink."
    )


# ---------------------------------------------------------------------------
# 5. Broken wikilinks are excluded from relevant_note_ids
# ---------------------------------------------------------------------------


def test_broken_wikilink_excluded(tmp_path: Path) -> None:
    """Phantom [[wikilinks]] pointing to non-existent notes must not produce invalid note IDs.

    Since only real vault note stems can ever appear in relevant_note_ids, a
    [[Ghost]] link where ghost.md does not exist will never pollute any entry.
    """
    brain_dir = tmp_path / "brain"

    alice_content = (
        "---\ntype: person\ncreated: 2024-01-01T00:00:00Z\n"
        "updated: 2024-01-01T00:00:00Z\ntags:\n  - person\n"
        "entities:\n  - Bob\nstate: active\n---\n"
        "# Alice\n\nShe knows [[Bob]] and [[Ghost]].\n"
    )
    bob_content = (
        "---\ntype: person\ncreated: 2024-01-01T00:00:00Z\n"
        "updated: 2024-01-01T00:00:00Z\ntags:\n  - person\n"
        "entities:\n  - Alice\nstate: active\n---\n"
        "# Bob\n\nBody.\n"
    )

    _write_notes(brain_dir, {"alice": alice_content, "bob": bob_content})

    vault_ids = frozenset({"alice", "bob"})
    qrels = generate_qrels(brain_dir=brain_dir, seed=0, query_count=100)

    for entry in qrels.entries:
        invalid = entry.relevant_note_ids - vault_ids
        assert not invalid, (
            f"Entry {entry.query_id} has note IDs outside the vault: {invalid}"
        )


# ---------------------------------------------------------------------------
# 6. text_utils.slug() property tests
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
# 7. Empty brain raises ValueError
# ---------------------------------------------------------------------------


def test_empty_brain_raises(tmp_path: Path) -> None:
    """generate_qrels must raise ValueError when brain_dir has no .md files."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(ValueError, match="brain_dir contains no .md notes"):
        generate_qrels(brain_dir=empty_dir, seed=1)


# ---------------------------------------------------------------------------
# 8. No-entity vault raises ValueError
# ---------------------------------------------------------------------------


def test_no_entity_vault_raises(tmp_path: Path) -> None:
    """generate_qrels must raise ValueError when no note has a populated entities: list."""
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    # Plain notes with no frontmatter entities
    for i in range(3):
        (brain_dir / f"note_{i}.md").write_text(
            f"# Note {i}\n\nBody text.\n", encoding="utf-8"
        )

    with pytest.raises(ValueError, match="No entities found"):
        generate_qrels(brain_dir=brain_dir, seed=1)
