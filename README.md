# brain-wrought-engine

Deterministic scoring code for the Brain-Wrought personal-brain benchmark.

## What this is

All scoring math. No LLM-in-the-loop except where unavoidable (judge panel for Axis C). Everything else is deterministic Python with seeded randomness.

### Modules

- **`retrieval/`** — P@k, Recall@k, MRR, nDCG@k, personalization weighting, temporal qrel evaluation, abstention scoring
- **`ingestion/`** — entity recall, backlink F1, citation accuracy, schema completeness, setup friction
- **`assistant/`** — judge panel orchestration via LiteLLM (Sonnet 4.6 + Opus 4.7 + GPT-5.4), bootstrap confidence intervals
- **`fixtures/`** — seeded fixture generation, randomization
- **`leaderboard/`** — composite score aggregation

## What this is NOT

- No CLI (that's [`brain-wrought-harness`](https://github.com/forgedynamicsai/brain-wrought-harness))
- No markdown skills or docs (those are [`brain-wrought-skills`](https://github.com/forgedynamicsai/brain-wrought-skills))
- No qrels, gold graphs, or actual judge rubrics (sealed private repo, fetched at eval time via CI)

## Determinism classes

Every function is classified in its docstring as one of:

- **Fully deterministic** — bit-identical output for the same input (IEEE 754 caveats)
- **Seeded-stochastic** — identical output given the same seed
- **Bounded-stochastic** — reruns fall within declared confidence interval

CI enforces these claims.

## Standards

- Python 3.12.3 (pinned)
- Pydantic v2 for all data contracts
- pytest + pytest-randomly + hypothesis for tests
- mypy strict
- ruff format + lint (line length 100)
- 100% coverage on scoring modules

## Design rules

1. No use of global random state (`random.random()` is banned; use `random.Random(seed)`)
2. No direct LLM SDK calls — always via LiteLLM
3. Every function crossing a module boundary has a Pydantic contract on I/O
4. No side effects in scoring functions (pure functions; any logging happens in the caller)

See [CLAUDE.md](./CLAUDE.md) for the full coding standard.

## Installation

```bash
pip install brain-wrought-engine
```

## Programmatic use

```python
from brain_wrought_engine.retrieval import precision_at_k, ndcg_at_k

p10 = precision_at_k(relevant={"a", "b", "c"}, retrieved=["a", "x", "b", "y", "c"], k=10)
```

## License

MIT.
