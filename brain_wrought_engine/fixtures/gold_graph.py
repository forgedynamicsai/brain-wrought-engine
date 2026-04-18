"""Gold entity graph generator for the ingestion axis.

Edge types and resolution rules are deliberately narrow. A submission's
backlink F1 is meaningful only if gold and submission both follow the
same rules. Ambiguity here corrupts every downstream scorer.

Edge resolution rules:
- "mentions": source note body text contains target entity name literally.
- "meeting_with": meeting notes only; attendees who have their own
  people/ note each get a "meeting_with" edge from the meeting node.
- "about_project": note frontmatter has a `project:` field whose slug
  matches an existing project note_id.
- "authored_by": meeting and project notes with an `author:` frontmatter
  field that resolves via slug to a people note.

Determinism class: FULLY_DETERMINISTIC — no LLM calls, no random
sampling beyond the seeded rng used for timestamps and ordering.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from brain_wrought_engine.text_utils import slug

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

NoteType = Literal["person", "project", "meeting", "topic"]
EdgeType = Literal["mentions", "meeting_with", "about_project", "authored_by"]

REQUIRED_FRONTMATTER_KEYS: dict[NoteType, frozenset[str]] = {
    "person":  frozenset({"type", "created", "updated", "tags", "role"}),
    "project": frozenset({"type", "created", "updated", "status", "owner"}),
    "meeting": frozenset({"type", "date", "attendees", "project"}),
    "topic":   frozenset({"type", "tags"}),
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class GoldNode(BaseModel):
    note_id: str
    title: str
    note_type: NoteType
    frontmatter: dict[str, str]
    expected_content_facets: list[str]  # key facts the note SHOULD contain
    source_inbox_items: list[str]  # item_ids from the inbox that produced this node

    model_config = {"frozen": True}


class GoldEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType

    model_config = {"frozen": True}


class GoldGraph(BaseModel):
    seed: int
    nodes: dict[str, GoldNode]  # key is note_id
    edges: tuple[GoldEdge, ...]  # sorted by (source_id, target_id, edge_type) for determinism

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


class PersonEntity(BaseModel):
    name: str  # "Alice Chen"
    role: str  # "engineer", "manager", etc.
    email: str  # derived: alice.chen@example.com


class ProjectEntity(BaseModel):
    name: str  # "Project Helios"
    status: str  # "active", "planning", "complete"
    owner: str  # person name


class CrossReference(BaseModel):
    source_item_id: str  # e.g. "email_0003"
    mentioned_people: list[str]
    mentioned_projects: list[str]
    event_date: str | None  # ISO 8601 if this is a meeting/calendar item
    attendees: list[str] | None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _seeded_iso_date(rng: random.Random, base: datetime) -> str:
    """Return a seeded ISO 8601 date string near base."""
    offset = rng.randint(0, 364)
    dt = base + timedelta(days=offset)
    return dt.strftime("%Y-%m-%d")


def _render_frontmatter(fm: dict[str, str]) -> str:
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _render_note(node: GoldNode, outbound_targets: list[str]) -> str:
    """Render a GoldNode to Obsidian-style Markdown."""
    fm_block = _render_frontmatter(node.frontmatter)
    body_paragraphs = "\n\n".join(node.expected_content_facets)
    wikilinks = " ".join(f"[[{t}]]" for t in outbound_targets)
    wikilink_section = f"\n\n{wikilinks}" if wikilinks else ""
    return f"{fm_block}\n\n# {node.title}\n\n{body_paragraphs}{wikilink_section}\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_gold_graph(
    *,
    seed: int,
    people: list[PersonEntity],
    projects: list[ProjectEntity],
    cross_references: list[CrossReference],
    out_dir: Path | None = None,
) -> GoldGraph:
    """Generate a fully deterministic gold entity graph from structured inputs.

    Parameters
    ----------
    seed:
        Master seed for the seeded RNG — controls timestamp generation and
        ordering.  No other randomness is used.
    people:
        Person entities to materialise as person-type nodes.
    projects:
        Project entities to materialise as project-type and companion topic nodes.
    cross_references:
        Cross-reference records linking inbox items to entities.  Records that
        carry ``attendees`` are treated as meeting/calendar items and generate
        meeting-type nodes.
    out_dir:
        Optional output directory.  When provided:
        - ``out_dir/gold_graph.json`` is written (pretty-printed JSON).
        - ``out_dir/gold_brain/`` is populated with one ``.md`` file per node.

    Returns
    -------
    GoldGraph
        Fully constructed, immutable gold graph.
    """
    rng = random.Random(seed)
    base_date = datetime(2026, 1, 1, tzinfo=UTC)

    nodes: dict[str, GoldNode] = {}

    # ------------------------------------------------------------------
    # 1. Build a lookup: person name → list of project names they appear in
    # ------------------------------------------------------------------
    person_projects: dict[str, list[str]] = {p.name: [] for p in people}
    for xref in cross_references:
        for person_name in xref.mentioned_people:
            if person_name in person_projects:
                for proj_name in xref.mentioned_projects:
                    if proj_name not in person_projects[person_name]:
                        person_projects[person_name].append(proj_name)

    # ------------------------------------------------------------------
    # 2. Person nodes
    # ------------------------------------------------------------------
    for person in people:
        note_id = slug(person.name)
        created = _seeded_iso_date(rng, base_date)
        updated = _seeded_iso_date(rng, base_date)
        fm: dict[str, str] = {
            "type": "person",
            "created": created,
            "updated": updated,
            "tags": "person",
            "role": person.role,
        }
        facets: list[str] = [
            f"{person.name} is a {person.role}.",
            f"Email: {person.email}",
        ]
        for proj_name in person_projects.get(person.name, []):
            facets.append(f"{person.name} is referenced in relation to {proj_name}.")

        # Collect source_inbox_items where this person is mentioned
        source_items = [
            xref.source_item_id
            for xref in cross_references
            if person.name in xref.mentioned_people
        ]

        nodes[note_id] = GoldNode(
            note_id=note_id,
            title=person.name,
            note_type="person",
            frontmatter=fm,
            expected_content_facets=facets,
            source_inbox_items=source_items,
        )

    # ------------------------------------------------------------------
    # 3. Project nodes  (+ author frontmatter = slug of owner)
    # ------------------------------------------------------------------
    for project in projects:
        note_id = slug(project.name)
        created = _seeded_iso_date(rng, base_date)
        updated = _seeded_iso_date(rng, base_date)
        owner_slug = slug(project.owner)
        fm = {
            "type": "project",
            "created": created,
            "updated": updated,
            "status": project.status,
            "owner": owner_slug,
            "author": owner_slug,
        }
        facets = [
            f"{project.name} has status: {project.status}.",
            f"Owner: {project.owner}",
        ]
        source_items = [
            xref.source_item_id
            for xref in cross_references
            if project.name in xref.mentioned_projects
        ]
        nodes[note_id] = GoldNode(
            note_id=note_id,
            title=project.name,
            note_type="project",
            frontmatter=fm,
            expected_content_facets=facets,
            source_inbox_items=source_items,
        )

    # ------------------------------------------------------------------
    # 4. Topic nodes  (companion to each project)
    # ------------------------------------------------------------------
    for project in projects:
        note_id = f"topic_{slug(project.name)}"
        proj_slug = slug(project.name)
        fm = {
            "type": "topic",
            "tags": "topic",
            "project": proj_slug,  # enables Rule 3 ("about_project") → non-orphan
        }
        facets = [
            f"Topic area for {project.name}.",
        ]
        nodes[note_id] = GoldNode(
            note_id=note_id,
            title=f"Topic: {project.name}",
            note_type="topic",
            frontmatter=fm,
            expected_content_facets=facets,
            source_inbox_items=[],
        )

    # ------------------------------------------------------------------
    # 5. Meeting nodes  (cross_references with attendees)
    # ------------------------------------------------------------------
    for xref in cross_references:
        if xref.attendees is None:
            continue
        note_id = f"meeting_{xref.source_item_id}"
        event_date = xref.event_date or _seeded_iso_date(rng, base_date)
        attendee_slugs = ", ".join(slug(a) for a in xref.attendees)
        proj_slug = slug(xref.mentioned_projects[0]) if xref.mentioned_projects else ""

        # Determine author: first attendee who is a known person node
        author_slug = ""
        for attendee in xref.attendees:
            candidate = slug(attendee)
            if candidate in nodes:
                author_slug = candidate
                break

        fm = {
            "type": "meeting",
            "date": event_date,
            "attendees": attendee_slugs,
            "project": proj_slug,
        }
        if author_slug:
            fm["author"] = author_slug

        facets = [
            f"Meeting held on {event_date}.",
            f"Attendees: {', '.join(xref.attendees)}",
        ]
        if xref.mentioned_projects:
            facets.append(f"Related project: {xref.mentioned_projects[0]}.")

        nodes[note_id] = GoldNode(
            note_id=note_id,
            title=f"Meeting {xref.source_item_id}",
            note_type="meeting",
            frontmatter=fm,
            expected_content_facets=facets,
            source_inbox_items=[xref.source_item_id],
        )

    # ------------------------------------------------------------------
    # 6. Edge construction — apply the four resolution rules
    # ------------------------------------------------------------------
    edges: set[GoldEdge] = set()

    person_node_ids = {nid for nid, n in nodes.items() if n.note_type == "person"}
    project_node_ids = {nid for nid, n in nodes.items() if n.note_type == "project"}

    # Build a reverse map: entity name → note_id for "mentions" resolution
    # We check facets for literal entity names
    name_to_node_id: dict[str, str] = {}
    for nid, node in nodes.items():
        name_to_node_id[node.title] = nid

    for source_id, source_node in nodes.items():
        # Rule 1: "mentions" — scan expected_content_facets for entity name literals
        all_facets_text = " ".join(source_node.expected_content_facets)
        for target_name, target_id in name_to_node_id.items():
            if target_id == source_id:
                continue
            if target_name in all_facets_text:
                edges.add(
                    GoldEdge(source_id=source_id, target_id=target_id, edge_type="mentions")
                )

        # Rule 2: "meeting_with" — meeting nodes → attendee people nodes
        if source_node.note_type == "meeting":
            raw_attendees = source_node.frontmatter.get("attendees", "")
            for attendee_slug in (s.strip() for s in raw_attendees.split(",") if s.strip()):
                if attendee_slug in person_node_ids:
                    edges.add(
                        GoldEdge(
                            source_id=source_id,
                            target_id=attendee_slug,
                            edge_type="meeting_with",
                        )
                    )

        # Rule 3: "about_project" — any node with frontmatter["project"] resolving to a project
        proj_ref = source_node.frontmatter.get("project", "")
        if proj_ref and proj_ref in project_node_ids:
            edges.add(
                GoldEdge(
                    source_id=source_id, target_id=proj_ref, edge_type="about_project"
                )
            )

        # Rule 4: "authored_by" — meeting/project nodes with frontmatter["author"]
        if source_node.note_type in ("meeting", "project"):
            author_ref = source_node.frontmatter.get("author", "")
            if author_ref and author_ref in person_node_ids:
                edges.add(
                    GoldEdge(
                        source_id=source_id,
                        target_id=author_ref,
                        edge_type="authored_by",
                    )
                )

    # Sort edges for determinism: (source_id, target_id, edge_type)
    sorted_edges = tuple(
        sorted(edges, key=lambda e: (e.source_id, e.target_id, e.edge_type))
    )

    graph = GoldGraph(
        seed=seed,
        nodes=nodes,
        edges=sorted_edges,
    )

    # ------------------------------------------------------------------
    # 7. Optional file output
    # ------------------------------------------------------------------
    if out_dir is not None:
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # gold_graph.json
        json_path = out_path / "gold_graph.json"
        json_path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")

        # gold_brain/ vault — one .md per node
        vault_dir = out_path / "gold_brain"
        vault_dir.mkdir(parents=True, exist_ok=True)

        # Build outbound edge map: source_id → list of target_ids
        outbound: dict[str, list[str]] = {nid: [] for nid in nodes}
        for edge in sorted_edges:
            outbound[edge.source_id].append(edge.target_id)

        for note_id, node in nodes.items():
            md_content = _render_note(node, outbound[note_id])
            (vault_dir / f"{note_id}.md").write_text(md_content, encoding="utf-8")

    return graph
