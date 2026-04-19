BW-010: Backlink F1 scorer for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-010-backlink-f1-scorer (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 2-3 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 evaluates the INGESTION axis. An ingestion submission
produces a structured brain with [[wikilinks]] between notes,
forming a graph.

BW-010 scores how well the submission's graph matches the gold
entity graph (from BW-008's generate_gold_graph). A great brain
has all the gold edges (recall) without adding spurious ones
(precision).

## Scoring definition

Given:
- Gold graph edges from GoldGraph (each GoldEdge has source,
  target, edge_type)
- Submission's graph: for each submission note, the set of
  [[wikilink]] targets in its body

Treat both as sets of (source_slug, target_slug) pairs. Compute:

    precision = |gold ∩ submission| / |submission|
    recall    = |gold ∩ submission| / |gold|
    f1        = 2 * p * r / (p + r)

Edge type is NOT used in v1 — we only require the topology
(which notes link to which) to match. Edge type semantic scoring
is a v1.1 extension.

Match rule: an edge (A, B) in the submission matches a gold edge
(C, D) iff slug(A) == slug(C) and slug(B) == slug(D). Directional.

Score range: [0.0, 1.0]. 1.0 = perfect graph match.

## Required public API

Module: brain_wrought_engine/ingestion/backlink_f1.py

Follow the pattern established by ingestion/setup_friction.py
(and BW-009's entity_recall.py running in parallel — use the same
structural conventions).

Input contract:

    class SubmissionEdge(BaseModel):
        source_note_id: str  # stem, as produced by submission
        target_note_id: str  # stem, target of [[wikilink]]
        model_config = {"frozen": True}

    class BacklinkF1Input(BaseModel):
        gold_graph: GoldGraph                       # from fixtures
        submission_edges: frozenset[SubmissionEdge] # extracted
                                                     # from submission
        model_config = {"frozen": True}

Scorer signature:

    def score_backlink_f1(input: BacklinkF1Input) -> float:
        """Return [0.0, 1.0] F1 over directed edges."""

Also export a diagnostic helper for debugging:

    def compute_f1_components(
        input: BacklinkF1Input,
    ) -> tuple[float, float, float]:
        """Return (precision, recall, f1) for inspection."""

Both exports added to brain_wrought_engine/ingestion/__init__.py.

## Acceptance criteria

- [ ] Module backlink_f1.py under ingestion/
- [ ] Public API exactly as specified
- [ ] F1 formula documented in docstring with worked example
- [ ] Slug comparison via text_utils.slug, case-insensitive
- [ ] Edge cases:
      - Empty gold graph + empty submission → f1 = 1.0 (vacuous)
      - Empty gold, non-empty submission → f1 = 0.0
      - Non-empty gold, empty submission → f1 = 0.0
      - When p == 0 and r == 0 → f1 = 0.0 (avoid division by zero)
- [ ] Fully deterministic (pure function of inputs)
- [ ] Unit tests:
      1. Perfect match → f1 = 1.0
      2. All precision no recall (submission is subset of gold) →
         p = 1.0, r < 1.0, f1 somewhere in (0, 1)
      3. All recall no precision (submission is superset of gold) →
         p < 1.0, r = 1.0, f1 somewhere in (0, 1)
      4. Zero overlap → f1 = 0.0
      5. Vacuous empty/empty → f1 = 1.0
      6. compute_f1_components returns matching (p, r, f1)
- [ ] Property tests (hypothesis):
      - 0.0 <= f1 <= 1.0 always
      - f1 == 1.0 iff submission edges == gold edges (set-equal
        after slug normalization)
- [ ] Direction matters: (A, B) != (B, A) in edge set
- [ ] mypy strict passes
- [ ] ruff clean
- [ ] 100% test coverage

## Files to create

- brain_wrought_engine/ingestion/backlink_f1.py
- tests/ingestion/test_backlink_f1.py

## Files to modify

- brain_wrought_engine/ingestion/__init__.py (add exports)

## Out of scope

- Do NOT score edge-type correctness. Topology only in v1.
- Do NOT build wikilink extraction from note content. The scorer
  receives a pre-built set of SubmissionEdge; orchestration logic
  (harness repo) parses [[wikilinks]] from submission note bodies
  into that set.
- Do NOT modify fixtures/gold_graph.py.

## Coordination with BW-009 (running in parallel)

Both BW-009 and BW-010 add exports to ingestion/__init__.py. If
merge conflicts surface there, resolve by preserving both additions
alphabetically. The scope of each scorer's file is fully
independent — no shared code beyond the __init__.py additions.

## Dependencies

No new dependencies.

## Deliverable

Open PR titled "[BW-010] Backlink F1 scorer" against main.
Report:
- Commit SHA
- Test count
- Coverage percentage
- Example F1 against seed=42 gold with synthetic submission edges
  at different precision/recall tradeoffs

STOP conditions (report, don't fix):
- If GoldGraph doesn't expose edges in a form convertible to
  (source_slug, target_slug) pairs
- If there's ambiguity about directionality in the gold graph
  (e.g., if an edge type like "meeting_with" is semantically
  bidirectional, flag it — the spec says directional, but if
  the gold graph stores bidirectional edges, we need to decide
  together whether to double them or treat as undirected)
