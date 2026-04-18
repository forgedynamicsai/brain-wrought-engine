"""Setup friction scorer for the ingestion axis.

Measures how much manual effort a user needed to configure an ingestion
system. Lower friction → higher score. Score is in [0.0, 1.0].

Scoring formula:
    friction_actions = len(commands) + len(prompts) + len(config_files)
    score = clamp(1.0 - friction_actions / 20.0, 0.0, 1.0)

The denominator 20 is calibrated for v1; adjust in v1.1 based on
observed submission distributions. auto_detected entries are free —
they represent work the system did itself and do not penalize the score.

Determinism class: FULLY_DETERMINISTIC — pure function of input.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SetupBlock(BaseModel):
    """The `setup:` block from submission.yaml."""

    commands: list[str] = Field(default_factory=list)
    prompts: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    auto_detected: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


_MAX_FRICTION_ACTIONS: int = 20


def score_setup_friction(setup: SetupBlock) -> float:
    """Score the setup friction for an ingestion submission.

    Parameters
    ----------
    setup:
        The setup block from the submission's configuration.

    Returns
    -------
    float
        Friction score in [0.0, 1.0]. 1.0 = zero friction (fully automatic);
        0.0 = maximum friction (20+ manual actions required).
    """
    friction_actions = len(setup.commands) + len(setup.prompts) + len(setup.config_files)
    raw = 1.0 - friction_actions / _MAX_FRICTION_ACTIONS
    return max(0.0, min(1.0, raw))
