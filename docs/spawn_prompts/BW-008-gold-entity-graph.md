BW-008: Gold entity graph generator for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-008-gold-entity-graph (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 3-4 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 of BrainWrought evaluates the INGESTION axis: can an agent
turn raw inbox content into a well-structured personal brain?

BW-008 creates the GROUND TRUTH side of that evaluation: a
deterministic gold entity graph generator that produces the
reference answer describing what entities and relationships SHOULD
exist in a correctly-ingested brain.

Submissions will be scored (in BW-009, BW-010) by comparing their
extracted entity/backlink graphs against this gold graph.

This is a fixture generator, not a scorer. It produces the gold
artifacts that scorers will compare against.

## Relationship to BW-007 (running in parallel)

BW-007 generates synthetic inboxes with a metadata.json inventory
listing every mentioned entity per artifact.

BW-008 does NOT depend on BW-007's output existing yet, because
both generators draw from the same canonical entity pool in
brain_wrought_engine.fixtures.generator.

BW-008 produces an independently-derivable gold graph based on the
same seed + entity pool, such that if BW-007 generates an inbox
with seed=42, BW-008 can generate the corresponding gold graph
with seed=42 and the two will describe the same entity universe.

## Required output structure

The generator produces gold artifacts:

    gold_<seed>/
    ├── entities.json           (canonical entity list with types,
    │                            attributes, and IDs)
    ├── backlinks.json          (expected graph edges: every pair
    │                            of entities that SHOULD have a
    │                            backlink between them)
    ├── timeline.json           (temporal events per entity)
    ├── citations.json          (for each inbox artifact, which
    │                            entities should be cited, and from
    │                            which source)
    └── schema_expectations.json (per-entity-type, what frontmatter
                                  fields should exist in a correctly
                                  ingested brain page)

## Acceptance criteria

- [ ] `python -m brain_wrought_engine.fixtures.gold_graph.generate
       --seed 42 --out /tmp/test_gold/` produces one gold directory
      named `gold_42/`
- [ ] entities.json contains the subset of the canonical entity
      pool that WOULD be present in a seed-42 inbox (same entity
      selection logic as BW-007). Schema:
      [{id, name, type (person|company|project|concept),
        aliases[], canonical_tags[]}]
- [ ] backlinks.json encodes the expected bidirectional graph:
      [{source_id, target_id, relationship_type}]
      Relationship types: "mentioned_in", "collaborated_with",
      "part_of", "reports_to", "attended"
- [ ] timeline.json describes canonical dates per entity:
      [{entity_id, event_type, timestamp, source_artifact_ref}]
- [ ] citations.json describes expected source attribution:
      {artifact_filename: [entity_id, ...]}
- [ ] schema_expectations.json defines required frontmatter fields
      per entity type:
      {person: [type, created, updated, tags, entities, state],
       company: [type, created, updated, tags, entities],
       project: [type, created, updated, tags, entities,
                 exec_summary, state]}
- [ ] Generation is fully deterministic: same seed → bit-identical
      JSON output (sort keys alphabetically, use stable entity ID
      generation from canonical pool)
- [ ] No LLM calls. This is pure Python graph construction from
      the deterministic seed + canonical entity pool.
- [ ] Unit tests for determinism
- [ ] Unit tests for graph validity (no self-loops, no duplicate
      edges, every referenced entity_id exists in entities.json)
- [ ] Integration test: generate one gold graph, validate all four
      JSON files parse and pass schema validation

## Technical notes

- Entity selection: use rng.sample() seeded from the input seed
  to pick 30-50 entities from the canonical pool per gold graph.
  This matches BW-007's likely entity density per inbox.
- Entity IDs: slug-based, matching the convention in
  brain_wrought_engine.text_utils.slug() already in use.
- Backlink generation: for each pair of selected entities,
  deterministically decide whether they should be connected based
  on hash(sorted_pair + seed). Density target: ~15% connectivity
  (realistic for a personal brain, not sparse, not dense).
- Timeline events: 2-5 events per entity, anchored to the same
  2026-04-01 reference date as BW-007 for temporal alignment.
- Citations: assume ~60% of inbox artifacts cite 2-4 entities each.
  Don't require BW-007's output to exist; generate placeholder
  filenames following BW-007's naming convention (we'll align in
  BW-009 integration testing).
- All JSON output: sorted keys, 2-space indent, trailing newline.

## Files to create

- brain_wrought_engine/fixtures/gold_graph/__init__.py
- brain_wrought_engine/fixtures/gold_graph/generate.py
- brain_wrought_engine/fixtures/gold_graph/entities.py
- brain_wrought_engine/fixtures/gold_graph/backlinks.py
- brain_wrought_engine/fixtures/gold_graph/timeline.py
- brain_wrought_engine/fixtures/gold_graph/citations.py
- brain_wrought_engine/fixtures/gold_graph/schema.py
- brain_wrought_engine/fixtures/gold_graph/models.py (pydantic
  models for all five JSON schemas)
- tests/fixtures/gold_graph/test_determinism.py
- tests/fixtures/gold_graph/test_graph_validity.py
- tests/fixtures/gold_graph/test_integration.py

## Out of scope

- Do NOT create the inbox content. That's BW-007 running in
  parallel.
- Do NOT create scorers. Entity recall (BW-009) and backlink F1
  (BW-010) are separate issues running after this one merges.
- Do NOT modify the canonical entity pool in
  brain_wrought_engine.fixtures.generator. Use it as-is.

## Dependencies

No new dependencies. Use only stdlib + pydantic (already pinned).

## Deliverable

Open PR titled "[BW-008] Gold entity graph generator" against main.
Report:
- Commit SHA
- Test count
- Sample gold graph statistics (entities, edges, timeline events)
  for seeds 42 and 7
- Any architectural concerns

STOP conditions (report, don't fix):
- If deterministic reproducibility can't be verified
- If entity pool import creates circular dependencies
- If any architectural tension with BW-007's parallel work (they
  share the entity pool; if a coordination issue appears, flag it)
