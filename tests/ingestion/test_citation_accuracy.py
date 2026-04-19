"""Tests for brain_wrought_engine.ingestion.citation_accuracy (BW-011)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from brain_wrought_engine.fixtures.inbox_generator import InboxItem, InboxManifest
from brain_wrought_engine.ingestion.citation_accuracy import (
    CitationAccuracyInput,
    CitationCounters,
    SubmissionCitation,
    compute_citation_counters,
    score_citation_accuracy,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_GENERATED_AT = "2026-01-01T12:00:00Z"


def _make_manifest(item_ids: list[str]) -> InboxManifest:
    """Build a minimal InboxManifest containing only the given item IDs."""
    items = [
        InboxItem(
            item_id=iid,
            item_type="email",
            file_path=f"emails/{iid}.eml",
            source_timestamp=_GENERATED_AT,
            referenced_entities=[],
            referenced_projects=[],
        )
        for iid in item_ids
    ]
    return InboxManifest(
        seed=42,
        inbox_size="small",
        generated_at=_GENERATED_AT,
        entity_pool=[],
        items=items,
    )


def _make_input(
    item_ids: list[str],
    citations: list[tuple[str, str]],
) -> CitationAccuracyInput:
    """Build CitationAccuracyInput from item_ids and (note_id, inbox_item_id) pairs."""
    return CitationAccuracyInput(
        manifest=_make_manifest(item_ids),
        submission_citations=frozenset(
            SubmissionCitation(note_id=n, inbox_item_id=i) for n, i in citations
        ),
    )


# ---------------------------------------------------------------------------
# Unit tests — score_citation_accuracy
# ---------------------------------------------------------------------------


def test_no_citations_returns_one() -> None:
    """Zero citations → vacuously valid, score = 1.0."""
    inp = _make_input(["email_0001", "slack_0002"], [])
    assert score_citation_accuracy(inp) == 1.0


def test_all_valid_returns_one() -> None:
    """All cited items exist in manifest → score = 1.0."""
    inp = _make_input(
        ["email_0001", "slack_0002", "pdf_0003"],
        [
            ("note-a", "email_0001"),
            ("note-a", "slack_0002"),
            ("note-b", "pdf_0003"),
        ],
    )
    assert score_citation_accuracy(inp) == 1.0


def test_half_invalid_returns_half() -> None:
    """2 valid, 2 invalid → score = 0.5."""
    inp = _make_input(
        ["email_0001", "slack_0002"],
        [
            ("note-a", "email_0001"),
            ("note-a", "slack_0002"),
            ("note-b", "ghost_9999"),
            ("note-b", "ghost_8888"),
        ],
    )
    assert score_citation_accuracy(inp) == 0.5


def test_all_invalid_returns_zero() -> None:
    """Every cited item_id is absent from manifest → score = 0.0."""
    inp = _make_input(
        ["email_0001"],
        [
            ("note-a", "ghost_9999"),
            ("note-b", "ghost_8888"),
        ],
    )
    assert score_citation_accuracy(inp) == 0.0


def test_empty_inbox_item_id_counted_as_invalid() -> None:
    """A citation with an empty inbox_item_id is invalid."""
    inp = _make_input(
        ["email_0001"],
        [
            ("note-a", "email_0001"),
            ("note-b", ""),
        ],
    )
    assert score_citation_accuracy(inp) == 0.5


# ---------------------------------------------------------------------------
# Unit tests — compute_citation_counters
# ---------------------------------------------------------------------------


def test_counters_zero_citations() -> None:
    """No citations → counters all zero, submission_has_any_citations=False."""
    inp = _make_input(["email_0001"], [])
    counters = compute_citation_counters(inp)
    assert counters == CitationCounters(
        total_citations=0,
        valid_citations=0,
        invalid_citations=0,
        submission_has_any_citations=False,
    )


def test_counters_consistent_with_score() -> None:
    """compute_citation_counters counts are consistent: valid + invalid == total."""
    inp = _make_input(
        ["email_0001", "slack_0002"],
        [
            ("note-a", "email_0001"),
            ("note-b", "ghost_9999"),
            ("note-c", "ghost_8888"),
        ],
    )
    counters = compute_citation_counters(inp)
    assert counters.valid_citations + counters.invalid_citations == counters.total_citations
    assert counters.total_citations == 3
    assert counters.valid_citations == 1
    assert counters.invalid_citations == 2
    assert counters.submission_has_any_citations is True


def test_counters_all_valid() -> None:
    """All citations valid → invalid_citations == 0."""
    inp = _make_input(
        ["email_0001", "slack_0002"],
        [("note-a", "email_0001"), ("note-b", "slack_0002")],
    )
    counters = compute_citation_counters(inp)
    assert counters.valid_citations == 2
    assert counters.invalid_citations == 0
    assert counters.submission_has_any_citations is True


# ---------------------------------------------------------------------------
# Multiple citations from one note count individually
# ---------------------------------------------------------------------------


def test_multiple_citations_from_one_note_counted_individually() -> None:
    """Two citations in the same note both count; each is checked independently."""
    inp = _make_input(
        ["email_0001", "slack_0002"],
        [
            ("meeting-notes", "email_0001"),
            ("meeting-notes", "slack_0002"),
        ],
    )
    counters = compute_citation_counters(inp)
    assert counters.total_citations == 2
    assert counters.valid_citations == 2


# ---------------------------------------------------------------------------
# Same citation from two different notes counts as two citations
# ---------------------------------------------------------------------------


def test_same_item_id_from_two_notes_counts_as_two() -> None:
    """(note-a, email_0001) and (note-b, email_0001) are distinct citations."""
    inp = _make_input(
        ["email_0001"],
        [
            ("note-a", "email_0001"),
            ("note-b", "email_0001"),
        ],
    )
    counters = compute_citation_counters(inp)
    assert counters.total_citations == 2
    assert counters.valid_citations == 2
    assert score_citation_accuracy(inp) == 1.0


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------

_ITEM_IDS = st.text(min_size=1, max_size=12, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
_NOTE_IDS = st.text(min_size=1, max_size=12, alphabet="abcdefghijklmnopqrstuvwxyz-")


@st.composite
def _citation_accuracy_input(draw: st.DrawFn) -> CitationAccuracyInput:
    """Strategy producing an arbitrary CitationAccuracyInput."""
    item_id_list = draw(st.lists(_ITEM_IDS, min_size=0, max_size=10, unique=True))
    note_id_list = draw(st.lists(_NOTE_IDS, min_size=0, max_size=5, unique=True))

    all_possible_ids = item_id_list + draw(st.lists(_ITEM_IDS, min_size=0, max_size=5))

    citation_pairs: list[tuple[str, str]] = []
    if note_id_list and all_possible_ids:
        raw = draw(
            st.lists(
                st.tuples(
                    st.sampled_from(note_id_list),
                    st.sampled_from(all_possible_ids),
                ),
                min_size=0,
                max_size=15,
            )
        )
        citation_pairs = list({(n, i) for n, i in raw})

    return _make_input(item_id_list, citation_pairs)


@settings(max_examples=300)
@given(_citation_accuracy_input())
def test_score_in_unit_interval(inp: CitationAccuracyInput) -> None:
    """score_citation_accuracy always returns a value in [0.0, 1.0]."""
    score = score_citation_accuracy(inp)
    assert 0.0 <= score <= 1.0


@settings(max_examples=300)
@given(_citation_accuracy_input())
def test_score_times_total_equals_valid(inp: CitationAccuracyInput) -> None:
    """When total > 0: score * total == valid (integer arithmetic equivalence)."""
    counters = compute_citation_counters(inp)
    score = score_citation_accuracy(inp)
    if counters.total_citations > 0:
        assert abs(score * counters.total_citations - counters.valid_citations) < 1e-9
