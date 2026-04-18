"""Ingestion axis scoring: entity recall, backlink F1, citation accuracy, schema completeness.

BW-009 through BW-013: implementation target for Phase 2.
"""

from brain_wrought_engine.ingestion.setup_friction import SetupBlock, score_setup_friction

__all__ = ["SetupBlock", "score_setup_friction"]
