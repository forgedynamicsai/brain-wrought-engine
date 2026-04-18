"""Deterministic qrel (query-relevance judgment) generator for the retrieval axis.

Determinism class: SEEDED_STOCHASTIC — same seed + same brain_dir contents
produces bit-identical output regardless of when or where it is run.

Public API
----------
generate_qrels(*, brain_dir, seed, query_count, qrel_version) -> QrelSet
"""

from __future__ import annotations

import random
import re
from pathlib import Path

from brain_wrought_engine.retrieval.models import QrelEntry, QrelSet
from brain_wrought_engine.text_utils import slug

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


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


def generate_qrels(
    *,
    brain_dir: Path,
    seed: int,
    query_count: int = 50,
    qrel_version: str = "v0",
) -> QrelSet:
    """Generate a deterministic set of query-relevance judgments.

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
        Immutable collection of query-relevance judgments.

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

    if query_count <= len(note_ids):
        sampled_ids = rng.sample(note_ids, query_count)
    else:
        sampled_ids = rng.choices(note_ids, k=query_count)

    entries: list[QrelEntry] = []
    for i, note_id in enumerate(sampled_ids):
        note_path = brain_dir / f"{note_id}.md"
        try:
            content = note_path.read_text(encoding="utf-8")
        except OSError:
            content = ""

        query_text = _extract_title(content, note_id)
        linked_ids = _extract_wikilinks(content, vault_ids)

        # The note itself is always relevant; add any wikilinked notes that
        # exist in the vault (broken links are excluded by _extract_wikilinks)
        relevant_note_ids: frozenset[str] = frozenset({note_id}) | linked_ids

        entries.append(
            QrelEntry(
                query_id=f"q{i:04d}",
                query_text=query_text,
                relevant_note_ids=relevant_note_ids,
            )
        )

    return QrelSet(
        qrel_version=qrel_version,
        seed=seed,
        entries=tuple(entries),
    )
