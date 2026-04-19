"""BW-002c regression tests: qrel entity extraction and relevance correctness.

Four tests that FAIL against the broken qrel_generator.py on main and PASS
against the fixed version on this branch:

  1. test_no_newlines_in_queries       — no query_text contains '\\n'
  2. test_no_heading_tokens_in_queries — no query_text contains standard section headings
  3. test_relevance_invariant          — every qrel's relevant_note_ids equals the mention
                                         set of the entity referenced in query_text
  4. test_abstention_correctness       — abstention queries reference fictional entities
                                         not found in the vault entity pool

Additional test:
  5. test_self_relevance_retained      — for any non-abstention entry about entity E,
                                         if a note with stem slug(E) exists, that note
                                         must appear in relevant_note_ids.

All tests use generate_brain(seed=42, fixture_index=0, note_count=50, use_llm=False)
to produce a realistic vault with proper YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from brain_wrought_engine.fixtures.generator import generate_brain
from brain_wrought_engine.retrieval.qrel_generator import (
    _FICTIONAL_SUFFIXES,
    _build_entity_index,
    generate_qrels,
)
from brain_wrought_engine.text_utils import slug

# Standard section headings injected by generator.py body templates.
# These must never appear verbatim in query_text.
_SECTION_HEADINGS = {"Overview", "Background", "Notes", "Connections", "Key People"}

# Number of qrels to generate in each test — enough to exercise all types.
_QUERY_COUNT = 20

# Regex patterns that extract the entity (or topic acting as entity) from each
# query template.  Every non-abstention template must match exactly one pattern.
_ENTITY_PATTERNS: list[re.Pattern[str]] = [
    # Factual
    re.compile(r"^What projects is (.+) working on\?$"),
    re.compile(r"^When did (.+) ship\?$"),
    re.compile(r"^What does (.+) think about .+\?$"),
    # Temporal (topic always embedded after BW-002c fix)
    re.compile(r"^Who did I meet about (.+) in .+\?$"),
    re.compile(r"^What changed this month related to (.+)\?$"),
    re.compile(r"^What was discussed about (.+) in .+\?$"),
    # Personalization (entity always embedded after BW-002c fix)
    re.compile(r"^Show me my notes about (.+)$"),
    re.compile(r"^What are my thoughts on (.+)\?$"),
    re.compile(r"^What have I written about (.+)\?$"),
]


def _extract_query_entity(query_text: str) -> str | None:
    """Return the entity name embedded in query_text, or None if no pattern matches."""
    for pattern in _ENTITY_PATTERNS:
        m = pattern.match(query_text)
        if m:
            return m.group(1)
    return None


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
# 3. Relevance invariant: relevant_note_ids matches the entity referenced in text
# ---------------------------------------------------------------------------


def test_relevance_invariant(vault_dir: Path, qrel_set) -> None:  # type: ignore[no-untyped-def]
    """For every non-abstention qrel, relevant_note_ids must equal entity_to_notes for the
    specific entity referenced in query_text (extracted via template pattern matching).

    This is stronger than checking that relevant_note_ids matches SOME entity's mention set:
    it verifies the correct entity was used, preventing coincidental matches where an
    unrelated entity happens to have the same mention set.
    """
    note_paths = sorted(vault_dir.glob("*.md"))
    _, entity_to_notes = _build_entity_index(note_paths)

    for entry in qrel_set.entries:
        if entry.query_type == "abstention":
            continue

        entity = _extract_query_entity(entry.query_text)
        assert entity is not None, (
            f"Entry {entry.query_id} ({entry.query_type!r}): "
            f"could not extract entity from query_text={entry.query_text!r}. "
            f"All non-abstention templates must embed the relevant entity in query text."
        )

        expected = entity_to_notes.get(entity, frozenset())
        assert entry.relevant_note_ids == expected, (
            f"Entry {entry.query_id} ({entry.query_type!r}): "
            f"relevant_note_ids={entry.relevant_note_ids!r} != "
            f"entity_to_notes[{entity!r}]={expected!r}"
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


# ---------------------------------------------------------------------------
# 5. Self-relevance retained: entity's own note is in its relevant set
# ---------------------------------------------------------------------------


def test_self_relevance_retained(vault_dir: Path, qrel_set) -> None:  # type: ignore[no-untyped-def]
    """For any non-abstention entry whose query references entity E, if a note with stem
    slug(E) exists in the vault then slug(E) must appear in entry.relevant_note_ids.

    This guards against the bug where Beatrix_Müller.md was excluded from queries about
    Beatrix Müller because her own frontmatter didn't list herself as an entity.
    """
    note_paths = sorted(vault_dir.glob("*.md"))
    stem_set = {p.stem for p in note_paths}

    for entry in qrel_set.entries:
        if entry.query_type == "abstention":
            continue

        entity = _extract_query_entity(entry.query_text)
        if entity is None:
            continue

        entity_slug = slug(entity)
        if entity_slug in stem_set:
            assert entity_slug in entry.relevant_note_ids, (
                f"Entry {entry.query_id} ({entry.query_type!r}): "
                f"entity {entity!r} has own note {entity_slug!r} in vault "
                f"but it is absent from relevant_note_ids={entry.relevant_note_ids!r}"
            )
