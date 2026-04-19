"""Deterministic degradation transformations for dirty-schema fixture generation.

Each function takes a list of (filename, content) pairs and returns a modified list.
All stochastic operations are driven by a seeded random.Random — no global state.

Degradation functions follow the signature:
    (notes: list[tuple[str, str]], *, seed: int, fraction: float) -> list[tuple[str, str]]

where fraction is derived from dirty_level * pattern_rate, clamped to [0.0, 1.0].
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable

_FM_OPEN_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

_OPTIONAL_FM_FIELDS = ["tags", "updated", "entities", "state"]
_TAG_VARIANTS: list[Callable[[str], str]] = [
    lambda t: t,  # bare: person
    lambda t: f"#{t}",  # hash-prefixed: #person
    lambda t: f"type/{t}",  # namespaced: type/person
    lambda t: t.upper(),  # uppercased: PERSON
]
_NONEXISTENT_TARGETS = [
    "Zylotron_X9",
    "Project_Phantom",
    "Alice_Holloway",
    "Research_Nexus",
    "Meeting_Echo",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Return (frontmatter_block, body) where frontmatter_block includes the delimiters."""
    m = _FM_OPEN_RE.match(content)
    if m:
        return m.group(0), content[m.end() :]
    return "", content


def _select_indices(rng: random.Random, n: int, fraction: float) -> set[int]:
    """Return a deterministic set of indices to degrade, sized floor(fraction * n)."""
    count = max(0, min(n, round(fraction * n)))
    if count == 0 or n == 0:
        return set()
    return set(rng.sample(range(n), count))


# ---------------------------------------------------------------------------
# 1. Stub notes
# ---------------------------------------------------------------------------


def apply_stub_notes(
    notes: list[tuple[str, str]],
    *,
    seed: int,
    fraction: float,
) -> list[tuple[str, str]]:
    """Replace a fraction of notes with minimal stub content.

    The stub retains the original frontmatter verbatim and replaces the body
    with a single TODO line, mimicking an unfleshed note.
    """
    rng = random.Random(seed)
    targets = _select_indices(rng, len(notes), fraction)
    result: list[tuple[str, str]] = []
    for i, (fname, content) in enumerate(notes):
        if i not in targets:
            result.append((fname, content))
            continue
        fm, _body = _split_frontmatter(content)
        stub_body = "\nTODO: flesh out\n"
        result.append((fname, fm + stub_body))
    return result


# ---------------------------------------------------------------------------
# 2. Missing frontmatter fields
# ---------------------------------------------------------------------------


def apply_missing_frontmatter_fields(
    notes: list[tuple[str, str]],
    *,
    seed: int,
    fraction: float,
) -> list[tuple[str, str]]:
    """Remove one optional frontmatter field from a fraction of notes."""
    rng = random.Random(seed)
    targets = _select_indices(rng, len(notes), fraction)
    result: list[tuple[str, str]] = []
    for i, (fname, content) in enumerate(notes):
        if i not in targets:
            result.append((fname, content))
            continue
        fm, body = _split_frontmatter(content)
        if not fm:
            result.append((fname, content))
            continue
        field = rng.choice(_OPTIONAL_FM_FIELDS)
        degraded_fm_lines: list[str] = []
        inner = fm.removeprefix("---\n").removesuffix("\n---\n")
        for line in inner.splitlines():
            key = line.split(":")[0].strip()
            if key == field:
                continue
            degraded_fm_lines.append(line)
        new_fm = "---\n" + "\n".join(degraded_fm_lines) + "\n---\n"
        result.append((fname, new_fm + body))
    return result


# ---------------------------------------------------------------------------
# 3. Stale dates
# ---------------------------------------------------------------------------


def apply_stale_dates(
    notes: list[tuple[str, str]],
    *,
    seed: int,
    fraction: float,
) -> list[tuple[str, str]]:
    """Set updated: to a date before created: in a fraction of notes.

    Uses a fixed stale timestamp that is guaranteed to precede any generated
    created: value (which is always 2024-01-01T00:00:00Z or later).
    """
    rng = random.Random(seed)
    targets = _select_indices(rng, len(notes), fraction)
    stale_date = "2020-01-01T00:00:00Z"
    result: list[tuple[str, str]] = []
    for i, (fname, content) in enumerate(notes):
        if i not in targets:
            result.append((fname, content))
            continue
        fm, body = _split_frontmatter(content)
        if not fm:
            result.append((fname, content))
            continue
        new_fm = re.sub(r"^updated:.*$", f"updated: {stale_date}", fm, flags=re.MULTILINE)
        result.append((fname, new_fm + body))
    return result


# ---------------------------------------------------------------------------
# 4. Broken backlinks
# ---------------------------------------------------------------------------


def apply_broken_backlinks(
    notes: list[tuple[str, str]],
    *,
    seed: int,
    fraction: float,
) -> list[tuple[str, str]]:
    """Replace a fraction of [[wikilinks]] across all notes with non-existent targets.

    The selection is across all wikilinks in all note bodies (not per-note).
    """
    rng = random.Random(seed)

    all_links: list[tuple[int, int, str]] = []
    parsed: list[tuple[str, str, str]] = []
    for i, (fname, content) in enumerate(notes):
        fm, body = _split_frontmatter(content)
        parsed.append((fname, fm, body))
        for m in _WIKILINK_RE.finditer(body):
            all_links.append((i, m.start(), m.group(1)))

    total = len(all_links)
    count = max(0, min(total, round(fraction * total)))
    if count == 0:
        return notes

    chosen = set(rng.sample(range(total), count))
    per_note_replacements: dict[int, list[tuple[str, str]]] = {}
    for link_idx, (note_idx, _pos, target) in enumerate(all_links):
        if link_idx not in chosen:
            continue
        fake = rng.choice(_NONEXISTENT_TARGETS)
        per_note_replacements.setdefault(note_idx, []).append((target, fake))

    result: list[tuple[str, str]] = []
    for i, (fname, fm, body) in enumerate(parsed):
        if i not in per_note_replacements:
            result.append((fname, fm + body))
            continue
        new_body = body
        for original, replacement in per_note_replacements[i]:
            new_body = new_body.replace(f"[[{original}]]", f"[[{replacement}]]", 1)
        result.append((fname, fm + new_body))
    return result


def _rewrite_tags_line(fm: str, variant_fn: Callable[[str], str]) -> str:
    """Rewrite the tags block (inline or multi-line YAML list) using variant_fn.

    Output is always a compact inline form: ``tags: #person, #engineer``
    so that dirty_stats.py can detect alternate conventions on a single line.
    """
    tags_block_re = re.compile(
        r"^(tags:[ \t]*\n(?:[ \t]+-[ \t]+.*\n)*)",
        re.MULTILINE,
    )
    m = tags_block_re.search(fm)
    if m:
        block = m.group(1)
        items = re.findall(r"^\s+-\s+(.+)$", block, flags=re.MULTILINE)
        rewritten = ", ".join(variant_fn(t.strip()) for t in items if t.strip())
        return fm[: m.start()] + f"tags: {rewritten}\n" + fm[m.end() :]

    def _inline_sub(match: re.Match[str]) -> str:
        line = match.group(0)
        rest = line[len("tags:") :]
        tags_raw = [t.strip().lstrip("- ").strip() for t in rest.split(",")]
        rewritten = ", ".join(variant_fn(t) for t in tags_raw if t)
        return f"tags: {rewritten}"

    return re.sub(r"^tags:.*$", _inline_sub, fm, flags=re.MULTILINE)


# ---------------------------------------------------------------------------
# 5. Inconsistent tag conventions
# ---------------------------------------------------------------------------


def apply_inconsistent_tags(
    notes: list[tuple[str, str]],
    *,
    seed: int,
    fraction: float,
) -> list[tuple[str, str]]:
    """Rewrite the tags: frontmatter field using an alternate convention."""
    rng = random.Random(seed)
    targets = _select_indices(rng, len(notes), fraction)
    result: list[tuple[str, str]] = []
    for i, (fname, content) in enumerate(notes):
        if i not in targets:
            result.append((fname, content))
            continue
        fm, body = _split_frontmatter(content)
        if not fm:
            result.append((fname, content))
            continue

        variant_fn: Callable[[str], str] = rng.choice(_TAG_VARIANTS[1:])
        new_fm = _rewrite_tags_line(fm, variant_fn)
        result.append((fname, new_fm + body))
    return result


# ---------------------------------------------------------------------------
# 6. Truncated content
# ---------------------------------------------------------------------------


def apply_truncated_content(
    notes: list[tuple[str, str]],
    *,
    seed: int,
    fraction: float,
) -> list[tuple[str, str]]:
    """Truncate note body mid-sentence in a fraction of notes."""
    rng = random.Random(seed)
    targets = _select_indices(rng, len(notes), fraction)
    result: list[tuple[str, str]] = []
    for i, (fname, content) in enumerate(notes):
        if i not in targets:
            result.append((fname, content))
            continue
        fm, body = _split_frontmatter(content)
        if not fm or len(body) < 20:
            result.append((fname, content))
            continue
        cut = rng.randint(len(body) // 4, max(len(body) // 4, 3 * len(body) // 4))
        truncated = body[:cut]
        result.append((fname, fm + truncated))
    return result
