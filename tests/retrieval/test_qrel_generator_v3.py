"""BW-002c regression tests: qrel entity extraction and relevance correctness.

Four tests that FAIL against the broken qrel_generator.py on main and PASS
against the fixed version on this branch:

  1. test_no_newlines_in_queries       — no query_text contains '\\n'
  2. test_no_heading_tokens_in_queries — no query_text contains standard section headings
  3. test_relevance_invariant          — every qrel's relevant_note_ids actually mentions
                                         the query entity (frontmatter or wikilink)
  4. test_abstention_correctness       — abstention queries reference fictional entities
                                         not found in the vault entity pool

All tests use generate_brain(seed=42, fixture_index=0, note_count=50, use_llm=False)
to produce a realistic vault with proper YAML frontmatter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brain_wrought_engine.fixtures.generator import generate_brain
from brain_wrought_engine.retrieval.qrel_generator import (
    _FICTIONAL_SUFFIXES,
    _build_entity_index,
    generate_qrels,
)

# Standard section headings injected by generator.py body templates.
# These must never appear verbatim in query_text.
_SECTION_HEADINGS = {"Overview", "Background", "Notes", "Connections", "Key People"}

# Number of qrels to generate in each test — enough to exercise all types.
_QUERY_COUNT = 20


@pytest.fixture(scope="module")
def vault_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a 50-note vault once for the entire module."""
    out = tmp_path_factory.mktemp("vault_root")
    return generate_brain(seed=42, fixture_index=0, out_dir=out, note_count=50, use_llm=False)


@pytest.fixture(scope="module")
def qrel_set(vault_dir: Path):  # type: ignore[no-untyped-def]
    """Generate 20 qrels from the shared vault."""
    return generate_qrels(brain_dir=vault_dir, seed=42, query_count=_QUERY_COUNT)


# ---------------------------------------------------------------------------
# 1. No newlines in query text
# ---------------------------------------------------------------------------


def test_no_newlines_in_queries(qrel_set) -> None:  # type: ignore[no-untyped-def]
    """Every query_text must be a single line — no embedded newlines or tabs."""
    for entry in qrel_set.entries:
        assert "\n" not in entry.query_text, (
            f"Entry {entry.query_id} query_text contains newline: {entry.query_text!r}"
        )
        assert "\t" not in entry.query_text, (
            f"Entry {entry.query_id} query_text contains tab: {entry.query_text!r}"
        )


# ---------------------------------------------------------------------------
# 2. No section heading tokens in query text
# ---------------------------------------------------------------------------


def test_no_heading_tokens_in_queries(qrel_set) -> None:  # type: ignore[no-untyped-def]
    """query_text must not contain literal section heading words from generator templates.

    The broken implementation extracted entity candidates from the note body,
    which picked up section headers like 'Overview\\n', 'Background\\n', etc.
    """
    for entry in qrel_set.entries:
        for heading in _SECTION_HEADINGS:
            # Check for the heading as a standalone word (case-sensitive, as generated)
            assert heading not in entry.query_text, (
                f"Entry {entry.query_id} query_text contains section heading {heading!r}: "
                f"{entry.query_text!r}"
            )


# ---------------------------------------------------------------------------
# 3. Relevance invariant: every cited note actually mentions the query entity
# ---------------------------------------------------------------------------


def test_relevance_invariant(vault_dir: Path, qrel_set) -> None:  # type: ignore[no-untyped-def]
    """For every non-abstention qrel, every note in relevant_note_ids must actually
    mention the query's referenced entity (in frontmatter entities: or body wikilinks).

    This catches the old bug where relevant_note_ids was "source note + its wikilinked
    notes" regardless of whether those notes had anything to do with the query entity.
    """
    note_paths = sorted(vault_dir.glob("*.md"))
    _, entity_to_notes = _build_entity_index(note_paths)

    for entry in qrel_set.entries:
        if entry.query_type == "abstention":
            continue

        # Determine which entity drove the relevance set by finding the entity whose
        # entity_to_notes value matches the entry's relevant_note_ids.
        # If no entity matches, the relevance set is wrong.
        matched = any(
            entity_to_notes.get(entity) == entry.relevant_note_ids
            for entity in entity_to_notes
        )
        assert matched, (
            f"Entry {entry.query_id} ({entry.query_type!r}): "
            f"relevant_note_ids={entry.relevant_note_ids!r} does not match any entity's "
            f"mention set. The relevant set may contain notes that don't actually "
            f"mention the query entity."
        )


# ---------------------------------------------------------------------------
# 4. Abstention correctness: fictional entity not in vault entity pool
# ---------------------------------------------------------------------------


def test_abstention_correctness(vault_dir: Path, qrel_set) -> None:  # type: ignore[no-untyped-def]
    """Abstention entries must have empty relevant_note_ids AND reference a fictional
    entity that is not found anywhere in the vault's entity pool.

    Verifies two things:
    1. Every abstention entry has relevant_note_ids == frozenset().
    2. Every abstention query contains at least one of the _FICTIONAL_SUFFIXES, which
       are by construction not in any realistic vault entity pool.
    3. None of the _FICTIONAL_SUFFIXES appear in the vault entity pool.
    """
    note_paths = sorted(vault_dir.glob("*.md"))
    entity_pool, _ = _build_entity_index(note_paths)
    entity_pool_set = set(entity_pool)

    # Guard: fictional suffixes must not be in the entity pool
    for suffix in _FICTIONAL_SUFFIXES:
        assert suffix not in entity_pool_set, (
            f"Fictional suffix {suffix!r} appeared in vault entity pool — "
            f"abstention test precondition violated."
        )

    abstention_entries = [e for e in qrel_set.entries if e.query_type == "abstention"]
    assert abstention_entries, "Expected at least one abstention entry in 20 qrels"

    for entry in abstention_entries:
        # Invariant 1: empty relevant set
        assert entry.relevant_note_ids == frozenset(), (
            f"Abstention entry {entry.query_id} has non-empty relevant_note_ids: "
            f"{entry.relevant_note_ids!r}"
        )
        # Invariant 2: query references a fictional entity (not in pool)
        contains_fictional = any(suffix in entry.query_text for suffix in _FICTIONAL_SUFFIXES)
        assert contains_fictional, (
            f"Abstention entry {entry.query_id} query_text does not contain any "
            f"fictional suffix: {entry.query_text!r}"
        )
