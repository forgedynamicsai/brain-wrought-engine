"""Clean-schema brain vault generator.

Determinism class: SEEDED-STOCHASTIC — same (seed, fixture_index) pair
produces an identical vault regardless of when or where it is run.

Public API
----------
generate_brain(*, seed, fixture_index, out_dir, note_count, use_llm) -> Path
"""

from __future__ import annotations

import random
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain_wrought_engine.fixtures.entity_pool import COMPANIES, PEOPLE, PROJECTS
from brain_wrought_engine.text_utils import slug as _slug

# ---------------------------------------------------------------------------
# Note-type catalogue
# ---------------------------------------------------------------------------

_NOTE_TYPES = ["person", "company", "project", "meeting", "research"]

_BODY_TEMPLATES: dict[str, str] = {
    "person": textwrap.dedent(
        """\
        ## Background
        {name} works as a {role} and has been involved with several initiatives.

        ## Connections
        {backlinks}

        ## Notes
        Placeholder notes about {name}.
        """
    ),
    "company": textwrap.dedent(
        """\
        ## Overview
        {name} is a technology firm with a strong engineering culture.

        ## Key People
        {backlinks}

        ## Notes
        Placeholder notes about {name}.
        """
    ),
    "project": textwrap.dedent(
        """\
        ## Summary
        {name} is an internal initiative currently in progress.

        ## Team
        {backlinks}

        ## Notes
        Placeholder notes about {name}.
        """
    ),
    "meeting": textwrap.dedent(
        """\
        ## Attendees
        {backlinks}

        ## Agenda
        - Status update
        - Blockers review
        - Next steps

        ## Notes
        Placeholder meeting notes.
        """
    ),
    "research": textwrap.dedent(
        """\
        ## Topic
        {name}

        ## Related
        {backlinks}

        ## Notes
        Placeholder research notes.
        """
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")



def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    lines = "\n".join(f"  - {item}" for item in items)
    return f"\n{lines}"


def _frontmatter(
    *,
    note_type: str,
    created: str,
    updated: str,
    tags: list[str],
    entities: list[str],
    state: str,
) -> str:
    tags_block = _yaml_list(tags)
    entities_block = _yaml_list(entities)
    return (
        "---\n"
        f"type: {note_type}\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"tags:{tags_block}\n"
        f"entities:{entities_block}\n"
        f"state: {state}\n"
        "---\n"
    )


def _pick_backlinks(rng: random.Random, all_names: list[str], count: int) -> list[str]:
    """Return *count* wikilinks sampled without replacement from *all_names*."""
    sample = rng.sample(all_names, min(count, len(all_names)))
    return [f"[[{name}]]" for name in sample]


# ---------------------------------------------------------------------------
# LLM body generation (optional)
# ---------------------------------------------------------------------------


def _generate_body_llm(
    *,
    note_type: str,
    name: str,
    backlinks: list[str],
    rng: random.Random,
) -> str:
    """Generate note body via Anthropic Batch API.

    Falls back to template if the batch fails or the package is unavailable.
    """
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError:
        return _generate_body_template(
            note_type=note_type, name=name, backlinks=backlinks, rng=rng
        )

    prompt = (
        f"Write a concise Obsidian-style Markdown note body (no frontmatter) for a "
        f"{note_type} named '{name}'. "
        f"Reference the following related notes using wikilinks exactly as written: "
        f"{', '.join(backlinks) if backlinks else 'none'}. "
        f"Keep it under 150 words."
    )

    client = anthropic.Anthropic()
    request: dict[str, Any] = {
        "custom_id": f"{note_type}-{_slug(name)}",
        "params": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
        },
    }

    try:
        batch = client.messages.batches.create(requests=[request])
        # Poll until done
        import time

        while True:
            batch = client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            time.sleep(2)

        results = list(client.messages.batches.results(batch.id))
        if results and results[0].result.type == "succeeded":
            content = results[0].result.message.content
            if content and content[0].type == "text":
                return content[0].text
    except Exception:
        pass

    return _generate_body_template(
        note_type=note_type, name=name, backlinks=backlinks, rng=rng
    )


def _generate_body_template(
    *,
    note_type: str,
    name: str,
    backlinks: list[str],
    rng: random.Random,
) -> str:
    template = _BODY_TEMPLATES[note_type]
    entity = next(
        (p for p in PEOPLE if p["name"] == name),
        None,
    )
    role = entity["role"] if entity else "contributor"
    backlinks_str = "\n".join(backlinks) if backlinks else "_none_"
    return template.format(name=name, role=role, backlinks=backlinks_str)


# ---------------------------------------------------------------------------
# Note assembly
# ---------------------------------------------------------------------------


def _make_note(
    *,
    rng: random.Random,
    note_type: str,
    name: str,
    all_entity_names: list[str],
    use_llm: bool,
    base_dt: datetime,
) -> tuple[str, str]:
    """Return (filename, full_note_content) for one note.

    The filename is ``{slug}.md``.
    """
    created_dt = base_dt
    updated_dt = base_dt
    created = _iso_timestamp(created_dt)
    updated = _iso_timestamp(updated_dt)

    # Tags
    tags: list[str] = [note_type]
    if note_type == "person":
        entity = next((p for p in PEOPLE if p["name"] == name), None)
        if entity:
            tags.append(entity["role"].lower().replace(" ", "-"))
    elif note_type == "company":
        tags.append("org")
    elif note_type == "project":
        tags.append("initiative")
    elif note_type == "meeting":
        tags.append("sync")
    elif note_type == "research":
        tags.append("knowledge")

    # Entities list in frontmatter = names of backlinked items
    others = [n for n in all_entity_names if n != name]
    max_links = min(4, len(others))
    link_count = rng.randint(1, max_links) if max_links >= 1 else 0
    linked_names = rng.sample(others, link_count) if link_count else []
    entities = linked_names

    state = rng.choice(["active", "archived", "draft"])

    fm = _frontmatter(
        note_type=note_type,
        created=created,
        updated=updated,
        tags=tags,
        entities=entities,
        state=state,
    )

    backlinks = [f"[[{n}]]" for n in linked_names]

    if use_llm:
        body = _generate_body_llm(
            note_type=note_type, name=name, backlinks=backlinks, rng=rng
        )
    else:
        body = _generate_body_template(
            note_type=note_type, name=name, backlinks=backlinks, rng=rng
        )

    content = fm + "\n" + body
    filename = _slug(name) + ".md"
    return filename, content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_brain(
    *,
    seed: int,
    fixture_index: int,
    out_dir: Path,
    note_count: int = 100,
    use_llm: bool = True,
) -> Path:
    """Generate a synthetic Obsidian-style brain vault.

    Parameters
    ----------
    seed:
        Master randomness seed.  Combined with *fixture_index* to produce an
        independent ``random.Random`` instance — no global state is mutated.
    fixture_index:
        Index of this fixture within a batch.  Combined with *seed* so that
        different fixtures from the same seed are not identical.
    out_dir:
        Parent directory under which a new vault directory is created.  The
        vault is written to ``out_dir/brain_{seed}_{fixture_index}/``.
    note_count:
        Number of Markdown notes to generate (minimum 1).
    use_llm:
        When ``True``, attempt to generate note bodies via the Anthropic Batch
        API.  When ``False`` (or when the API is unavailable), fall back to
        deterministic templates.

    Returns
    -------
    Path
        Absolute path to the generated vault directory.
    """
    if note_count < 1:
        raise ValueError(f"note_count must be >= 1, got {note_count}")

    rng = random.Random(seed + fixture_index)

    vault_dir = Path(out_dir) / f"brain_{seed}_{fixture_index}"
    vault_dir.mkdir(parents=True, exist_ok=True)

    # Build a pool of (type, name) pairs for this vault
    all_people = [p["name"] for p in PEOPLE]
    all_companies = [c["name"] for c in COMPANIES]
    all_projects = [proj["name"] for proj in PROJECTS]

    # Assign note slots: fill entity types first, then pad with meetings/research
    entity_slots: list[tuple[str, str]] = []

    people_sample = rng.sample(all_people, min(len(all_people), note_count))
    company_sample = rng.sample(all_companies, min(len(all_companies), note_count))
    project_sample = rng.sample(all_projects, min(len(all_projects), note_count))

    for name in people_sample:
        entity_slots.append(("person", name))
    for name in company_sample:
        entity_slots.append(("company", name))
    for name in project_sample:
        entity_slots.append(("project", name))

    # Shuffle to interleave types
    rng.shuffle(entity_slots)
    entity_slots = entity_slots[:note_count]

    # Pad with synthetic meeting / research notes if needed
    while len(entity_slots) < note_count:
        idx = len(entity_slots)
        note_type = rng.choice(["meeting", "research"])
        name = f"{note_type.capitalize()} Note {idx + 1}"
        entity_slots.append((note_type, name))

    all_entity_names = [name for _, name in entity_slots]

    # Fixed base timestamp derived from seed for determinism
    base_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)

    written: list[Path] = []
    for note_type, name in entity_slots:
        filename, content = _make_note(
            rng=rng,
            note_type=note_type,
            name=name,
            all_entity_names=all_entity_names,
            use_llm=use_llm,
            base_dt=base_ts,
        )
        note_path = vault_dir / filename
        note_path.write_text(content, encoding="utf-8")
        written.append(note_path)

    return vault_dir.resolve()
