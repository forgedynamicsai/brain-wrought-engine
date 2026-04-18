"""Pydantic v2 input/output models for retrieval scoring.

Determinism class: FULLY_DETERMINISTIC

BW-003
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RetrievalInput(BaseModel):
    """Shared validated input for ranked-retrieval metrics that take k."""

    relevant: frozenset[str] = Field(description="Set of relevant document IDs.")
    retrieved: tuple[str, ...] = Field(description="Ordered list of retrieved document IDs.")
    k: int = Field(ge=1, description="Cut-off depth (must be >= 1).")

    model_config = {"frozen": True}


class RetrievalInputNoK(BaseModel):
    """Validated input for metrics that do not use k (e.g. MRR)."""

    relevant: frozenset[str] = Field(description="Set of relevant document IDs.")
    retrieved: tuple[str, ...] = Field(description="Ordered list of retrieved document IDs.")

    model_config = {"frozen": True}


class ScoreOutput(BaseModel):
    """Single floating-point metric score in [0.0, 1.0]."""

    score: float = Field(ge=0.0, le=1.0, description="Metric value in [0.0, 1.0].")

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _clamp_check(self) -> "ScoreOutput":
        """Sanity guard: score must be in [0, 1]."""
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")
        return self
