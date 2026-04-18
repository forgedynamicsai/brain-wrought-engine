"""Fixture generation: seeded synthetic brain vault generation.

Determinism class: SEEDED-STOCHASTIC — same seed produces identical brains.

BW-001: clean-schema fixture generator (Phase 1).
BW-014: dirty-schema fixture generator (Phase 2).
"""

from brain_wrought_engine.fixtures.generator import generate_brain
from brain_wrought_engine.fixtures.validator import validate_brain

__all__ = ["generate_brain", "validate_brain"]
