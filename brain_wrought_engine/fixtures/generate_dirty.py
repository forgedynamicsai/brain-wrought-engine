"""Dirty-schema brain vault generator.

Determinism class: SEEDED-STOCHASTIC — same (seed, fixture_index, dirty_level)
produces an identical dirty vault regardless of when or where it is run.

Public API
----------
generate_dirty_brain(*, seed, fixture_index, out_dir, note_count, use_llm, dirty_level) -> Path

CLI
---
python -m brain_wrought_engine.fixtures.generate_dirty \\
    --count 1 --seed 42 --dirty-level 0.5 --out /tmp/test_dirty/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from brain_wrought_engine.fixtures.degradations import (
    apply_broken_backlinks,
    apply_inconsistent_tags,
    apply_missing_frontmatter_fields,
    apply_stale_dates,
    apply_stub_notes,
    apply_truncated_content,
)
from brain_wrought_engine.fixtures.generator import generate_brain

# Degradation rates: fraction = dirty_level * rate
_STUB_RATE = 0.30
_MISSING_FM_RATE = 0.40
_STALE_DATE_RATE = 0.50
_BROKEN_LINK_RATE = 0.20
_INCONSISTENT_TAGS_RATE = 0.30
_TRUNCATED_RATE = 0.15

# Per-degradation seed offsets to ensure independent RNG streams.
_SEED_STUB = 1
_SEED_MISSING_FM = 2
_SEED_STALE = 3
_SEED_BROKEN = 4
_SEED_TAGS = 5
_SEED_TRUNC = 6


def generate_dirty_brain(
    *,
    seed: int,
    fixture_index: int,
    out_dir: Path,
    note_count: int = 100,
    use_llm: bool = True,
    dirty_level: float,
) -> Path:
    """Generate a dirty vault by calling generate_brain then applying degradations.

    Parameters
    ----------
    seed:
        Master randomness seed. Combined with fixture_index for the clean vault,
        and with per-degradation offsets for each transformation.
    fixture_index:
        Index of this fixture within a batch.
    out_dir:
        Parent directory. The vault is written to
        ``out_dir/dirty_brain_{seed}_{fixture_index}_{dirty_level}/``.
    note_count:
        Number of Markdown notes (minimum 1).
    use_llm:
        Passed through to generate_brain.
    dirty_level:
        Float in [0.0, 1.0]. 0.0 produces an exactly-clean vault;
        1.0 applies maximum degradation.

    Returns
    -------
    Path
        Absolute path to the generated dirty vault directory.
    """
    if not (0.0 <= dirty_level <= 1.0):
        raise ValueError(f"dirty_level must be in [0.0, 1.0], got {dirty_level!r}")
    if note_count < 1:
        raise ValueError(f"note_count must be >= 1, got {note_count}")

    clean_vault = generate_brain(
        seed=seed,
        fixture_index=fixture_index,
        out_dir=Path(out_dir) / "_clean_tmp",
        note_count=note_count,
        use_llm=use_llm,
    )

    notes: list[tuple[str, str]] = [
        (p.name, p.read_text(encoding="utf-8")) for p in sorted(clean_vault.glob("*.md"))
    ]

    if dirty_level > 0.0:
        base_seed = seed + fixture_index
        notes = apply_stub_notes(
            notes, seed=base_seed + _SEED_STUB, fraction=dirty_level * _STUB_RATE
        )
        notes = apply_missing_frontmatter_fields(
            notes, seed=base_seed + _SEED_MISSING_FM, fraction=dirty_level * _MISSING_FM_RATE
        )
        notes = apply_stale_dates(
            notes, seed=base_seed + _SEED_STALE, fraction=dirty_level * _STALE_DATE_RATE
        )
        notes = apply_broken_backlinks(
            notes, seed=base_seed + _SEED_BROKEN, fraction=dirty_level * _BROKEN_LINK_RATE
        )
        notes = apply_inconsistent_tags(
            notes, seed=base_seed + _SEED_TAGS, fraction=dirty_level * _INCONSISTENT_TAGS_RATE
        )
        notes = apply_truncated_content(
            notes, seed=base_seed + _SEED_TRUNC, fraction=dirty_level * _TRUNCATED_RATE
        )

    level_tag = f"{dirty_level:.4f}".rstrip("0").rstrip(".")
    dirty_vault = Path(out_dir) / f"dirty_brain_{seed}_{fixture_index}_{level_tag}"
    dirty_vault.mkdir(parents=True, exist_ok=True)

    for fname, content in notes:
        (dirty_vault / fname).write_text(content, encoding="utf-8")

    for tmp_file in clean_vault.glob("*.md"):
        tmp_file.unlink()
    clean_vault.rmdir()
    clean_tmp = Path(out_dir) / "_clean_tmp"
    try:
        clean_tmp.rmdir()
    except OSError:
        pass

    return dirty_vault.resolve()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m brain_wrought_engine.fixtures.generate_dirty",
        description="Generate a dirty-schema brain vault fixture.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of vaults to generate (default: 1)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Master random seed (default: 0)",
    )
    parser.add_argument(
        "--dirty-level",
        type=float,
        default=0.5,
        dest="dirty_level",
        help="Degradation level in [0.0, 1.0] (default: 0.5)",
    )
    parser.add_argument(
        "--out",
        required=True,
        metavar="DIR",
        help="Parent directory for generated vaults",
    )
    parser.add_argument(
        "--notes",
        type=int,
        default=100,
        metavar="N",
        help="Notes per vault (default: 100)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM body generation; use deterministic templates",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    out = Path(args.out)
    for i in range(args.count):
        vault = generate_dirty_brain(
            seed=args.seed,
            fixture_index=i,
            out_dir=out,
            note_count=args.notes,
            use_llm=not args.no_llm,
            dirty_level=args.dirty_level,
        )
        print(f"[{i + 1}/{args.count}] generated dirty vault: {vault}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
