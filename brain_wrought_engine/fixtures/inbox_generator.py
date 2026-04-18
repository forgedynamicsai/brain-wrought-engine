"""Synthetic inbox fixture generator for the ingestion axis.

Produces a realistic raw inbox that ingestion-axis submissions must process
into a well-structured brain. This is the input side of ingestion evaluation;
the gold brain structure (BW-008) is the output side.

Determinism class: SEEDED_STOCHASTIC — same (seed, inbox_size) always produces
an identical file tree, including any LLM-generated content (cached by seed +
item_index).
"""

from __future__ import annotations

import datetime
import json
import math
import random
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel

from brain_wrought_engine.fixtures.entity_pool import COMPANIES, PEOPLE, PROJECTS

InboxSize = Literal["small", "medium", "large"]
ItemType = Literal["email", "calendar", "slack", "pdf", "attachment"]

_SIZE_COUNTS: dict[str, int] = {"small": 20, "medium": 50, "large": 100}

# Distribution: 35% emails, 15% calendar, 30% Slack, 10% PDF stubs, 10% attachments
_TYPE_FRACTIONS: list[tuple[ItemType, float]] = [
    ("email", 0.35),
    ("calendar", 0.15),
    ("slack", 0.30),
    ("pdf", 0.10),
    ("attachment", 0.10),
]
_TYPE_SUBDIRS: dict[str, str] = {
    "email": "emails",
    "calendar": "calendar",
    "slack": "slack",
    "pdf": "pdfs",
    "attachment": "attachments",
}
_TYPE_EXTENSIONS: dict[str, str] = {
    "email": ".eml",
    "calendar": ".ics",
    "slack": ".json",
    "pdf": ".txt",
    "attachment": ".txt",
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class InboxItem(BaseModel):
    item_id: str
    item_type: ItemType
    file_path: str
    source_timestamp: str
    referenced_entities: list[str]
    referenced_projects: list[str]

    model_config = {"frozen": True}


class InboxManifest(BaseModel):
    seed: int
    inbox_size: str
    generated_at: str
    entity_pool: list[str]
    items: list[InboxItem]

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------


def _compute_type_distribution(total: int) -> dict[ItemType, int]:
    """Ceil-then-trim distribution across item types."""
    counts: dict[str, int] = {t: math.ceil(f * total) for t, f in _TYPE_FRACTIONS}
    excess = sum(counts.values()) - total
    if excess > 0:
        order = sorted(counts.keys(), key=lambda k: -counts[k])
        for key in order:
            if excess <= 0:
                break
            trim = min(excess, counts[key])
            counts[key] -= trim
            excess -= trim
    return cast("dict[ItemType, int]", counts)


# ---------------------------------------------------------------------------
# Entity pool helpers
# ---------------------------------------------------------------------------


def _build_entity_pool(seed: int, n_people: int = 8, n_projects: int = 5) -> dict[str, list[str]]:
    """Return a seeded sample of people and projects from the static pools."""
    rng = random.Random(seed)
    people_sample = rng.sample(PEOPLE, min(n_people, len(PEOPLE)))
    projects_sample = rng.sample(PROJECTS, min(n_projects, len(PROJECTS)))
    _ = COMPANIES  # available but not sampled in v1
    return {
        "people": [p["name"] for p in people_sample],
        "projects": [p["name"] for p in projects_sample],
    }


def _email_address(name: str) -> str:
    """Derive a deterministic email address from a person name."""
    slug = name.lower().replace(" ", ".").replace("'", "").replace("-", "")
    return f"{slug}@example.com"


def _to_rfc2822(dt: datetime.datetime) -> str:
    """Format a datetime as RFC 2822 (email Date header)."""
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _to_ical(dt: datetime.datetime) -> str:
    """Format a datetime as iCal DTSTART value."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _to_iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Timestamp generation
# ---------------------------------------------------------------------------


def _make_timestamp_window(seed: int) -> tuple[datetime.datetime, datetime.datetime]:
    """Return (window_start, now) — a 90-day window derived from seed."""
    base_date = datetime.date(2026, 1, 1) + datetime.timedelta(days=seed % 60)
    now = datetime.datetime(base_date.year, base_date.month, base_date.day, 12, 0, 0)
    window_start = now - datetime.timedelta(days=90)
    return window_start, now


def _random_timestamp(rng: random.Random, window_start: datetime.datetime,
                      now: datetime.datetime) -> datetime.datetime:
    total_seconds = int((now - window_start).total_seconds())
    offset = rng.randint(0, total_seconds)
    return window_start + datetime.timedelta(seconds=offset)


# ---------------------------------------------------------------------------
# Entity assignment — guarantees every entity appears in >= 2 items
# ---------------------------------------------------------------------------


def _assign_entities(
    rng: random.Random,
    total_items: int,
    people: list[str],
    projects: list[str],
) -> list[tuple[list[str], list[str]]]:
    """Return per-item (people_refs, project_refs).

    Contract:
    - Every entity in people+projects appears in a distinct set of
      >= 2 items (when total_items >= 2; single-item inboxes clamp).
    - Each item ends up with >= 1 person AND >= 1 project.
    """
    all_entities = people + projects
    item_people: list[list[str]] = [[] for _ in range(total_items)]
    item_projects: list[list[str]] = [[] for _ in range(total_items)]

    for entity in all_entities:
        k = min(2 + rng.randint(0, 2), total_items)  # 2-4 distinct items
        indices = rng.sample(range(total_items), k)
        target = item_people if entity in people else item_projects
        for i in indices:
            if entity not in target[i]:
                target[i].append(entity)

    # Ensure every item has >= 1 person AND >= 1 project
    for i in range(total_items):
        if not item_people[i]:
            item_people[i].append(rng.choice(people))
        if not item_projects[i]:
            item_projects[i].append(rng.choice(projects))

    return list(zip(item_people, item_projects, strict=True))


# ---------------------------------------------------------------------------
# LLM caching
# ---------------------------------------------------------------------------


def _cache_path(seed: int, item_index: int) -> Path:
    root = Path(__file__).parent.parent.parent / ".cache" / "inbox"
    return root / str(seed) / f"{item_index:04d}.json"


def _load_cached(seed: int, item_index: int) -> str | None:
    p = _cache_path(seed, item_index)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return str(data.get("content", ""))
        except (json.JSONDecodeError, KeyError):
            return None
    return None


def _save_cached(seed: int, item_index: int, content: str) -> None:
    p = _cache_path(seed, item_index)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"content": content}), encoding="utf-8")


def _generate_content_llm(
    item_type: ItemType,
    item_index: int,
    seed: int,
    people_refs: list[str],
    project_refs: list[str],
    timestamp: datetime.datetime,
) -> str:
    from litellm import completion  # local import — only when use_llm=True

    cached = _load_cached(seed, item_index)
    if cached is not None:
        return cached

    entity_list = ", ".join(people_refs + project_refs)
    prompt = (
        f"Write a realistic {item_type} involving these people and projects: {entity_list}. "
        f"The item is from {_to_iso(timestamp)}. "
        "Keep it under 400 words. Write only the body/content, no metadata headers."
    )
    response = completion(
        model="claude-haiku-4-5-20251001",
        temperature=0.7,
        max_tokens=600,
        seed=seed + item_index,
        messages=[{"role": "user", "content": prompt}],
    )
    content: str = response.choices[0].message.content or ""
    _save_cached(seed, item_index, content)
    return content


# ---------------------------------------------------------------------------
# Item format renderers
# ---------------------------------------------------------------------------


def _render_email(
    rng: random.Random,
    people_refs: list[str],
    project_refs: list[str],
    timestamp: datetime.datetime,
    body: str,
) -> str:
    sender = people_refs[0]
    recipient = people_refs[1] if len(people_refs) > 1 else rng.choice(people_refs)
    project = project_refs[0]
    subject = f"Update on {project}"
    return (
        f"From: {sender} <{_email_address(sender)}>\r\n"
        f"To: {recipient} <{_email_address(recipient)}>\r\n"
        f"Subject: {subject}\r\n"
        f"Date: {_to_rfc2822(timestamp)}\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        f"{body}\r\n"
    )


def _render_calendar(
    people_refs: list[str],
    project_refs: list[str],
    timestamp: datetime.datetime,
    body: str,
) -> str:
    attendees = ", ".join(people_refs)
    project = project_refs[0]
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART:{_to_ical(timestamp)}\r\n"
        f"SUMMARY:{project} sync\r\n"
        f"DESCRIPTION:{body[:200].replace(chr(10), ' ')}\r\n"
        f"ATTENDEES:{attendees}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def _render_slack(
    rng: random.Random,
    people_refs: list[str],
    project_refs: list[str],
    timestamp: datetime.datetime,
    body: str,
) -> str:
    project = project_refs[0]
    channel = "#" + project.lower().replace(" ", "-")
    base_ts = timestamp.timestamp()
    messages = []
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()][:4] or [body[:100]]
    for j, line in enumerate(lines):
        speaker = people_refs[j % len(people_refs)]
        username = speaker.lower().replace(" ", ".")
        messages.append({
            "user": username,
            "text": line,
            "ts": str(base_ts + j * 30),
        })
    return json.dumps(
        {
            "channel": channel,
            "timestamp": _to_iso(timestamp),
            "messages": messages,
        },
        indent=2,
    )


def _render_pdf(body: str, project_refs: list[str]) -> str:
    project = project_refs[0]
    return (
        "[PDF STUB — real PDF generation deferred to v1.1]\n"
        f"Original filename: {project.lower().replace(' ', '_')}.pdf\n\n"
        f"{body}\n"
    )


def _render_attachment(body: str, project_refs: list[str]) -> str:
    project = project_refs[0]
    return f"[ATTACHMENT: {project.lower().replace(' ', '_')}_notes.txt]\n{body}\n"


# ---------------------------------------------------------------------------
# Placeholder content (use_llm=False)
# ---------------------------------------------------------------------------


def _make_placeholder_body(people_refs: list[str], project_refs: list[str]) -> str:
    """Generate deterministic body text that literally contains all entity names."""
    people_str = " and ".join(people_refs)
    projects_str = " and ".join(project_refs)
    return (
        f"This item involves {people_str}.\n"
        f"The main topic is {projects_str}.\n"
        "Progress has been steady this week. Action items were discussed and assigned.\n"
        f"Follow-up scheduled with {people_refs[0]} regarding {project_refs[0]}.\n"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_inbox(
    *,
    out_dir: Path,
    seed: int,
    inbox_size: InboxSize = "medium",
    use_llm: bool = True,
) -> InboxManifest:
    """Generate a deterministic synthetic inbox fixture tree.

    Parameters
    ----------
    out_dir:
        Directory to create. Subdirectories emails/, calendar/, slack/,
        pdfs/, attachments/ are created automatically.
    seed:
        Randomness seed. Same seed + same inbox_size → identical file tree.
    inbox_size:
        "small" (20), "medium" (50), or "large" (100) items.
    use_llm:
        If True, use Haiku batch via LiteLLM for content (cached to disk).
        If False, generate deterministic placeholder content (for tests).
    """
    rng = random.Random(seed)
    total = _SIZE_COUNTS[inbox_size]
    type_counts = _compute_type_distribution(total)

    # Create subdirectories
    out_dir.mkdir(parents=True, exist_ok=True)
    for subdir in _TYPE_SUBDIRS.values():
        (out_dir / subdir).mkdir(exist_ok=True)

    # Sample entity pool
    pool = _build_entity_pool(seed)
    people = pool["people"]
    projects = pool["projects"]

    # Timestamp window
    window_start, now = _make_timestamp_window(seed)

    # Build ordered work list: item_type per index
    type_sequence: list[ItemType] = []
    for item_type, count in type_counts.items():
        type_sequence.extend([item_type] * count)
    rng.shuffle(type_sequence)

    # Assign entities — guarantees every entity in >= 2 items
    assignments = _assign_entities(rng, total, people, projects)

    items: list[InboxItem] = []
    type_counters: dict[str, int] = {t: 0 for t in _TYPE_SUBDIRS}

    for idx, item_type in enumerate(type_sequence):
        people_refs, project_refs = assignments[idx]
        timestamp = _random_timestamp(rng, window_start, now)
        counter = type_counters[item_type]
        type_counters[item_type] += 1

        item_id = f"{item_type}_{counter:04d}"
        ext = _TYPE_EXTENSIONS[item_type]
        rel_path = f"{_TYPE_SUBDIRS[item_type]}/{item_id}{ext}"
        abs_path = out_dir / rel_path

        if use_llm:
            body = _generate_content_llm(
                item_type, idx, seed, people_refs, project_refs, timestamp
            )
        else:
            body = _make_placeholder_body(people_refs, project_refs)

        if item_type == "email":
            content = _render_email(rng, people_refs, project_refs, timestamp, body)
        elif item_type == "calendar":
            content = _render_calendar(people_refs, project_refs, timestamp, body)
        elif item_type == "slack":
            content = _render_slack(rng, people_refs, project_refs, timestamp, body)
        elif item_type == "pdf":
            content = _render_pdf(body, project_refs)
        else:
            content = _render_attachment(body, project_refs)

        abs_path.write_text(content, encoding="utf-8")

        items.append(
            InboxItem(
                item_id=item_id,
                item_type=item_type,
                file_path=rel_path,
                source_timestamp=_to_iso(timestamp),
                referenced_entities=list(people_refs),
                referenced_projects=list(project_refs),
            )
        )

    manifest = InboxManifest(
        seed=seed,
        inbox_size=inbox_size,
        generated_at=_to_iso(now),
        entity_pool=people + projects,
        items=sorted(items, key=lambda it: it.item_id),
    )
    (out_dir / "_manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest
