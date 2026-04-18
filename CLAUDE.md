# CLAUDE.md — Brain-Wrought

This file is loaded by Claude Code at the start of every session in this repo.

---

## Project

Brain-Wrought is an independent open benchmark for personal AI knowledge systems. Three axes: retrieval, ingestion, personalization. Sealed qrels. Reproducibility-first. Target: arxiv preprint on v1 launch (summer 2026); NeurIPS 2027 Evaluations & Datasets Track as formal academic venue.

## Your role in this session

You are a coding assistant. Priority order:
1. Correctness (the scorer has to produce the right number)
2. Reproducibility (deterministic where possible, seeded elsewhere)
3. Readability (other people will audit this code)
4. Performance (last — only when the above are solid)

## Architecture

Four repos:
- `brain-wrought-harness` (public) — pytest runner, submission CLI
- `brain-wrought-skills` (public) — markdown skills for fixture/query generation, public rubric scaffolds
- `brain-wrought-engine` (this repo) — deterministic scoring math
- `brain-wrought-sealed` (PRIVATE) — qrels, actual judge rubrics, gold graphs

## Coding standards

### Language + tooling
- Python 3.12.3 (pinned)
- uv or poetry for dependency management
- ruff for lint + format (line length 100)
- mypy strict mode
- pytest + pytest-randomly + pytest-cov
- pydantic v2 for all data contracts

### Determinism discipline

**Rule:** every stochastic operation must accept a seed parameter. No exceptions.

```python
# GOOD
def sample_fixtures(pool: list[Fixture], n: int, *, seed: int) -> list[Fixture]:
    rng = random.Random(seed)
    return rng.sample(pool, n)

# BAD
def sample_fixtures(pool: list[Fixture], n: int) -> list[Fixture]:
    return random.sample(pool, n)  # uses global state
```

### LLM calls through LiteLLM only

```python
from litellm import completion  # always this
# NOT: from anthropic import Anthropic  # direct SDK banned in engine code
```

### Seeded judge calls

```python
response = completion(
    model="claude-sonnet-4-6",
    temperature=0.1,
    max_tokens=1024,
    seed=submission_seed + judge_offset,
    messages=[...],
)
```

### Pydantic contracts on everything crossing boundaries

```python
class JudgeScore(BaseModel):
    rubric: Literal["identity", "stance", "novelty", "calibration"]
    score: int = Field(ge=1, le=5)
    evidence: list[str] = Field(min_length=1)
    rubric_version: str

    model_config = {"frozen": True}
```

### Testing

Every scorer has:
1. A unit test with a known input and expected output
2. A property test (hypothesis) for invariants
3. A "reference submission" integration test

### Error handling

Every error either:
1. Is caught and handled meaningfully, or
2. Propagates with enough context to debug

No silent `except Exception: pass`. Ever.

## Workflow

### Before making changes

1. Read the relevant ADR if the change is architectural
2. Check `docs/DECISIONS.md` for prior context
3. Run tests locally before committing: `uv run pytest`

### Commit discipline

- Small commits; one logical change per commit
- Conventional Commits format: `feat(retrieval): add temporal qrel scorer`
- Every commit passes CI; no "WIP" commits on main

### GitHub Issues

When working an issue (BW-001, BW-002, etc.):
1. Create a branch named `issue/BW-XXX-short-description`
2. Reference the issue in commit messages (`feat: add P@k scorer (BW-003)`)
3. Open PR when acceptance criteria are met

## What NOT to do

- ❌ Do NOT commit anything from `brain-wrought-sealed` to public repos
- ❌ Do NOT use `latest` or floating version constraints
- ❌ Do NOT call LLM APIs directly (always LiteLLM)
- ❌ Do NOT use global random state
- ❌ Do NOT add dependencies without updating the lock file
- ❌ Do NOT disable CI checks to merge
- ❌ Do NOT import from `brain-wrought-sealed` at import time

## Model routing

- **Opus 4.7** — architecture decisions, ADR drafting, rubric design
- **Sonnet 4.6** — default for build sessions (you are probably this)
- **Haiku 4.5 batch** — fixture generation at volume, entity extraction

## Key references

- `docs/PROJECT_CONTEXT.md` — what and why
- `docs/BUILD_PLAN.md` — timeline and phase gates
- `https://github.com/forgedynamicsai/brain-wrought-skills/tree/main/docs/` — ADR-001 through ADR-004
- `https://github.com/forgedynamicsai/brain-wrought-skills/blob/main/docs/REPRODUCIBILITY_SPEC.md`
- `https://github.com/forgedynamicsai/brain-wrought-skills/blob/main/SUBMISSION_PROTOCOL.md`
