"""Tests for dirty-schema fixture generator (BW-014).

Tests:
  1. determinism        — same (seed, fixture_index, dirty_level) → identical vault
  2. clean_boundary     — dirty_level=0.0 produces the same vault as generate_brain
  3. dirty_boundary     — dirty_level=1.0 produces non-zero degradation stats
  4. intermediate_stats — dirty_level=0.5 produces stats between clean and max
  5. invalid_dirty_level — ValueError on out-of-range dirty_level
  6. note_count_preserved — dirty vault always has exactly note_count notes
  7. stats_report_clean  — report_dirty_stats on a clean vault returns zeros
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brain_wrought_engine.fixtures.dirty_stats import DirtyStatsReport, report_dirty_stats
from brain_wrought_engine.fixtures.generate_dirty import generate_dirty_brain
from brain_wrought_engine.fixtures.generator import generate_brain

_NOTE_COUNT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_vault(vault: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(vault.glob("*.md"))}


def _gen_dirty(tmp_path: Path, *, dirty_level: float, seed: int = 42, idx: int = 0) -> Path:
    return generate_dirty_brain(
        seed=seed,
        fixture_index=idx,
        out_dir=tmp_path,
        note_count=_NOTE_COUNT,
        use_llm=False,
        dirty_level=dirty_level,
    )


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


def test_determinism(tmp_path: Path) -> None:
    """Two calls with identical arguments must produce bit-identical vaults."""
    vault_a = _gen_dirty(tmp_path / "a", dirty_level=0.5)
    vault_b = _gen_dirty(tmp_path / "b", dirty_level=0.5)
    assert _read_vault(vault_a) == _read_vault(vault_b)


def test_determinism_different_levels(tmp_path: Path) -> None:
    """Different dirty_levels must produce different vaults."""
    vault_05 = _gen_dirty(tmp_path / "l05", dirty_level=0.5)
    vault_10 = _gen_dirty(tmp_path / "l10", dirty_level=1.0)
    assert _read_vault(vault_05) != _read_vault(vault_10)


# ---------------------------------------------------------------------------
# 2. Clean boundary
# ---------------------------------------------------------------------------


def test_clean_boundary(tmp_path: Path) -> None:
    """dirty_level=0.0 must produce the same files as generate_brain."""
    clean = generate_brain(
        seed=42,
        fixture_index=0,
        out_dir=tmp_path / "clean",
        note_count=_NOTE_COUNT,
        use_llm=False,
    )
    dirty_zero = _gen_dirty(tmp_path / "dirty0", dirty_level=0.0)

    files_clean = _read_vault(clean)
    files_dirty = _read_vault(dirty_zero)
    assert files_clean == files_dirty, "dirty_level=0.0 must be bit-identical to clean vault"


def test_clean_boundary_stats(tmp_path: Path) -> None:
    """report_dirty_stats on a dirty_level=0.0 vault returns all-zero degradation counts."""
    vault = _gen_dirty(tmp_path, dirty_level=0.0)
    stats = report_dirty_stats(vault)
    assert stats.stub_notes == 0
    assert stats.notes_with_stale_dates == 0
    assert stats.broken_backlinks == 0


# ---------------------------------------------------------------------------
# 3. Dirty boundary
# ---------------------------------------------------------------------------


def test_dirty_boundary_nonzero(tmp_path: Path) -> None:
    """dirty_level=1.0 must produce a vault with measurable degradation."""
    vault = _gen_dirty(tmp_path, dirty_level=1.0)
    stats = report_dirty_stats(vault)
    assert stats.total_notes == _NOTE_COUNT
    total_degraded = (
        stats.stub_notes
        + stats.notes_with_stale_dates
        + stats.broken_backlinks
        + stats.notes_with_inconsistent_tags
    )
    assert total_degraded > 0, f"Expected degradation at dirty_level=1.0, got {stats}"


def test_dirty_boundary_stubs(tmp_path: Path) -> None:
    """At dirty_level=1.0 there should be a significant number of stub notes."""
    vault = _gen_dirty(tmp_path, dirty_level=1.0)
    stats = report_dirty_stats(vault)
    assert stats.stub_notes > 0, "Expected stub notes at dirty_level=1.0"


def test_dirty_boundary_stale_dates(tmp_path: Path) -> None:
    """At dirty_level=1.0 there should be stale-date notes."""
    vault = _gen_dirty(tmp_path, dirty_level=1.0)
    stats = report_dirty_stats(vault)
    assert stats.notes_with_stale_dates > 0, "Expected stale dates at dirty_level=1.0"


# ---------------------------------------------------------------------------
# 4. Intermediate stats roughly monotone
# ---------------------------------------------------------------------------


def test_intermediate_stats_ordering(tmp_path: Path) -> None:
    """Degradation counts at dirty_level=0.5 must sit between 0 and 1.0 values."""
    vault_05 = _gen_dirty(tmp_path / "l05", dirty_level=0.5)
    vault_10 = _gen_dirty(tmp_path / "l10", dirty_level=1.0)

    stats_05 = report_dirty_stats(vault_05)
    stats_10 = report_dirty_stats(vault_10)

    assert stats_05.stub_notes <= stats_10.stub_notes
    assert stats_05.notes_with_stale_dates <= stats_10.notes_with_stale_dates


def test_intermediate_stats_nonzero(tmp_path: Path) -> None:
    """dirty_level=0.5 must produce at least some degradation."""
    vault = _gen_dirty(tmp_path, dirty_level=0.5)
    stats = report_dirty_stats(vault)
    total_degraded = (
        stats.stub_notes
        + stats.notes_with_stale_dates
        + stats.broken_backlinks
        + stats.notes_with_inconsistent_tags
    )
    assert total_degraded > 0, f"Expected some degradation at dirty_level=0.5, got {stats}"


# ---------------------------------------------------------------------------
# 5. Invalid dirty_level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", [-0.1, 1.001, 2.0, -1.0])
def test_invalid_dirty_level(tmp_path: Path, level: float) -> None:
    with pytest.raises(ValueError, match="dirty_level"):
        generate_dirty_brain(
            seed=1,
            fixture_index=0,
            out_dir=tmp_path,
            note_count=5,
            use_llm=False,
            dirty_level=level,
        )


# ---------------------------------------------------------------------------
# 6. Note count preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [5, 10, 20])
def test_note_count_preserved(tmp_path: Path, n: int) -> None:
    vault = generate_dirty_brain(
        seed=7,
        fixture_index=n,
        out_dir=tmp_path / str(n),
        note_count=n,
        use_llm=False,
        dirty_level=0.5,
    )
    md_files = list(vault.glob("*.md"))
    assert len(md_files) == n, f"Expected {n} notes, found {len(md_files)}"


# ---------------------------------------------------------------------------
# 7. Stats report on a clean generate_brain vault
# ---------------------------------------------------------------------------


def test_stats_report_clean_vault(tmp_path: Path) -> None:
    """report_dirty_stats on a pristine generate_brain vault returns zeros for synthetic markers."""
    clean = generate_brain(
        seed=99,
        fixture_index=1,
        out_dir=tmp_path,
        note_count=_NOTE_COUNT,
        use_llm=False,
    )
    stats = report_dirty_stats(clean)
    assert stats.stub_notes == 0
    assert stats.notes_with_stale_dates == 0
    assert stats.broken_backlinks == 0
    assert stats.total_notes == _NOTE_COUNT


# ---------------------------------------------------------------------------
# 8. DirtyStatsReport is a frozen Pydantic model
# ---------------------------------------------------------------------------


def test_stats_report_is_frozen() -> None:
    """DirtyStatsReport must declare frozen=True in its model_config."""
    assert DirtyStatsReport.model_config.get("frozen") is True


def test_stats_report_fields() -> None:
    """DirtyStatsReport must expose all seven expected fields."""
    report = DirtyStatsReport(
        total_notes=10,
        stub_notes=2,
        notes_missing_frontmatter_fields=3,
        notes_with_stale_dates=4,
        broken_backlinks=1,
        notes_with_inconsistent_tags=2,
        truncated_notes=1,
    )
    assert report.total_notes == 10
    assert report.stub_notes == 2
    assert report.notes_missing_frontmatter_fields == 3
    assert report.notes_with_stale_dates == 4
    assert report.broken_backlinks == 1
    assert report.notes_with_inconsistent_tags == 2
    assert report.truncated_notes == 1
