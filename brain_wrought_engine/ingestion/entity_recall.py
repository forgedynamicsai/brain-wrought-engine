"""Entity recall scorer for the ingestion axis (BW-009).

Measures what fraction of gold entities a submission's brain has captured.

Scoring formula:
    recall = |{gold_entities ∩ submission_entities}| / |gold_entities|

where a gold entity is considered "present" in the submission if the
submission contains a note whose stem matches ``slug(entity.title)``.
Both sides are slugified via ``text_utils.slug`` before comparison, so
the match is normalised (slug-canonical, not raw case-fold).

Score range: [0.0, 1.0].
Determinism class: FULLY_DETERMINISTIC — pure function of inputs.
"""

from __future__ import annotations

from pydantic import BaseModel

from brain_wrought_engine.fixtures.gold_graph import GoldGraph
from brain_wrought_engine.text_utils import slug


class EntityRecallInput(BaseModel):
    """Input contract for the entity recall scorer."""

    gold_graph: GoldGraph
    submission_note_ids: frozenset[str]  # stems of notes in submission's brain

    model_config = {"frozen": True}


def score_entity_recall(input: EntityRecallInput) -> float:  # noqa: A002
    """Return [0.0, 1.0] fraction of gold entities present in the submission.

    Parameters
    ----------
    input:
        Gold graph and the set of note stems the submission produced.

    Returns
    -------
    float
        Recall in [0.0, 1.0].

    Raises
    ------
    ValueError
        If ``gold_graph`` contains no nodes (denominator is undefined).
    """
    if not input.gold_graph.nodes:
        raise ValueError("gold_graph has no nodes — recall denominator is undefined")

    if not input.submission_note_ids:
        return 0.0

    gold_slugs: frozenset[str] = frozenset(
        slug(node.title) for node in input.gold_graph.nodes.values()
    )
    matched = gold_slugs & input.submission_note_ids
    return len(matched) / len(gold_slugs)
