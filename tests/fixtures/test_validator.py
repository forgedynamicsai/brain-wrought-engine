"""Tests for brain_wrought_engine.fixtures.validator.

Three tests:
  1. valid_brain_passes          — a freshly generated vault reports no errors.
  2. missing_frontmatter_fails   — a note without frontmatter is flagged.
  3. broken_link_fails           — a note with an unresolvable wikilink is flagged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brain_wrought_engine.fixtures.generator import generate_brain
from brain_wrought_engine.fixtures.validator import validate_brain


@pytest.fixture()
def valid_vault(tmp_path: Path) -> Path:
    """A small valid vault used by several tests."""
    return generate_brain(
        seed=13,
        fixture_index=0,
        out_dir=tmp_path,
        note_count=8,
        use_llm=False,
    )


# ---------------------------------------------------------------------------
# 1. Valid brain passes
# ---------------------------------------------------------------------------


def test_valid_brain_passes(valid_vault: Path) -> None:
    """A freshly generated vault must validate with zero errors."""
    errors = validate_brain(valid_vault)
    assert errors == [], "Unexpected errors in valid vault:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# 2. Missing frontmatter fails
# ---------------------------------------------------------------------------


def test_missing_frontmatter_fails(valid_vault: Path) -> None:
    """A note stripped of its frontmatter must produce a validation error."""
    # Pick any note and overwrite with body-only content
    note = next(valid_vault.glob("*.md"))
    original = note.read_text(encoding="utf-8")
    # Remove the frontmatter block (everything up to and including the closing ---)
    lines = original.splitlines(keepends=True)
    # Find second "---" line and drop everything before it (inclusive)
    idx = next(
        (i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"),
        None,
    )
    if idx is not None:
        body_only = "".join(lines[idx + 1 :])
    else:
        body_only = original  # fallback: content was already odd

    note.write_text(body_only, encoding="utf-8")

    errors = validate_brain(valid_vault)
    assert any(
        note.name in err and "frontmatter" in err for err in errors
    ), f"Expected missing-frontmatter error for {note.name}; got: {errors}"


# ---------------------------------------------------------------------------
# 3. Broken wikilink fails
# ---------------------------------------------------------------------------


def test_broken_link_fails(valid_vault: Path) -> None:
    """A note containing a wikilink to a non-existent target must be flagged."""
    note = next(valid_vault.glob("*.md"))
    content = note.read_text(encoding="utf-8")
    # Append a wikilink to a note that definitely does not exist
    poisoned = content + "\n\n[[Definitely_Does_Not_Exist_XYZ]]\n"
    note.write_text(poisoned, encoding="utf-8")

    errors = validate_brain(valid_vault)
    assert any(
        "Definitely_Does_Not_Exist_XYZ" in err for err in errors
    ), f"Expected broken-link error; got: {errors}"
