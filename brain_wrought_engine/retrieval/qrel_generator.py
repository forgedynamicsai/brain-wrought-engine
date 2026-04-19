"""Deterministic qrel (query-relevance judgment) generator for the retrieval axis.

Determinism class: SEEDED_STOCHASTIC — same seed + same brain_dir contents
produces bit-identical output regardless of when or where it is run.

Public API
----------
generate_qrels(*, brain_dir, seed, query_count, qrel_version) -> QrelSet

Relevance definition
--------------------
A note N is relevant to a query Q about entity E iff:
  - E appears in N's frontmatter ``entities:`` list, OR
  - E appears as a ``[[wikilink]]`` target in N's body.

Entity pool
-----------
The pool of query-able entities is the union of all ``entities:`` lists found
in YAML frontmatter across the vault.  Notes without a populated ``entities:``
field contribute nothing to the pool.  If the pool is empty, ``generate_qrels``
raises ``ValueError`` rather than silently producing broken queries.
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from brain_wrought_engine.retrieval.models import QrelEntry, QrelSet

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)

# Month names for temporal extraction
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
_MONTH_RE = re.compile(
    r"\b(" + "|".join(_MONTH_NAMES) + r")\b"
    r"|\bthis week\b|\blast week\b|\bthis month\b|\blast month\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

# Generic timeframes used when no temporal hints are found in vault content
_GENERIC_TIMEFRAMES = [
    "January", "February", "March", "April", "Q1", "Q2", "Q3", "Q4",
    "last month", "this week", "last week",
]

# Fictional suffixes that are obviously not in any real vault entity pool.
# Used in abstention queries to reference something the vault cannot answer.
_FICTIONAL_SUFFIXES = [
    "the Xenotopia initiative",
    "the Paradox Engine project",
    "Argus Prime",
    "the Nullspace protocol",
    "Dr. Zephyr Ixion",
    "the Vermillion accord",
    "Operation Kaleidoscope",
    "the Hollowgram summit",
    "Tesseract Division",
    "the Chrysalis rollout",
]

# Query templates per type
_FACTUAL_TEMPLATES = [
    "What projects is {entity} working on?",
    "When did {project} ship?",
    "What does {entity} think about {topic}?",
]

_TEMPORAL_TEMPLATES = [
    "Who did I meet in {timeframe}?",
    "What changed this month related to {topic}?",
    "What was discussed in {timeframe}?",
]

_PERSONALIZATION_TEMPLATES = [
    "Show me my notes about {topic}",
    "What are my thoughts on {entity}?",
    "What have I written about {topic}?",
]


def _parse_frontmatter_entities(content: str) -> list[str]:
    """Extract the ``entities:`` list from YAML frontmatter only.

    Returns an empty list if the note has no frontmatter, the frontmatter has
    no ``entities:`` key, or the frontmatter cannot be parsed.  Never reads the
    note body, section headers, or title.
    """
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return []
    # Strip opening "---\\n" (4 chars) and closing "\\n---\\n" (5 chars)
    inner = m.group(0)[4:-5]
    try:
        data = yaml.safe_load(inner)
        if isinstance(data, dict):
            raw = data.get("entities", [])
            if isinstance(raw, list):
                return [str(e).strip() for e in raw if e is not None and str(e).strip()]
    except yaml.YAMLError:
        pass
    return []


def _extract_wikilinks(content: str) -> frozenset[str]:
    """Return raw wikilink target strings from the note body (frontmatter stripped)."""
    body = _FRONTMATTER_RE.sub("", content, count=1)
    return frozenset(
        m.group(1).strip() for m in _WIKILINK_RE.finditer(body) if m.group(1).strip()
    )


def _extract_timeframes(content: str) -> list[str]:
    """Extract temporal hints from note body content (month names, relative phrases, dates)."""
    body = _FRONTMATTER_RE.sub("", content, count=1)
    found: list[str] = []
    for match in _MONTH_RE.finditer(body):
        hint = match.group(0)
        if hint not in found:
            found.append(hint)
    return found


def _build_entity_index(
    note_paths: list[Path],
) -> tuple[list[str], dict[str, frozenset[str]]]:
    """Build entity pool and entity-to-notes mapping from vault note paths.

    Entity pool: sorted union of all ``entities:`` values from frontmatter.
    entity_to_notes: entity name → frozenset of note_ids (stems) where the entity
    appears in frontmatter ``entities:`` OR body ``[[wikilinks]]``.

    Parameters
    ----------
    note_paths:
        Sorted list of ``.md`` file paths in the vault.

    Returns
    -------
    entity_pool:
        Sorted list of entity name strings (deterministic ordering for RNG).
    entity_to_notes:
        Mapping from entity name to frozenset of note stems that mention it.
    """
    note_contents: dict[str, str] = {}
    entity_pool_set: set[str] = set()

    for path in note_paths:
        content = path.read_text(encoding="utf-8")
        note_contents[path.stem] = content
        entity_pool_set.update(_parse_frontmatter_entities(content))

    entity_pool = sorted(entity_pool_set)

    entity_to_notes_mut: dict[str, set[str]] = {e: set() for e in entity_pool}
    for note_id, content in note_contents.items():
        fm_entities = set(_parse_frontmatter_entities(content))
        wikilink_targets = _extract_wikilinks(content)
        for entity in entity_pool:
            if entity in fm_entities or entity in wikilink_targets:
                entity_to_notes_mut[entity].add(note_id)

    return entity_pool, {k: frozenset(v) for k, v in entity_to_notes_mut.items()}


def _validate_query_text(query_text: str) -> None:
    """Raise ValueError if query_text contains newlines, tabs, or heading-like lines."""
    if "\n" in query_text:
        raise ValueError(f"query_text contains newline: {query_text!r}")
    if "\t" in query_text:
        raise ValueError(f"query_text contains tab: {query_text!r}")
    for line in query_text.splitlines():
        if line.lstrip().startswith("#"):
            raise ValueError(f"query_text contains heading token: {query_text!r}")


def _generate_factual(
    entity_pool: list[str],
    entity_to_notes: dict[str, frozenset[str]],
    rng: random.Random,
) -> QrelEntry:
    """Generate a factual query about a pooled entity."""
    entity = rng.choice(entity_pool)
    topic = rng.choice(entity_pool)
    template = rng.choice(_FACTUAL_TEMPLATES)
    query_text = template.format(entity=entity, project=entity, topic=topic)
    _validate_query_text(query_text)
    return QrelEntry(
        query_id="",
        query_text=query_text,
        relevant_note_ids=entity_to_notes.get(entity, frozenset()),
        query_type="factual",
        expected_abstain=False,
    )


def _generate_temporal(
    entity_pool: list[str],
    entity_to_notes: dict[str, frozenset[str]],
    timeframes: list[str],
    rng: random.Random,
) -> QrelEntry:
    """Generate a temporal query using vault-extracted timeframes and a pooled entity as topic."""
    topic = rng.choice(entity_pool)
    timeframe = rng.choice(timeframes)
    template = rng.choice(_TEMPORAL_TEMPLATES)
    query_text = template.format(timeframe=timeframe, topic=topic)
    _validate_query_text(query_text)
    return QrelEntry(
        query_id="",
        query_text=query_text,
        relevant_note_ids=entity_to_notes.get(topic, frozenset()),
        query_type="temporal",
        expected_abstain=False,
    )


def _generate_personalization(
    entity_pool: list[str],
    entity_to_notes: dict[str, frozenset[str]],
    rng: random.Random,
) -> QrelEntry:
    """Generate a first-person personalization query about a pooled entity."""
    entity = rng.choice(entity_pool)
    topic = rng.choice(entity_pool)
    template = rng.choice(_PERSONALIZATION_TEMPLATES)
    query_text = template.format(entity=entity, topic=topic)
    _validate_query_text(query_text)
    return QrelEntry(
        query_id="",
        query_text=query_text,
        relevant_note_ids=entity_to_notes.get(entity, frozenset()),
        query_type="personalization",
        expected_abstain=False,
    )


def _generate_abstention(
    entity_pool: list[str],
    rng: random.Random,
) -> QrelEntry:
    """Generate a query about something NOT answerable from the vault.

    Uses a real entity from the pool as the subject but pairs it with a
    fictional suffix that cannot exist in any realistic vault entity pool.
    The fictional suffix is the entity the vault cannot answer about.
    """
    entity = rng.choice(entity_pool)
    fictional_suffix = rng.choice(_FICTIONAL_SUFFIXES)
    query_text = f"What is {entity}'s relationship with {fictional_suffix}?"
    _validate_query_text(query_text)
    return QrelEntry(
        query_id="",
        query_text=query_text,
        relevant_note_ids=frozenset(),
        query_type="abstention",
        expected_abstain=True,
    )


def _compute_distribution(query_count: int) -> tuple[int, int, int, int]:
    """Compute (factual, temporal, personalization, abstention) counts.

    Distribution target: 30% factual, 20% temporal, 20% personalization, 30% abstention.
    Each bucket is ceil(fraction * n); if the sum exceeds query_count, trim the
    largest bucket by the excess.

    Returns a 4-tuple (n_factual, n_temporal, n_personal, n_abstain).
    """
    n_factual = math.ceil(0.30 * query_count)
    n_temporal = math.ceil(0.20 * query_count)
    n_personal = math.ceil(0.20 * query_count)
    n_abstain = math.ceil(0.30 * query_count)

    counts = [n_factual, n_temporal, n_personal, n_abstain]
    excess = sum(counts) - query_count
    if excess > 0:
        order = sorted(range(len(counts)), key=lambda i: -counts[i])
        for idx in order:
            if excess <= 0:
                break
            trim = min(excess, counts[idx])
            counts[idx] -= trim
            excess -= trim

    return (counts[0], counts[1], counts[2], counts[3])


def generate_qrels(
    *,
    brain_dir: Path,
    seed: int,
    query_count: int = 50,
    qrel_version: str = "v1",
) -> QrelSet:
    """Generate a deterministic set of typed query-relevance judgments.

    Parameters
    ----------
    brain_dir:
        Path to an Obsidian-style brain vault directory.  All ``.md`` files
        directly inside this directory are treated as notes.
    seed:
        Randomness seed.  Identical (seed, brain_dir contents) pairs always
        produce identical output.
    query_count:
        Number of qrel entries to generate.
    qrel_version:
        Opaque version tag embedded in the returned :class:`QrelSet`.

    Returns
    -------
    QrelSet
        Immutable collection of typed query-relevance judgments.

    Raises
    ------
    ValueError
        If *brain_dir* contains no ``.md`` files, or if the vault has no
        ``entities:`` fields in any note's frontmatter (which would produce
        broken queries referencing arbitrary text instead of real entities).
    """
    note_paths = sorted(brain_dir.glob("*.md"))
    if not note_paths:
        raise ValueError("brain_dir contains no .md notes")

    entity_pool, entity_to_notes = _build_entity_index(note_paths)
    if not entity_pool:
        raise ValueError(
            "No entities found in vault frontmatter entities: fields. "
            "At least one note must have a populated entities: list."
        )

    # Collect temporal hints across all notes; fall back to generic list
    all_timeframes: list[str] = []
    seen_tf: set[str] = set()
    for path in note_paths:
        content = path.read_text(encoding="utf-8")
        for hint in _extract_timeframes(content):
            if hint not in seen_tf:
                all_timeframes.append(hint)
                seen_tf.add(hint)
    if not all_timeframes:
        all_timeframes = list(_GENERIC_TIMEFRAMES)

    rng = random.Random(seed)
    n_factual, n_temporal, n_personal, n_abstain = _compute_distribution(query_count)

    entries: list[QrelEntry] = []

    for _ in range(n_factual):
        entries.append(_generate_factual(entity_pool, entity_to_notes, rng))
    for _ in range(n_temporal):
        entries.append(_generate_temporal(entity_pool, entity_to_notes, all_timeframes, rng))
    for _ in range(n_personal):
        entries.append(_generate_personalization(entity_pool, entity_to_notes, rng))
    for _ in range(n_abstain):
        entries.append(_generate_abstention(entity_pool, rng))

    stamped = [
        QrelEntry(
            query_id=f"q{i:04d}",
            query_text=e.query_text,
            relevant_note_ids=e.relevant_note_ids,
            query_type=e.query_type,
            expected_abstain=e.expected_abstain,
        )
        for i, e in enumerate(entries)
    ]

    return QrelSet(
        qrel_version=qrel_version,
        seed=seed,
        entries=tuple(stamped),
    )
