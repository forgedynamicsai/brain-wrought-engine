"""Deterministic qrel (query-relevance judgment) generator for the retrieval axis.

Determinism class: SEEDED_STOCHASTIC — same seed + same brain_dir contents
produces bit-identical output regardless of when or where it is run.

Public API
----------
generate_qrels(*, brain_dir, seed, query_count, qrel_version) -> QrelSet
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path
from typing import Literal

from brain_wrought_engine.retrieval.models import QrelEntry, QrelSet
from brain_wrought_engine.text_utils import slug

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)

# Regex for capitalized multi-word phrases (two or more capitalized words in sequence)
_CAPITALIZED_PHRASE_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")

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

# Generic timeframes used when no temporal hints are found in note content
_GENERIC_TIMEFRAMES = [
    "January", "February", "March", "April", "Q1", "Q2", "Q3", "Q4",
    "last month", "this week", "last week",
]

# Suffixes must be obviously fictional to the verifier. Avoid common names,
# generic corporate terms, or routine business events that could plausibly
# exist in any real vault — if Sonnet hedges, the verifier rejects the qrel.
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


def _extract_title(content: str, stem: str) -> str:
    """Return the note title: first non-empty line after stripping YAML frontmatter.

    Falls back to *stem* if the content cannot be parsed or is empty.
    """
    body = _FRONTMATTER_RE.sub("", content, count=1)
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip() or stem
    return stem


def _extract_wikilinks(content: str, vault_ids: frozenset[str]) -> frozenset[str]:
    """Return wikilinked note IDs that actually exist in the vault.

    Converts each wikilink target to a slug (same convention as
    :func:`brain_wrought_engine.text_utils.slug`) and filters out any IDs
    that do not correspond to an ``.md`` file in the vault.  This prevents
    phantom relevance judgments for broken links.
    """
    targets: set[str] = set()
    for match in _WIKILINK_RE.finditer(content):
        target = match.group(1).strip()
        if target:
            candidate = slug(target)
            if candidate in vault_ids:
                targets.add(candidate)
    return frozenset(targets)


def _extract_entities(content: str, stem: str) -> list[str]:
    """Extract capitalized multi-word phrases and the note stem as entity candidates.

    Returns a de-duplicated list with the stem always included as a fallback.
    """
    found: list[str] = []
    body = _FRONTMATTER_RE.sub("", content, count=1)
    for match in _CAPITALIZED_PHRASE_RE.finditer(body):
        phrase = match.group(1)
        if phrase not in found:
            found.append(phrase)
    # Always include the humanized stem as a fallback entity
    human_stem = stem.replace("_", " ").replace("-", " ").title()
    if human_stem not in found:
        found.append(human_stem)
    return found


def _extract_timeframes(content: str) -> list[str]:
    """Extract temporal hints from note content.

    Looks for month names, relative time phrases ("this week"), or ISO dates.
    Returns unique matches; falls back to an empty list if none found.
    """
    body = _FRONTMATTER_RE.sub("", content, count=1)
    found: list[str] = []
    for match in _MONTH_RE.finditer(body):
        hint = match.group(0)
        if hint not in found:
            found.append(hint)
    return found


def _pick(items: list[str], rng: random.Random, fallback: str) -> str:
    """Pick a random item from a non-empty list, or return the fallback."""
    return rng.choice(items) if items else fallback


def _generate_factual(
    note_id: str,
    content: str,
    vault_ids: frozenset[str],
    rng: random.Random,
) -> QrelEntry:
    """Generate a factual query about entities/topics in the note."""
    entities = _extract_entities(content, note_id)
    entity = _pick(entities, rng, note_id)
    # Pick a second entity for the topic slot; may overlap
    topic = _pick(entities, rng, note_id)
    project = _pick(entities, rng, note_id)

    template = rng.choice(_FACTUAL_TEMPLATES)
    query_text = template.format(entity=entity, project=project, topic=topic)

    linked_ids = _extract_wikilinks(content, vault_ids)
    relevant_note_ids: frozenset[str] = frozenset({note_id}) | linked_ids

    return QrelEntry(
        query_id="",  # filled by caller
        query_text=query_text,
        relevant_note_ids=relevant_note_ids,
        query_type="factual",
        expected_abstain=False,
    )


def _generate_temporal(
    note_id: str,
    content: str,
    vault_ids: frozenset[str],
    rng: random.Random,
) -> QrelEntry:
    """Generate a temporal query using time hints extracted from the note."""
    timeframes = _extract_timeframes(content)
    if not timeframes:
        timeframes = _GENERIC_TIMEFRAMES

    entities = _extract_entities(content, note_id)
    timeframe = _pick(timeframes, rng, "last month")
    topic = _pick(entities, rng, note_id)

    template = rng.choice(_TEMPORAL_TEMPLATES)
    query_text = template.format(timeframe=timeframe, topic=topic)

    linked_ids = _extract_wikilinks(content, vault_ids)
    relevant_note_ids: frozenset[str] = frozenset({note_id}) | linked_ids

    return QrelEntry(
        query_id="",  # filled by caller
        query_text=query_text,
        relevant_note_ids=relevant_note_ids,
        query_type="temporal",
        expected_abstain=False,
    )


def _generate_personalization(
    note_id: str,
    content: str,
    vault_ids: frozenset[str],
    rng: random.Random,
) -> QrelEntry:
    """Generate a first-person personalization query about the note's topic."""
    entities = _extract_entities(content, note_id)
    entity = _pick(entities, rng, note_id)
    topic = _pick(entities, rng, note_id)

    template = rng.choice(_PERSONALIZATION_TEMPLATES)
    query_text = template.format(entity=entity, topic=topic)

    linked_ids = _extract_wikilinks(content, vault_ids)
    relevant_note_ids: frozenset[str] = frozenset({note_id}) | linked_ids

    return QrelEntry(
        query_id="",  # filled by caller
        query_text=query_text,
        relevant_note_ids=relevant_note_ids,
        query_type="personalization",
        expected_abstain=False,
    )


def _generate_abstention(
    vault_ids: frozenset[str],
    rng: random.Random,
) -> QrelEntry:
    """Generate a query about something NOT in the vault.

    Strategy: combine two random vault stems with a fictional suffix to produce
    a plausible-sounding but non-existent entity reference.
    """
    stems = sorted(vault_ids)  # deterministic ordering before rng picks
    if len(stems) >= 2:
        picked = rng.sample(stems, 2)
        stem_a = picked[0]
    elif stems:
        stem_a = stems[0]
    else:
        stem_a = "unknown"

    fictional_suffix = rng.choice(_FICTIONAL_SUFFIXES)
    human_a = stem_a.replace("_", " ").replace("-", " ").title()

    query_text = f"What is {human_a}'s relationship with {fictional_suffix}?"

    return QrelEntry(
        query_id="",  # filled by caller
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
        # Sort indices descending by count so we trim the largest buckets first
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
        Number of qrel entries to generate.  When *query_count* exceeds the
        number of notes in the vault, notes are sampled with replacement.
    qrel_version:
        Opaque version tag embedded in the returned :class:`QrelSet`.

    Returns
    -------
    QrelSet
        Immutable collection of typed query-relevance judgments.

    Raises
    ------
    ValueError
        If *brain_dir* contains no ``.md`` files.
    """
    note_paths = sorted(brain_dir.glob("*.md"))
    if not note_paths:
        raise ValueError("brain_dir contains no .md notes")

    rng = random.Random(seed)
    note_ids = [p.stem for p in note_paths]
    vault_ids: frozenset[str] = frozenset(note_ids)

    n_factual, n_temporal, n_personal, n_abstain = _compute_distribution(query_count)

    # Build a per-type bucket of sampled note IDs (for non-abstention types).
    # Total non-abstention count = n_factual + n_temporal + n_personal
    n_non_abstain = n_factual + n_temporal + n_personal
    if n_non_abstain <= len(note_ids):
        non_abstain_ids = rng.sample(note_ids, n_non_abstain)
    else:
        non_abstain_ids = rng.choices(note_ids, k=n_non_abstain)

    factual_ids = non_abstain_ids[:n_factual]
    temporal_ids = non_abstain_ids[n_factual : n_factual + n_temporal]
    personal_ids = non_abstain_ids[n_factual + n_temporal :]

    # Build typed generator work items in deterministic order:
    # factual first, then temporal, then personalization, then abstention
    work_items: list[tuple[Literal["factual", "temporal", "personalization", "abstention"], str]]
    work_items = []
    for nid in factual_ids:
        work_items.append(("factual", nid))
    for nid in temporal_ids:
        work_items.append(("temporal", nid))
    for nid in personal_ids:
        work_items.append(("personalization", nid))
    for _ in range(n_abstain):
        work_items.append(("abstention", ""))

    entries: list[QrelEntry] = []
    for i, (qtype, note_id) in enumerate(work_items):
        if qtype == "abstention":
            entry = _generate_abstention(vault_ids, rng)
        else:
            note_path = brain_dir / f"{note_id}.md"
            try:
                content = note_path.read_text(encoding="utf-8")
            except OSError:
                content = ""

            if qtype == "factual":
                entry = _generate_factual(note_id, content, vault_ids, rng)
            elif qtype == "temporal":
                entry = _generate_temporal(note_id, content, vault_ids, rng)
            else:  # personalization
                entry = _generate_personalization(note_id, content, vault_ids, rng)

        # Stamp the query_id (frozen model requires reconstruction)
        entry = QrelEntry(
            query_id=f"q{i:04d}",
            query_text=entry.query_text,
            relevant_note_ids=entry.relevant_note_ids,
            query_type=entry.query_type,
            expected_abstain=entry.expected_abstain,
        )
        entries.append(entry)

    return QrelSet(
        qrel_version=qrel_version,
        seed=seed,
        entries=tuple(entries),
    )
