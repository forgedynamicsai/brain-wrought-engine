"""Pydantic v2 data models for the retrieval axis.

Determinism class: FULLY_DETERMINISTIC — models are pure data containers.

BW-003: scorer input/output models.
BW-002: qrel entry and set models.
"""

from __future__ import annotations

from typing import Literal

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
    def _clamp_check(self) -> ScoreOutput:
        """Sanity guard: score must be in [0, 1]."""
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")
        return self


class QrelEntry(BaseModel):
    """A single query with its relevant note IDs.

    query_type discriminates the query class:
      - "factual": entity/project-centric factual questions
      - "temporal": time-scoped questions (meetings, changes, dates)
      - "personalization": first-person recall queries
      - "abstention": query about something NOT in the vault; must have
        relevant_note_ids=frozenset() and expected_abstain=True
    """

    query_id: str
    query_text: str
    relevant_note_ids: frozenset[str]
    query_type: Literal["factual", "temporal", "personalization", "abstention"]
    expected_abstain: bool = False

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _validate_abstention_invariants(self) -> QrelEntry:
        """Enforce cross-field constraints for abstention vs. non-abstention queries."""
        if self.query_type == "abstention":
            if self.relevant_note_ids != frozenset():
                raise ValueError(
                    "abstention queries must have relevant_note_ids=frozenset(), "
                    f"got {self.relevant_note_ids!r}"
                )
            if not self.expected_abstain:
                raise ValueError(
                    "abstention queries must have expected_abstain=True"
                )
        else:
            if self.expected_abstain:
                raise ValueError(
                    f"non-abstention query (type={self.query_type!r}) "
                    "must have expected_abstain=False"
                )
        return self


class QrelSet(BaseModel):
    """A complete set of query-relevance judgments for one brain vault."""

    qrel_version: str = "v1"
    seed: int
    entries: tuple[QrelEntry, ...]

    model_config = {"frozen": True}
