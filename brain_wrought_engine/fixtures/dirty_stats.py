"""Dirty-vault statistics reporter.

Scans a vault directory and counts degradation indicators introduced by
generate_dirty_brain. Results are returned as a frozen Pydantic model so
callers can compare counts across dirty_level values.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

_FM_OPEN_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

_NONEXISTENT_TARGETS = {
    "Zylotron_X9",
    "Project_Phantom",
    "Alice_Holloway",
    "Research_Nexus",
    "Meeting_Echo",
}

_STUB_MARKER = "TODO: flesh out"
_STALE_UPDATED = "2020-01-01T00:00:00Z"


class DirtyStatsReport(BaseModel):
    total_notes: int
    stub_notes: int
    notes_missing_frontmatter_fields: int
    notes_with_stale_dates: int
    broken_backlinks: int
    notes_with_inconsistent_tags: int
    truncated_notes: int

    model_config = {"frozen": True}


def _split_frontmatter(content: str) -> tuple[str, str]:
    m = _FM_OPEN_RE.match(content)
    if m:
        return m.group(0), content[m.end() :]
    return "", content


def _is_stub(body: str) -> bool:
    stripped = body.strip()
    return stripped == _STUB_MARKER or stripped.startswith(_STUB_MARKER)


def _has_stale_date(fm: str) -> bool:
    return _STALE_UPDATED in fm


def _is_missing_optional_field(fm: str) -> bool:
    """Return True if any of the tracked optional fields is absent from frontmatter."""
    optional = ["tags", "updated", "entities", "state"]
    fm_inner = fm.removeprefix("---\n").removesuffix("\n---\n")
    present_keys = {line.split(":")[0].strip() for line in fm_inner.splitlines() if ":" in line}
    return any(f not in present_keys for f in optional)


def _has_inconsistent_tags(fm: str) -> bool:
    """Return True when the tags: line uses a non-bare-word convention."""
    m = re.search(r"^tags:(.*)$", fm, flags=re.MULTILINE)
    if not m:
        return False
    tag_text = m.group(1)
    return bool(re.search(r"#|\btype/", tag_text))


def _count_broken_backlinks(body: str) -> int:
    return sum(1 for m in _WIKILINK_RE.finditer(body) if m.group(1) in _NONEXISTENT_TARGETS)


def _is_truncated(body: str) -> bool:
    """Detect truncation: body ends without a trailing newline or ends mid-paragraph."""
    stripped = body.rstrip("\n")
    if not stripped:
        return False
    last_char = stripped[-1]
    return last_char not in {".", "!", "?", "-", "_", "*", "`", "#"}


def report_dirty_stats(vault_dir: Path) -> DirtyStatsReport:
    """Count each degradation type present in the vault.

    Parameters
    ----------
    vault_dir:
        Path to the vault directory containing .md files.

    Returns
    -------
    DirtyStatsReport
        Counts of each degradation category found in the vault.
    """
    notes = list(vault_dir.glob("*.md"))
    total = len(notes)

    stubs = 0
    missing_fm = 0
    stale = 0
    broken_links = 0
    inconsistent_tags = 0
    truncated = 0

    for note in notes:
        content = note.read_text(encoding="utf-8")
        fm, body = _split_frontmatter(content)

        if _is_stub(body):
            stubs += 1
        if fm and _has_stale_date(fm):
            stale += 1
        if fm and _is_missing_optional_field(fm):
            missing_fm += 1
        if fm and _has_inconsistent_tags(fm):
            inconsistent_tags += 1
        broken_links += _count_broken_backlinks(body)
        if not _is_stub(body) and body.strip() and _is_truncated(body):
            truncated += 1

    return DirtyStatsReport(
        total_notes=total,
        stub_notes=stubs,
        notes_missing_frontmatter_fields=missing_fm,
        notes_with_stale_dates=stale,
        broken_backlinks=broken_links,
        notes_with_inconsistent_tags=inconsistent_tags,
        truncated_notes=truncated,
    )
