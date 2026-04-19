BW-INTEG-2: Inbox-to-gold-graph conversion layer

Repo: brain-wrought-engine
Branch: issue/BW-INTEG-2-inbox-to-gold-graph (create from current main)
Model: Sonnet 4.6 for implementation; Opus 4.7 recommended for
architecture discussion before code ships
Estimated wall-clock: architecture 30 min, implementation 2-3 hrs

## Permission model

--dangerously-skip-permissions is assumed. Do NOT proceed with
code changes if the architectural path is ambiguous. STOP and
report if you encounter ambiguity that requires a design decision.

## Context

The ingestion-axis pipeline has an integration gap surfaced by
end-to-end smoke testing on 2026-04-19 (see DECISIONS.md entry).

Current state:
- generate_inbox(seed) -> InboxManifest
  - manifest.entity_pool: list[str]  (names only)
  - manifest.items: list[InboxItem]
- generate_gold_graph(seed, people, projects, cross_references) -> GoldGraph
  - requires structured PersonEntity / ProjectEntity / CrossReference

No code converts between them. Per-scorer tests pass because they
construct synthetic structured entities directly. Nothing exercises
the inbox -> gold graph chain.

BW-INTEG-2 closes this gap.

## Architectural choice required BEFORE implementation

Two viable designs. The implementer must report a recommendation
with reasoning before writing code.

### Option A: Shared entity pool module

Extract PersonEntity, ProjectEntity, CrossReference into a new
module brain_wrought_engine/fixtures/entities.py. Both
inbox_generator and gold_graph import from there. A new function
generate_entity_pool(seed) produces the structured entities; both
generators consume it.

Pros: Single source of truth. Neither generator owns the entity
types. Clean dependency graph.

Cons: Refactor touches both inbox_generator and gold_graph.
Existing tests may need updates. More invasive.

### Option B: Enrich InboxManifest with structured entities

Change InboxManifest.entity_pool from list[str] to include
structured PersonEntity, ProjectEntity, CrossReference collections
alongside the names. gold_graph can then consume them directly
from a manifest.

Pros: Smaller change. Manifest becomes the canonical
inbox+entities artifact.

Cons: Couples gold-graph structured types into the inbox manifest's
schema, which is sub-optimal if they should be separate concerns.

## Required public API (after architecture decision)

If Option A is chosen:
- brain_wrought_engine/fixtures/entities.py exists with moved
  PersonEntity, ProjectEntity, CrossReference definitions
- generate_entity_pool(seed: int, people_count: int = 8, projects_count: int = 5, ...) -> tuple[list[PersonEntity], list[ProjectEntity], list[CrossReference]]
- inbox_generator and gold_graph both import from entities module

If Option B is chosen:
- InboxManifest gains people, projects, cross_references fields
  (structured, not just names)
- entity_pool field renamed or kept for backward compat
- Migration path for any callers relying on current
  entity_pool: list[str] schema

In BOTH options, expose a top-level helper for end-to-end users:

    def generate_fixture_pair(
        seed: int,
        inbox_out_dir: Path,
        gold_graph_out_dir: Path | None = None,
    ) -> tuple[InboxManifest, GoldGraph]:
        """Generate a matched inbox + gold graph pair from a single seed."""

This lets a smoke test call ONE function and get both halves
consistent with each other.

## Acceptance criteria

- [ ] Architecture recommendation (A or B) with reasoning recorded
      in DECISIONS.md via a new entry
- [ ] Implementation matches chosen architecture
- [ ] generate_fixture_pair(seed=42) returns consistent
      (inbox, gold_graph) where every gold node's
      source_inbox_items references inbox_item_ids that exist in
      the manifest
- [ ] Existing inbox_generator tests still pass
- [ ] Existing gold_graph tests still pass
- [ ] End-to-end smoke test in tests/integration/ exercising the
      full chain: inbox -> gold_graph -> at least one scorer
      (entity_recall is simplest) with a synthetic "perfect
      submission" derived from the gold graph, producing score 1.0
- [ ] mypy strict passes
- [ ] ruff clean
- [ ] Coverage does not decrease

## Files to touch (Option A path)

Create:
- brain_wrought_engine/fixtures/entities.py
- tests/integration/test_inbox_to_gold_graph.py
- brain_wrought_engine/fixtures/pair.py (generate_fixture_pair)

Modify:
- brain_wrought_engine/fixtures/inbox_generator.py (import from entities, refactor entity building)
- brain_wrought_engine/fixtures/gold_graph.py (import from entities, remove local entity class defs)
- brain_wrought_engine/fixtures/__init__.py (exports)

## Files to touch (Option B path)

Modify:
- brain_wrought_engine/fixtures/inbox_generator.py (enrich manifest)
- brain_wrought_engine/fixtures/gold_graph.py (accept manifest)
- tests for both

Create:
- tests/integration/test_inbox_to_gold_graph.py
- brain_wrought_engine/fixtures/pair.py

## Out of scope

- Do NOT build a submission-side ingestion module. BW-INTEG-2 only
  generates matched (inbox, gold_graph) pairs. A submission that
  consumes the inbox and produces something to score is a separate
  concern (analogous to BW-006 for retrieval).
- Do NOT modify any scorer in brain_wrought_engine/ingestion/.

## Dependencies

No new dependencies.

## Deliverable

Open PR titled "[BW-INTEG-2] Inbox-to-gold-graph conversion".
Report:
- Architectural recommendation (A or B) with reasoning
- Commit SHA
- Test count (new tests + full suite on main)
- Coverage delta
- End-to-end smoke test output showing the chain works
- Any concerns surfaced by the refactor

STOP conditions (report, don't fix):
- If PersonEntity / ProjectEntity refactor breaks more than 2
  existing tests in non-trivial ways
- If the inbox and gold_graph disagree on what a "person" or
  "project" means in any substantive way
- If Option A requires a circular import between entities and any
  other module

## Priority

MEDIUM. Phase 2 harness integration cannot start until this
resolves. But Phase 3 can be discussed in parallel.
