"""Brain vault validator.

Checks that every note in a vault directory:
- Has valid YAML frontmatter with the required keys.
- Does not have a duplicate filename (enforced by the filesystem, but
  we verify the expected schema keys are present).
- Contains no broken wikilinks — every ``[[Target]]`` resolves to an
  existing ``.md`` file in the vault.

Public API
----------
validate_brain(brain_dir: Path) -> list[str]
    Returns a (possibly empty) list of human-readable error strings.
    An empty list means the vault is valid.
"""

from __future__ import annotations

import re
from pathlib import Path

# Required frontmatter keys
_REQUIRED_KEYS = {"type", "created", "updated", "tags", "entities", "state"}

# Regex to find YAML frontmatter block
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# Regex to find all wikilinks in note body
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Minimal YAML key parser — handles simple ``key: value`` and ``key:\n  - item`` lists
_KEY_RE = re.compile(r"^([a-zA-Z_]+)\s*:", re.MULTILINE)


def _parse_frontmatter_keys(fm_block: str) -> set[str]:
    """Return the set of top-level key names found in the YAML block."""
    return set(_KEY_RE.findall(fm_block))


def _extract_frontmatter(content: str) -> tuple[str | None, str]:
    """Return (frontmatter_block, body).  frontmatter_block is None if absent."""
    m = _FM_RE.match(content)
    if m is None:
        return None, content
    return m.group(1), content[m.end():]


def validate_brain(brain_dir: Path) -> list[str]:
    """Validate every ``.md`` note in *brain_dir*.

    Parameters
    ----------
    brain_dir:
        Path to the vault directory (must exist).

    Returns
    -------
    list[str]
        Error messages.  Empty list means all notes pass validation.
    """
    brain_dir = Path(brain_dir)
    if not brain_dir.is_dir():
        return [f"vault directory does not exist: {brain_dir}"]

    notes = list(brain_dir.glob("*.md"))
    if not notes:
        return [f"vault is empty — no .md files found in {brain_dir}"]

    # Build the set of valid targets (stem → filename mapping)
    # Wikilinks use the entity name with spaces; filenames use underscores.
    # We match by normalising both sides.
    def _normalise(s: str) -> str:
        return s.replace(" ", "_").replace("-", "_").lower()

    valid_stems = {_normalise(n.stem) for n in notes}

    errors: list[str] = []
    seen_names: set[str] = set()

    for note_path in sorted(notes):
        note_name = note_path.name

        # Duplicate check
        if note_name in seen_names:
            errors.append(f"{note_name}: duplicate filename")
        seen_names.add(note_name)

        content = note_path.read_text(encoding="utf-8")
        fm_block, body = _extract_frontmatter(content)

        # Missing frontmatter
        if fm_block is None:
            errors.append(f"{note_name}: missing YAML frontmatter")
            continue

        # Missing required keys
        present_keys = _parse_frontmatter_keys(fm_block)
        missing = _REQUIRED_KEYS - present_keys
        if missing:
            errors.append(
                f"{note_name}: frontmatter missing required keys: "
                + ", ".join(sorted(missing))
            )

        # Broken wikilinks
        for link_target in _WIKILINK_RE.findall(body):
            if _normalise(link_target) not in valid_stems:
                errors.append(f"{note_name}: broken wikilink [[{link_target}]]")

    return errors
