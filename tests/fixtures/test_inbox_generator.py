"""Tests for brain_wrought_engine.fixtures.inbox_generator."""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from brain_wrought_engine.fixtures.inbox_generator import (
    InboxManifest,
    generate_inbox,
)


def _tree_hash(root: Path) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for every file under root (excl. _manifest.json)."""
    result: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "_manifest.json":
            rel = str(p.relative_to(root))
            result[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_determinism(tmp_path: Path) -> None:
    """Same seed → identical file tree (recursive hash match)."""
    d1 = tmp_path / "run1"
    d2 = tmp_path / "run2"
    generate_inbox(out_dir=d1, seed=42, inbox_size="small", use_llm=False)
    generate_inbox(out_dir=d2, seed=42, inbox_size="small", use_llm=False)
    assert _tree_hash(d1) == _tree_hash(d2)


def test_different_seeds_differ(tmp_path: Path) -> None:
    """Different seeds produce different content."""
    d1 = tmp_path / "s1"
    d2 = tmp_path / "s2"
    generate_inbox(out_dir=d1, seed=1, inbox_size="small", use_llm=False)
    generate_inbox(out_dir=d2, seed=2, inbox_size="small", use_llm=False)
    assert _tree_hash(d1) != _tree_hash(d2)


# ---------------------------------------------------------------------------
# Size invariants
# ---------------------------------------------------------------------------


def test_size_small(tmp_path: Path) -> None:
    m = generate_inbox(out_dir=tmp_path / "s", seed=0, inbox_size="small", use_llm=False)
    assert len(m.items) == 20


def test_size_medium(tmp_path: Path) -> None:
    m = generate_inbox(out_dir=tmp_path / "m", seed=0, inbox_size="medium", use_llm=False)
    assert len(m.items) == 50


def test_size_large(tmp_path: Path) -> None:
    m = generate_inbox(out_dir=tmp_path / "l", seed=0, inbox_size="large", use_llm=False)
    assert len(m.items) == 100


# ---------------------------------------------------------------------------
# Subdirectory structure
# ---------------------------------------------------------------------------


def test_subdirectory_structure(tmp_path: Path) -> None:
    """emails/, calendar/, slack/, pdfs/, attachments/ are all created."""
    d = tmp_path / "inbox"
    generate_inbox(out_dir=d, seed=7, inbox_size="small", use_llm=False)
    for subdir in ("emails", "calendar", "slack", "pdfs", "attachments"):
        assert (d / subdir).is_dir(), f"Missing subdirectory: {subdir}"


# ---------------------------------------------------------------------------
# Manifest integrity
# ---------------------------------------------------------------------------


def test_manifest_written(tmp_path: Path) -> None:
    """_manifest.json exists and parses as InboxManifest."""
    d = tmp_path / "inbox"
    generate_inbox(out_dir=d, seed=3, inbox_size="small", use_llm=False)
    manifest_path = d / "_manifest.json"
    assert manifest_path.exists()
    manifest = InboxManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest.items) == 20


def test_manifest_integrity(tmp_path: Path) -> None:
    """Every referenced_entity in manifest appears literally in the item's file content."""
    d = tmp_path / "inbox"
    manifest = generate_inbox(out_dir=d, seed=11, inbox_size="small", use_llm=False)
    for item in manifest.items:
        content = (d / item.file_path).read_text(encoding="utf-8")
        for entity in item.referenced_entities:
            assert entity in content, (
                f"Entity {entity!r} not found in {item.file_path}"
            )
        for project in item.referenced_projects:
            assert project in content, (
                f"Project {project!r} not found in {item.file_path}"
            )


# ---------------------------------------------------------------------------
# Cross-reference coverage
# ---------------------------------------------------------------------------


def test_no_broken_references(tmp_path: Path) -> None:
    """Every entity referenced in any item appears in at least 2 items."""
    d = tmp_path / "inbox"
    manifest = generate_inbox(out_dir=d, seed=99, inbox_size="medium", use_llm=False)
    entity_count: dict[str, int] = {}
    for item in manifest.items:
        for entity in item.referenced_entities + item.referenced_projects:
            entity_count[entity] = entity_count.get(entity, 0) + 1
    for entity, count in entity_count.items():
        assert count >= 2, (
            f"Entity {entity!r} appears in only {count} item(s); expected >= 2"
        )


# ---------------------------------------------------------------------------
# Temporal plausibility
# ---------------------------------------------------------------------------


def test_temporal_plausibility(tmp_path: Path) -> None:
    """All source_timestamps fall within a 90-day window ending at seeded 'now'."""
    seed = 17
    d = tmp_path / "inbox"
    manifest = generate_inbox(out_dir=d, seed=seed, inbox_size="small", use_llm=False)

    # Reconstruct the window used for seed=17
    base_date = datetime.date(2026, 1, 1) + datetime.timedelta(days=seed % 60)
    now = datetime.datetime(base_date.year, base_date.month, base_date.day, 12, 0, 0)
    window_start = now - datetime.timedelta(days=90)

    for item in manifest.items:
        ts_str = item.source_timestamp.rstrip("Z")
        ts = datetime.datetime.fromisoformat(ts_str)
        assert window_start <= ts <= now, (
            f"Timestamp {ts} for {item.item_id} outside [{window_start}, {now}]"
        )
