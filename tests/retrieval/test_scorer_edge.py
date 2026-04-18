"""Edge case tests for brain_wrought_engine.retrieval.scorer.

Covers: empty retrieved, empty relevant, k > len(retrieved), ties in ranking
(determinism via lexicographic sort is the caller's responsibility — scorer
operates on already-sorted tuples).

BW-003
"""

from __future__ import annotations

import math

from brain_wrought_engine.retrieval.scorer import (
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

# ---------------------------------------------------------------------------
# Empty retrieved
# ---------------------------------------------------------------------------


class TestEmptyRetrieved:
    def test_precision_empty_retrieved(self) -> None:
        """Empty retrieved list: 0 hits / k = 0.0."""
        assert precision_at_k(frozenset({"a", "b"}), (), 3) == 0.0

    def test_recall_empty_retrieved(self) -> None:
        """Empty retrieved list: 0 hits / |relevant| = 0.0."""
        assert recall_at_k(frozenset({"a", "b"}), (), 3) == 0.0

    def test_mrr_empty_retrieved(self) -> None:
        """No items retrieved → MRR = 0.0."""
        assert mrr(frozenset({"a"}), ()) == 0.0

    def test_ndcg_empty_retrieved_with_relevant(self) -> None:
        """No items retrieved but relevant set non-empty → nDCG = 0.0."""
        assert ndcg_at_k(frozenset({"a"}), (), 3) == 0.0


# ---------------------------------------------------------------------------
# Empty relevant
# ---------------------------------------------------------------------------


class TestEmptyRelevant:
    def test_precision_empty_relevant(self) -> None:
        """No relevant docs: 0 hits / k = 0.0."""
        assert precision_at_k(frozenset(), ("a", "b", "c"), 3) == 0.0

    def test_recall_empty_relevant(self) -> None:
        """recall_at_k returns 0.0 when relevant is empty (avoids division by zero)."""
        assert recall_at_k(frozenset(), ("a", "b", "c"), 3) == 0.0

    def test_mrr_empty_relevant(self) -> None:
        """No relevant docs → MRR = 0.0."""
        assert mrr(frozenset(), ("a", "b", "c")) == 0.0

    def test_ndcg_empty_relevant(self) -> None:
        """Vacuously perfect score when no relevant items exist."""
        assert ndcg_at_k(frozenset(), ("a", "b", "c"), 3) == 1.0


# ---------------------------------------------------------------------------
# k larger than retrieved length
# ---------------------------------------------------------------------------


class TestKLargerThanRetrieved:
    def test_precision_k_larger(self) -> None:
        """k=10, only 3 docs retrieved, 2 relevant → P = 2/10."""
        assert math.isclose(
            precision_at_k(frozenset({"a", "b"}), ("a", "b", "c"), 10),
            2 / 10,
        )

    def test_recall_k_larger(self) -> None:
        """k=10, all relevant docs retrieved → Recall = 1.0."""
        assert recall_at_k(frozenset({"a", "b"}), ("a", "b", "c"), 10) == 1.0

    def test_recall_k_larger_partial(self) -> None:
        """k=10, 1 of 3 relevant docs retrieved → Recall = 1/3."""
        assert math.isclose(
            recall_at_k(frozenset({"a", "b", "c"}), ("a", "x", "y"), 10),
            1 / 3,
        )

    def test_ndcg_k_larger(self) -> None:
        """k > len(retrieved): only actually-retrieved positions contribute to DCG."""
        # relevant={a,b}, retrieved=(a,), k=5
        # DCG = 1/log2(2); IDCG = 1/log2(2) + 1/log2(3)  (ideal has 2 hits)
        score = ndcg_at_k(frozenset({"a", "b"}), ("a",), 5)
        dcg = 1.0 / math.log2(2)
        idcg = 1.0 / math.log2(2) + 1.0 / math.log2(3)
        assert math.isclose(score, dcg / idcg)


# ---------------------------------------------------------------------------
# Ties / determinism
# ---------------------------------------------------------------------------


class TestTiesAndDeterminism:
    """Scorer operates on caller-provided ordered tuples.

    Tie-breaking by lexicographic sort happens before calling the scorer.
    The scorer itself is deterministic given the same tuple order.
    """

    def test_same_inputs_same_output_precision(self) -> None:
        rel = frozenset({"alpha", "beta", "gamma"})
        ret = ("alpha", "delta", "beta", "epsilon", "gamma")
        assert precision_at_k(rel, ret, 3) == precision_at_k(rel, ret, 3)

    def test_same_inputs_same_output_ndcg(self) -> None:
        rel = frozenset({"alpha", "beta"})
        ret = ("beta", "alpha", "gamma")
        score_a = ndcg_at_k(rel, ret, 2)
        score_b = ndcg_at_k(rel, ret, 2)
        assert score_a == score_b

    def test_order_matters_for_ndcg(self) -> None:
        """Two orderings of the same set of docs yield different nDCG scores."""
        rel = frozenset({"a", "b"})
        perfect = ("a", "b", "c")
        imperfect = ("c", "a", "b")
        assert ndcg_at_k(rel, perfect, 3) > ndcg_at_k(rel, imperfect, 3)

    def test_order_matters_for_mrr(self) -> None:
        """Relevant item at rank 1 vs rank 3 gives different MRR."""
        rel = frozenset({"a"})
        assert mrr(rel, ("a", "b", "c")) > mrr(rel, ("c", "b", "a"))

    def test_duplicate_ids_in_retrieved(self) -> None:
        """Duplicates in retrieved are each evaluated independently at their rank."""
        # "a" appears twice; second occurrence also counts as a hit
        # relevant={a}, retrieved=(a, a, b), k=2 → 2 hits / 2 = 1.0
        rel = frozenset({"a"})
        ret = ("a", "a", "b")
        assert precision_at_k(rel, ret, 2) == 1.0

    def test_ndcg_single_relevant_various_k(self) -> None:
        """nDCG with a single relevant item placed at increasing ranks."""
        rel = frozenset({"a"})
        for rank in range(1, 6):
            ret = tuple(["x"] * (rank - 1) + ["a"] + ["y"])
            score = ndcg_at_k(rel, ret, rank + 1)
            # DCG = 1/log2(rank+1); IDCG = 1/log2(2)
            expected = (1.0 / math.log2(rank + 1)) / (1.0 / math.log2(2))
            assert math.isclose(score, expected), f"rank={rank}: {score} != {expected}"
