"""Citation accuracy scorer for the ingestion axis.

Measures the fraction of submitted citations that reference inbox items which
actually exist in the evaluated manifest. Semantic correctness (does the note
body actually describe something in the item?) is deferred to v1.1; this scorer
performs existence-only validation.

Scoring formula:
    validity = valid_citations / total_citations

Where a citation is VALID if its ``inbox_item_id`` is present in the manifest's
item set (case-sensitive, exact match).

Worked example:
    manifest item IDs: {"email_0001", "slack_0002", "pdf_0003"}
    submission citations:
        note_id="meeting-notes", inbox_item_id="email_0001"   ← valid
        note_id="meeting-notes", inbox_item_id="slack_9999"   ← invalid
        note_id="project-log",   inbox_item_id="pdf_0003"     ← valid
    → score = 2 / 3 ≈ 0.6667

Edge case: if submission has zero citations, score is 1.0 (vacuously valid).

Determinism class: FULLY_DETERMINISTIC — pure function of input.
"""

from __future__ import annotations

from pydantic import BaseModel

from brain_wrought_engine.fixtures.inbox_generator import InboxManifest


class SubmissionCitation(BaseModel):
    """A single citation from a submitted note to an inbox item."""

    note_id: str
    inbox_item_id: str

    model_config = {"frozen": True}


class CitationAccuracyInput(BaseModel):
    """All inputs needed to compute the citation accuracy score."""

    manifest: InboxManifest
    submission_citations: frozenset[SubmissionCitation]

    model_config = {"frozen": True}


class CitationCounters(BaseModel):
    """Detailed citation counts for inspection, logging, and warnings."""

    total_citations: int
    valid_citations: int
    invalid_citations: int
    submission_has_any_citations: bool

    model_config = {"frozen": True}


def compute_citation_counters(input: CitationAccuracyInput) -> CitationCounters:
    """Return detailed counts for inspection and warnings.

    Parameters
    ----------
    input:
        The manifest and submission citations to evaluate.

    Returns
    -------
    CitationCounters
        Counts of total, valid, and invalid citations, plus a flag indicating
        whether the submission included any citations at all.
    """
    known_ids: frozenset[str] = frozenset(item.item_id for item in input.manifest.items)
    total = len(input.submission_citations)
    valid = sum(
        1 for c in input.submission_citations if c.inbox_item_id and c.inbox_item_id in known_ids
    )
    return CitationCounters(
        total_citations=total,
        valid_citations=valid,
        invalid_citations=total - valid,
        submission_has_any_citations=total > 0,
    )


def score_citation_accuracy(input: CitationAccuracyInput) -> float:
    """Return [0.0, 1.0] fraction of citations that reference real inbox items.

    Parameters
    ----------
    input:
        The manifest and submission citations to evaluate.

    Returns
    -------
    float
        Citation validity score in [0.0, 1.0].
        Returns 1.0 when there are zero citations (vacuously valid).
    """
    counters = compute_citation_counters(input)
    if counters.total_citations == 0:
        return 1.0
    return counters.valid_citations / counters.total_citations
