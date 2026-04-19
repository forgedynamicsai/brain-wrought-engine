BW-011: Citation accuracy scorer for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-011-citation-accuracy-scorer (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 2-3 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 evaluates the INGESTION axis. When an ingestion submission
produces a brain from a raw inbox (from
brain_wrought_engine.fixtures.inbox_generator), a good brain cites
its sources: note bodies reference the inbox items that contributed
facts, allowing a reader to trace claims back to their source.

BW-011 scores whether the submission correctly attributes facts to
their sources. An uncited claim is a fabrication by our definition;
a cited claim must actually trace to content in the cited inbox
item.

## Scoring definition

Given:
- Inbox manifest from InboxManifest (fixtures.inbox_generator)
  listing every inbox_item_id and its content
- Submission's brain notes, each of which may reference inbox
  items via structured citation markers

Submission citation format (defined here, enforced by
SUBMISSION_PROTOCOL.md §3.2):

    In the note body: "...the proposal was accepted on Thursday
    [cite:inbox:email_042]..."

Where `inbox:<item_id>` is a reference to an inbox item by its
manifest ID.

Citation accuracy rule: a citation is ACCURATE if the inbox item
referenced actually exists in the manifest AND the note's assertion
near the citation is supported by text in that inbox item.

For v1, we apply a simpler proxy: a citation is VALID if the
referenced inbox_item_id exists in the manifest. Semantic
verification (does the cited item actually support the claim?) is
a v1.1 extension using the judge panel.

    validity = valid_citations / total_citations

If submission has zero citations, return 1.0 (vacuously valid) AND
report a warning in the input counters (see diagnostic helper).

Score range: [0.0, 1.0]. 1.0 = every citation references a real
inbox item.

## Required public API

Module: brain_wrought_engine/ingestion/citation_accuracy.py

Follow the pattern established by ingestion/setup_friction.py and
BW-009/010 running in parallel.

Input contract:

    class SubmissionCitation(BaseModel):
        note_id: str              # stem of the citing note
        inbox_item_id: str        # value after "cite:inbox:"
        model_config = {"frozen": True}

    class CitationAccuracyInput(BaseModel):
        manifest: InboxManifest                          # from fixtures
        submission_citations: frozenset[SubmissionCitation]
        model_config = {"frozen": True}

Scorer signature:

    def score_citation_accuracy(
        input: CitationAccuracyInput,
    ) -> float:
        """Return [0.0, 1.0] fraction of citations that reference
        real inbox items."""

Diagnostic helper:

    class CitationCounters(BaseModel):
        total_citations: int
        valid_citations: int
        invalid_citations: int
        submission_has_any_citations: bool
        model_config = {"frozen": True}

    def compute_citation_counters(
        input: CitationAccuracyInput,
    ) -> CitationCounters:
        """Return detailed counts for inspection and warnings."""

Both exports added to brain_wrought_engine/ingestion/__init__.py.

## Acceptance criteria

- [ ] Module citation_accuracy.py under ingestion/
- [ ] Public API exactly as specified
- [ ] Scoring rule documented in docstring with worked example
- [ ] Edge cases:
      - Empty submission_citations → score = 1.0, counters report
        total=0, valid=0, invalid=0, submission_has_any_citations=False
      - All valid citations → score = 1.0
      - Mixed valid/invalid → score = valid / total
      - All invalid (every cited item_id missing from manifest) →
        score = 0.0
      - Citation referencing item_id that's an empty string → counted
        as invalid
- [ ] Fully deterministic
- [ ] Unit tests:
      1. No citations → score 1.0, counters show zero
      2. Perfect citations → 1.0
      3. Half invalid → 0.5
      4. All invalid → 0.0
      5. compute_citation_counters returns consistent counts
      6. Multiple citations in one note count individually
      7. Same citation from two notes counts as two citations (unique
         by (note_id, inbox_item_id) tuple)
- [ ] Property tests (hypothesis):
      - 0.0 <= score <= 1.0
      - score * total_citations == valid_citations (when total > 0)
- [ ] mypy strict passes
- [ ] ruff clean
- [ ] 100% test coverage

## Files to create

- brain_wrought_engine/ingestion/citation_accuracy.py
- tests/ingestion/test_citation_accuracy.py

## Files to modify

- brain_wrought_engine/ingestion/__init__.py (add exports)

## Out of scope

- Do NOT parse citations from raw note bodies. Orchestration logic
  (harness repo) does that parsing and hands the scorer a
  structured frozenset of SubmissionCitation.
- Do NOT verify semantic support (is the claim near the citation
  actually supported by the cited inbox item's content?). That's
  v1.1 with the judge panel.
- Do NOT modify fixtures/inbox_generator.py.

## Coordination with BW-009 and BW-010 (running in parallel)

All three add exports to ingestion/__init__.py. Resolve merge
conflicts alphabetically:
- citation_accuracy / CitationAccuracyInput / SubmissionCitation /
  CitationCounters / score_citation_accuracy / compute_citation_counters
- entity_recall / EntityRecallInput / score_entity_recall
- backlink_f1 / BacklinkF1Input / SubmissionEdge /
  score_backlink_f1 / compute_f1_components
- setup_friction / SetupBlock / score_setup_friction (already there)

## Dependencies

No new dependencies.

## Deliverable

Open PR titled "[BW-011] Citation accuracy scorer" against main.
Report:
- Commit SHA
- Test count
- Coverage percentage
- Example scores with seed=42 manifest and synthetic
  submission_citations sets

STOP conditions (report, don't fix):
- If InboxManifest doesn't expose inbox item IDs in a form that
  can be checked for existence
- If the InboxManifest schema suggests a different citation
  convention than "cite:inbox:<id>" — flag for discussion rather
  than picking unilaterally
