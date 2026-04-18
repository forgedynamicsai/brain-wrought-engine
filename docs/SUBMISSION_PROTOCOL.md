# Submission Protocol

This document describes the `submission.yaml` schema and related conventions for
submitting systems to the Brain-Wrought benchmark.

---

## submission.yaml schema

A valid submission must include a `submission.yaml` file at the repo root. Required fields:

```yaml
submission_id: "my-system-v1"
version: "1.0.0"
axes:
  - retrieval
  - ingestion
seed: 42
```

**Fields:**
- `submission_id` — unique string identifier for this submission
- `version` — semantic version of the submitted system
- `axes` — list of axes the submission participates in (`retrieval`, `ingestion`, `assistant`)
- `seed` — integer random seed; must be fixed and committed

---

## Setup block (ingestion axis)

Submissions that participate in the **ingestion axis** must include a `setup:` block
in `submission.yaml`. This block declares the manual effort required to configure the
system. It is used by the setup-friction scorer (BW-013).

```yaml
setup:
  commands:
    - "pip install my-package"
    - "python configure.py"
  prompts:
    - "Enter your API key"
  config_files:
    - "my_config.yaml"
  auto_detected:
    - "vault_path"
    - "default_model"
```

**Fields:**
- `commands` — shell commands the user must run manually (each command = 1 friction unit)
- `prompts` — interactive prompts the user must answer (each prompt = 1 friction unit)
- `config_files` — config files the user must author (each file = 1 friction unit)
- `auto_detected` — config values the system derived automatically (**free** — do not add friction)

**Scoring:**
```
friction_score = clamp(1.0 - (commands + prompts + config_files) / 20.0, 0.0, 1.0)
```

The denominator 20 is the v1 calibration point. Submissions with zero manual actions
score 1.0; submissions requiring 20+ manual actions score 0.0.
