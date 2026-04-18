"""Tests for brain_wrought_engine.fixtures.generator.

Four tests:
  1. determinism      — same (seed, fixture_index) produces identical vaults.
  2. note_count       — generated vault contains exactly the requested notes.
  3. frontmatter_present — every note has a YAML frontmatter block.
  4. no_broken_links  — no wikilink in any note targets a missing file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from brain_wrought_engine.fixtures.generator import generate_brain

_FM_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _normalise(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").lower()


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """A small vault (10 notes, no LLM) used by several tests."""
    return generate_brain(
        seed=42,
        fixture_index=0,
        out_dir=tmp_path,
        note_count=10,
        use_llm=False,
    )


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


def test_determinism(tmp_path: Path) -> None:
    """Two calls with the same (seed, fixture_index) must produce identical content."""
    kwargs = dict(seed=99, fixture_index=3, note_count=10, use_llm=False)
    vault_a = generate_brain(out_dir=tmp_path / "a", **kwargs)  # type: ignore[arg-type]
    vault_b = generate_brain(out_dir=tmp_path / "b", **kwargs)  # type: ignore[arg-type]

    files_a = {p.name: p.read_text() for p in vault_a.glob("*.md")}
    files_b = {p.name: p.read_text() for p in vault_b.glob("*.md")}

    assert files_a == files_b, "Vaults from identical seeds differ"


# ---------------------------------------------------------------------------
# 2. Note count
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 5, 10, 85])
def test_note_count(tmp_path: Path, n: int) -> None:
    """Vault must contain exactly *n* Markdown files."""
    vault = generate_brain(
        seed=7,
        fixture_index=n,
        out_dir=tmp_path / str(n),
        note_count=n,
        use_llm=False,
    )
    md_files = list(vault.glob("*.md"))
    assert len(md_files) == n, f"Expected {n} notes, found {len(md_files)}"


# ---------------------------------------------------------------------------
# 3. Frontmatter present
# ---------------------------------------------------------------------------


def test_frontmatter_present(vault: Path) -> None:
    """Every note must open with a YAML frontmatter block."""
    missing: list[str] = []
    for note in vault.glob("*.md"):
        content = note.read_text(encoding="utf-8")
        if not _FM_RE.match(content):
            missing.append(note.name)
    assert not missing, f"Notes missing frontmatter: {missing}"


# ---------------------------------------------------------------------------
# 4. No broken wikilinks
# ---------------------------------------------------------------------------


def test_no_broken_links(vault: Path) -> None:
    """Every [[Target]] wikilink must resolve to an existing .md file."""
    notes = list(vault.glob("*.md"))
    valid_stems = {_normalise(n.stem) for n in notes}

    broken: list[str] = []
    for note in notes:
        content = note.read_text(encoding="utf-8")
        # Strip frontmatter before scanning
        body = _FM_RE.sub("", content)
        for target in _WIKILINK_RE.findall(body):
            if _normalise(target) not in valid_stems:
                broken.append(f"{note.name}: [[{target}]]")

    assert not broken, f"Broken wikilinks found:\n" + "\n".join(broken)
