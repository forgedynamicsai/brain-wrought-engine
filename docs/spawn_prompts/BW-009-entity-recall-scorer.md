BW-009: Entity recall scorer for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-009-entity-recall-scorer (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 2-3 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 evaluates the INGESTION axis. An ingestion-axis submission
receives a raw inbox (emails, calendar, Slack, PDFs per
brain_wrought_engine.fixtures.inbox_generator) and must produce a
structured brain — a directory of markdown notes with YAML
frontmatter and [[wikilinks]].

BW-009 scores how well a submission extracted the ENTITIES that
should exist in the resulting brain, by comparing the submission's
entity set against the gold entity graph (from BW-008's
generate_gold_graph).

## Scoring definition

Given:
- A gold entity graph (GoldGraph from fixtures.gold_graph) listing
  every entity that SHOULD be represented as a note in the brain
- A submission's generated brain directory containing the notes
  it actually produced

Entity recall measures: what fraction of gold entities actually
have a corresponding note in the submission's brain?

    recall = |{gold_entities ∩ submission_entities}| / |gold_entities|

Matching rule: a gold entity E "exists" in the submission if there
is a note in the submission's brain whose stem (slugified) equals
slug(E.name). Case-insensitive slug comparison, with the same
slug() function from brain_wrought_engine.text_utils already in use.

Score range: [0.0, 1.0]. 1.0 = every gold entity got a note.

## Required public API

Module: brain_wrought_engine/ingestion/entity_recall.py

Follow the pattern established by ingestion/setup_friction.py:
- Pydantic input model (frozen)
- Single scorer function returning float
- Fully deterministic
- Determinism class documented in module docstring

Input contract:

    class EntityRecallInput(BaseModel):
        gold_graph: GoldGraph        # from fixtures.gold_graph
        submission_note_ids: frozenset[str]  # stems of notes
                                              # in submission's brain
        model_config = {"frozen": True}

Scorer signature:

    def score_entity_recall(input: EntityRecallInput) -> float:
        """Return [0.0, 1.0] fraction of gold entities present."""

Also export from brain_wrought_engine/ingestion/__init__.py:
    - EntityRecallInput
    - score_entity_recall

## Acceptance criteria

- [ ] Module entity_recall.py exists under ingestion/
- [ ] Public API exactly as specified
- [ ] Score formula documented in module docstring
- [ ] Slug matching is case-insensitive (via text_utils.slug)
- [ ] Handles edge cases:
      - Empty gold_graph → raise ValueError (undefined denominator)
      - Empty submission_note_ids → returns 0.0
      - Submission has extra notes not in gold → IGNORED (recall only,
        not precision; precision is a separate concern)
- [ ] Fully deterministic (pure function of inputs)
- [ ] Unit tests:
      1. Perfect recall (all gold entities have matching notes) → 1.0
      2. Zero recall (no matching notes) → 0.0
      3. Half recall → 0.5 exactly
      4. Case-insensitive slug match verified
      5. Extra submission notes don't inflate score
      6. Empty gold_graph raises ValueError
      7. Empty submission_note_ids returns 0.0
- [ ] Property tests (hypothesis):
      - 0.0 <= score <= 1.0 for any valid input
      - Adding submission_note_ids cannot decrease score
- [ ] mypy strict passes
- [ ] ruff clean
- [ ] 100% test coverage on the module

## Files to create

- brain_wrought_engine/ingestion/entity_recall.py
- tests/ingestion/test_entity_recall.py

## Files to modify

- brain_wrought_engine/ingestion/__init__.py (add exports)

## Out of scope

- Do NOT build entity extraction from raw note content. This scorer
  receives a pre-built set of note IDs; orchestration-layer logic
  (harness repo) will walk the submission's brain and produce the
  submission_note_ids set.
- Do NOT score backlink F1. That's BW-010 running in parallel.
- Do NOT modify fixtures/gold_graph.py.

## Dependencies

No new dependencies. Stdlib + pydantic + hypothesis (all pinned).

## Deliverable

Open PR titled "[BW-009] Entity recall scorer" against main.
Report:
- Commit SHA
- Test count
- Coverage percentage
- Example scores against a seed=42 gold graph with various synthetic
  submission_note_ids sets

STOP conditions (report, don't fix):
- If GoldGraph's public API doesn't expose a way to enumerate gold
  entity names cleanly
- If slug() from text_utils has unexpected behavior on entity names
  with special characters
