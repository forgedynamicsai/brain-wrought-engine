"""Composite score aggregation for the leaderboard.

Composite = 0.35 * retrieval + 0.35 * ingestion + 0.30 * assistant
See ADR-001 for weighting rationale.

Determinism class: FULLY DETERMINISTIC.
"""
