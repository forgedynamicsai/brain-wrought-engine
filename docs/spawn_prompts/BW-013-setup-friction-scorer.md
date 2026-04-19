BW-013: Setup friction scorer for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-013-setup-friction-scorer (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 2 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 of BrainWrought evaluates the INGESTION axis across
multiple sub-metrics. BW-013 is the simplest: "setup friction" —
how much human effort was required to get the submission system
to a state where it could start ingesting?

The metric captures a real differentiator among personal-brain
systems. Some require zero config; others need API keys, schema
definitions, prompt-engineered setup instructions, multi-step
CLI wizards. A benchmark should reward systems that minimize
required human intervention.

## Definition of setup friction

A submission reports its setup friction as part of its ingestion
response (per SUBMISSION_PROTOCOL.md §3.1 ingest mode):

    {
      "status": "ok",
      "entities_extracted": 47,
      ...
      "setup_prompts_required": 3,
      "setup_commands_required": 2,
      ...
    }

BW-013 scores this into a normalized friction metric:

    friction_score = 1.0 / (1.0 + 0.2 * prompts + 0.3 * commands)

Lower raw counts → higher score. Score range: (0, 1].
- 0 prompts, 0 commands → 1.0 (frictionless)
- 3 prompts, 2 commands → 1 / (1 + 0.6 + 0.6) = 0.455
- 10 prompts, 10 commands → 1 / (1 + 2.0 + 3.0) = 0.167

Rationale for weights: commands are slightly costlier to humans
than prompts (commands require correct syntax; prompts are more
forgiving natural language). Both are roughly log-scale
annoyances.

## Acceptance criteria

- [ ] `brain_wrought_engine.ingestion.scorers.friction` module
      with a public function:

          score_friction(
              *, setup_prompts_required: int,
              setup_commands_required: int,
          ) -> float

- [ ] Pydantic model for the input contract (matches
      SUBMISSION_PROTOCOL.md §3.1):

          class FrictionInput(BaseModel):
              setup_prompts_required: int = Field(ge=0)
              setup_commands_required: int = Field(ge=0)
              model_config = {"frozen": True}

- [ ] Output: float in (0, 1]
- [ ] Fully deterministic (no randomness, no external calls)
- [ ] Docstring with formula
- [ ] Unit tests:
      1. Zero friction → 1.0 exactly
      2. Reference case (3 prompts, 2 commands) → 0.4545... ± 1e-9
      3. Monotonicity: more prompts → lower score; more commands
         → lower score
      4. Bounded: any non-negative inputs → (0, 1]
      5. Input validation: negative values raise ValidationError
- [ ] Property tests (hypothesis):
      - For any non-negative (p, c), 0 < score_friction(p, c) <= 1
      - score_friction(p, c) > score_friction(p+1, c)
      - score_friction(p, c) > score_friction(p, c+1)
- [ ] mypy strict passes
- [ ] ruff clean
- [ ] 100% test coverage on the module

## Files to create

- brain_wrought_engine/ingestion/__init__.py
- brain_wrought_engine/ingestion/scorers/__init__.py
- brain_wrought_engine/ingestion/scorers/friction.py
- tests/ingestion/scorers/test_friction.py

## Out of scope

- Do NOT extract setup counts from submission responses. That's
  orchestration-layer work (harness repo) and will come in a
  later issue.
- Do NOT score other ingestion metrics. Entity recall (BW-009),
  backlink F1 (BW-010), etc. are separate issues.
- Do NOT hard-code the weights 0.2 and 0.3 in ways that make
  them hard to adjust later. Put them as module-level constants:

      _PROMPT_PENALTY_WEIGHT = 0.2
      _COMMAND_PENALTY_WEIGHT = 0.3

## Dependencies

No new dependencies. Stdlib + pydantic + hypothesis (all pinned).

## Deliverable

Open PR titled "[BW-013] Setup friction scorer" against main.
Report:
- Commit SHA
- Test count
- Coverage percentage
- Any concerns about the weighting formula (it's a first-pass
  choice; if it produces strange behavior in the test cases,
  flag it)

STOP conditions (report, don't fix):
- If the formula produces values outside (0, 1] for any legal
  input combination
- If there's a structural reason this belongs in the harness
  repo instead of engine (scoring is engine; extraction is harness)
