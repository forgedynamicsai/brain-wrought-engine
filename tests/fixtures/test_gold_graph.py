"""Tests for brain_wrought_engine.fixtures.gold_graph.

Six tests:
  1. test_determinism           — same seed → bit-identical gold_graph.json
  2. test_all_edges_resolve     — every edge source/target exists in nodes
  3. test_frontmatter_completeness — every node has all required frontmatter keys
  4. test_materialized_vault_valid — every [[wikilink]] resolves to an existing .md
  5. test_no_orphan_nodes       — every node is source OR target of at least one edge
  6. test_json_roundtrip        — gold_graph.json parses back as a valid GoldGraph
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from brain_wrought_engine.fixtures.gold_graph import (
    CrossReference,
    GoldGraph,
    PersonEntity,
    ProjectEntity,
    generate_gold_graph,
)

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_graph_inputs() -> (
    tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]]
):
    """A small but non-trivial graph with two people, one project, and two cross-refs."""
    people = [
        PersonEntity(name="Alice Chen", role="engineer", email="alice.chen@example.com"),
        PersonEntity(name="Bob Park", role="manager", email="bob.park@example.com"),
    ]
    projects = [
        ProjectEntity(name="Project Helios", status="active", owner="Alice Chen"),
    ]
    cross_references = [
        CrossReference(
            source_item_id="email_0001",
            mentioned_people=["Alice Chen", "Bob Park"],
            mentioned_projects=["Project Helios"],
            event_date=None,
            attendees=None,
        ),
        CrossReference(
            source_item_id="calendar_0001",
            mentioned_people=["Alice Chen", "Bob Park"],
            mentioned_projects=["Project Helios"],
            event_date="2026-01-15",
            attendees=["Alice Chen", "Bob Park"],
        ),
    ]
    return people, projects, cross_references


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


def test_determinism(
    tmp_path: Path,
    small_graph_inputs: tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]],
) -> None:
    """Same seed → bit-identical gold_graph.json."""
    people, projects, cross_refs = small_graph_inputs
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    g1 = generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
        out_dir=out1,
    )
    g2 = generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
        out_dir=out2,
    )
    assert g1.nodes == g2.nodes
    assert g1.edges == g2.edges
    assert g1.seed == g2.seed
    # JSON files will differ only in generated_at (datetime.now()) — compare
    # everything except that field.
    j1 = json.loads((out1 / "gold_graph.json").read_text())
    j2 = json.loads((out2 / "gold_graph.json").read_text())
    j1.pop("generated_at")
    j2.pop("generated_at")
    assert j1 == j2


# ---------------------------------------------------------------------------
# 2. All edges resolve
# ---------------------------------------------------------------------------


def test_all_edges_resolve(
    small_graph_inputs: tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]],
) -> None:
    """Every edge source and target exists in nodes."""
    people, projects, cross_refs = small_graph_inputs
    graph = generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
    )
    node_ids = set(graph.nodes.keys())
    for edge in graph.edges:
        assert edge.source_id in node_ids, (
            f"Edge source {edge.source_id!r} not found in nodes"
        )
        assert edge.target_id in node_ids, (
            f"Edge target {edge.target_id!r} not found in nodes"
        )


# ---------------------------------------------------------------------------
# 3. Frontmatter completeness
# ---------------------------------------------------------------------------


def test_frontmatter_completeness(
    small_graph_inputs: tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]],
) -> None:
    """Every node has all required frontmatter keys for its note_type."""
    required: dict[str, set[str]] = {
        "person": {"type", "created", "updated", "tags", "role"},
        "project": {"type", "created", "updated", "status", "owner"},
        "meeting": {"type", "date", "attendees", "project"},
        "topic": {"type", "tags"},
    }
    people, projects, cross_refs = small_graph_inputs
    graph = generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
    )
    for note_id, node in graph.nodes.items():
        required_keys = required[node.note_type]
        actual_keys = set(node.frontmatter.keys())
        missing = required_keys - actual_keys
        assert not missing, (
            f"Node {note_id!r} (type={node.note_type!r}) missing frontmatter keys: {missing}"
        )


# ---------------------------------------------------------------------------
# 4. Materialized vault — all wikilinks resolve
# ---------------------------------------------------------------------------


def test_materialized_vault_valid(
    tmp_path: Path,
    small_graph_inputs: tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]],
) -> None:
    """Every [[wikilink]] in the markdown vault resolves to an existing .md file."""
    people, projects, cross_refs = small_graph_inputs
    generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
        out_dir=tmp_path,
    )
    vault_dir = tmp_path / "gold_brain"
    md_files = list(vault_dir.glob("*.md"))
    assert md_files, "gold_brain/ directory is empty"

    existing_stems = {f.stem for f in md_files}
    broken: list[str] = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        for target in _WIKILINK_RE.findall(content):
            if target not in existing_stems:
                broken.append(f"{md_file.name}: [[{target}]]")

    assert not broken, "Broken wikilinks found:\n" + "\n".join(broken)


# ---------------------------------------------------------------------------
# 5. No orphan nodes
# ---------------------------------------------------------------------------


def test_no_orphan_nodes(
    small_graph_inputs: tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]],
) -> None:
    """Every node appears as source OR target of at least one edge."""
    people, projects, cross_refs = small_graph_inputs
    graph = generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
    )
    connected: set[str] = set()
    for edge in graph.edges:
        connected.add(edge.source_id)
        connected.add(edge.target_id)

    orphans = set(graph.nodes.keys()) - connected
    assert not orphans, f"Orphan nodes (no edges): {orphans}"


# ---------------------------------------------------------------------------
# 6. JSON roundtrip
# ---------------------------------------------------------------------------


def test_json_roundtrip(
    tmp_path: Path,
    small_graph_inputs: tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]],
) -> None:
    """gold_graph.json can be loaded back and parsed as GoldGraph."""
    people, projects, cross_refs = small_graph_inputs
    original = generate_gold_graph(
        seed=42,
        people=people,
        projects=projects,
        cross_references=cross_refs,
        out_dir=tmp_path,
    )
    json_path = tmp_path / "gold_graph.json"
    raw = json_path.read_text(encoding="utf-8")
    restored = GoldGraph.model_validate_json(raw)

    assert restored.seed == original.seed
    assert restored.nodes == original.nodes
    assert restored.edges == original.edges
