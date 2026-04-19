BW-012: Schema completeness scorer for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-012-schema-completeness-scorer (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 1-2 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 INGESTION axis: submissions ingest raw inboxes and produce
structured brain vaults. BW-008 defines REQUIRED_FRONTMATTER_KEYS
per NoteType — the set of YAML frontmatter fields each note type
should have.

BW-012 scores how well a submission populated the expected
frontmatter. It is the most straightforward ingestion metric
because the ground truth is a fixed dict, not a fixture output
that varies per seed.

This is NOT a rubric scorer. Despite being called "rubric" in
early BUILD_PLAN.md snippets, the actual semantics is: per note,
what fraction of required keys did the submission actually produce?

## Scoring definition

Given:
- A gold graph (GoldGraph from fixtures.gold_graph), which lists
  every GoldNode including its note_type
- A submission's brain as a frozenset of
  (note_id, frontmatter_keys) pairs — one per note the submission
  produced

For each gold node, find the matching submission note by note_id
(slug-canonical match, same convention as BW-009). If a matching
submission note exists, compute per-note completeness:

    per_note_completeness = |submission_keys ∩ required_keys| / |required_keys|

Overall score:

    completeness = mean(per_note_completeness across all gold nodes)

If a gold node has NO matching submission note, that node
contributes 0.0 to the mean. This penalizes missing notes alongside
incomplete frontmatter.

Score range: [0.0, 1.0].

## Required public API

Module: brain_wrought_engine/ingestion/schema_completeness.py

Follow the pattern established by the other ingestion scorers
(setup_friction.py, entity_recall.py, backlink_f1.py,
citation_accuracy.py).

Input contract:

    class SubmissionNoteSchema(BaseModel):
        note_id: str  # stem of the note
        frontmatter_keys: frozenset[str]  # keys present
                                           # in the note's YAML
        model_config = {"frozen": True}

    class SchemaCompletenessInput(BaseModel):
        gold_graph: GoldGraph
        submission_schemas: frozenset[SubmissionNoteSchema]
        model_config = {"frozen": True}

Scorer signature:

    def score_schema_completeness(
        input: SchemaCompletenessInput,
    ) -> float:
        """Return [0.0, 1.0] mean per-note completeness across all
        gold nodes. Missing notes contribute 0.0."""

Diagnostic helper (optional but valuable):

    class CompletenessBreakdown(BaseModel):
        total_gold_notes: int
        matched_notes: int  # gold nodes with a submission match
        missing_notes: int  # gold nodes with no submission match
        mean_per_note_completeness: float  # across matched notes only
        overall_score: float  # across all gold nodes
        model_config = {"frozen": True}

    def compute_completeness_breakdown(
        input: SchemaCompletenessInput,
    ) -> CompletenessBreakdown:
        """Return detailed metrics for inspection."""

Both exports added to brain_wrought_engine/ingestion/__init__.py.

Import REQUIRED_FRONTMATTER_KEYS from brain_wrought_engine.fixtures.gold_graph
to get the per-type required key sets.

## Acceptance criteria

- [ ] Module schema_completeness.py under ingestion/
- [ ] Public API exactly as specified
- [ ] Formula documented in module docstring
- [ ] Uses slug() for note_id matching (case-preserving, same
      convention as BW-009)
- [ ] Uses REQUIRED_FRONTMATTER_KEYS from gold_graph module
      (do NOT duplicate the dict)
- [ ] Edge cases:
      - Empty gold graph → raise ValueError (no denominator)
      - Gold node present but no matching submission → contributes 0.0
      - Submission has extra notes not in gold → ignored
      - Submission note has extra keys beyond required → doesn't
        penalize, doesn't boost (only required keys matter)
- [ ] Fully deterministic (pure function)
- [ ] Unit tests:
      1. All gold nodes present, all keys filled → 1.0
      2. All gold nodes present, no keys filled → 0.0
      3. All gold nodes present, half keys filled → 0.5
      4. Half gold nodes missing from submission → 0.5 * per_note_completeness
      5. Empty gold graph → ValueError
      6. Extra submission notes don't affect score
      7. Extra submission keys don't affect score
      8. compute_completeness_breakdown returns consistent counts
- [ ] Property tests (hypothesis):
      - 0.0 <= score <= 1.0
      - Adding submission notes can never decrease score
      - Adding keys to a matched submission note can never decrease score
- [ ] mypy strict passes
- [ ] ruff clean
- [ ] 100% test coverage

## Files to create

- brain_wrought_engine/ingestion/schema_completeness.py
- tests/ingestion/test_schema_completeness.py

## Files to modify

- brain_wrought_engine/ingestion/__init__.py (add exports)

Merge ordering with __init__.py: add your exports alphabetically
within the existing pattern. Current exports (as of main):
BacklinkF1Input, CitationAccuracyInput, CitationCounters,
EntityRecallInput, SetupBlock, SubmissionCitation, SubmissionEdge,
compute_citation_counters, compute_f1_components,
score_backlink_f1, score_citation_accuracy, score_entity_recall,
score_setup_friction.

## Out of scope

- Do NOT parse frontmatter from raw note content. Orchestration
  (harness repo) will handle YAML parsing and pass the scorer a
  pre-built set of (note_id, frontmatter_keys) pairs.
- Do NOT score content quality, entity mentions, or backlink
  structure. Those are BW-009, BW-010, BW-011.
- Do NOT modify fixtures/gold_graph.py or REQUIRED_FRONTMATTER_KEYS.

## Dependencies

No new dependencies.

## Deliverable

Open PR titled "[BW-012] Schema completeness scorer" against main.
Report:
- Commit SHA
- Test count
- Coverage percentage
- Example breakdown against seed=42 gold graph with synthetic
  submission schemas at various completeness levels

STOP conditions (report, don't fix):
- If GoldGraph doesn't expose nodes in a form that makes
  per-type required_keys lookup straightforward
- If REQUIRED_FRONTMATTER_KEYS isn't importable cleanly
  (circular dependency between ingestion and fixtures modules)
