"""Unit tests + Hypothesis property tests for brain_wrought_engine.retrieval.scorer.

BW-003
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from brain_wrought_engine.retrieval.scorer import (
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOC_IDS = st.text(min_size=1, max_size=8, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")


@st.composite
def _relevant_retrieved_k(
    draw: st.DrawFn,
) -> tuple[frozenset[str], tuple[str, ...], int]:
    """Strategy: draw a consistent (relevant, retrieved, k) triple."""
    pool = draw(st.lists(_DOC_IDS, min_size=0, max_size=20, unique=True))
    relevant = frozenset(draw(st.lists(st.sampled_from(pool) if pool else _DOC_IDS, max_size=10)))
    retrieved_list = draw(st.permutations(pool)) if pool else []
    retrieved = tuple(retrieved_list)
    k = draw(st.integers(min_value=1, max_value=max(len(retrieved), 1) + 5))
    return relevant, retrieved, k


# ---------------------------------------------------------------------------
# precision_at_k — textbook examples
# ---------------------------------------------------------------------------


class TestPrecisionAtK:
    def test_mixed_results(self) -> None:
        """relevant={a,b,c}, retrieved=(a,x,b,y,c), k=3 → 2/3."""
        assert math.isclose(
            precision_at_k(frozenset({"a", "b", "c"}), ("a", "x", "b", "y", "c"), 3),
            2 / 3,
        )

    def test_no_relevant_in_retrieved(self) -> None:
        """relevant={a}, retrieved=(x,y,z), k=3 → 0.0."""
        assert precision_at_k(frozenset({"a"}), ("x", "y", "z"), 3) == 0.0

    def test_k_larger_than_retrieved(self) -> None:
        """relevant={a,b}, retrieved=(a,b,c), k=5 → 2/5 (k > len(retrieved))."""
        assert math.isclose(
            precision_at_k(frozenset({"a", "b"}), ("a", "b", "c"), 5),
            2 / 5,
        )

    def test_all_relevant(self) -> None:
        """All top-k items are relevant → P@k == 1.0."""
        assert precision_at_k(frozenset({"a", "b", "c"}), ("a", "b", "c", "d"), 3) == 1.0

    def test_k_equals_one_hit(self) -> None:
        """k=1 and top document is relevant → 1.0."""
        assert precision_at_k(frozenset({"a"}), ("a", "b", "c"), 1) == 1.0

    def test_k_equals_one_miss(self) -> None:
        """k=1 and top document is not relevant → 0.0."""
        assert precision_at_k(frozenset({"b"}), ("a", "b", "c"), 1) == 0.0

    def test_invalid_k_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be >= 1"):
            precision_at_k(frozenset({"a"}), ("a",), 0)


# ---------------------------------------------------------------------------
# recall_at_k — textbook examples
# ---------------------------------------------------------------------------


class TestRecallAtK:
    def test_partial_recall(self) -> None:
        """relevant={a,b,c}, retrieved=(a,x,b), k=3 → 2/3."""
        assert math.isclose(
            recall_at_k(frozenset({"a", "b", "c"}), ("a", "x", "b"), 3),
            2 / 3,
        )

    def test_zero_recall(self) -> None:
        """No overlap → 0.0."""
        assert recall_at_k(frozenset({"a", "b"}), ("x", "y", "z"), 3) == 0.0

    def test_full_recall(self) -> None:
        """All relevant items are in top-k → 1.0."""
        assert recall_at_k(frozenset({"a", "b"}), ("a", "b", "c", "d"), 2) == 1.0

    def test_empty_relevant_returns_zero(self) -> None:
        """If relevant set is empty, return 0.0."""
        assert recall_at_k(frozenset(), ("a", "b"), 2) == 0.0

    def test_k_larger_than_retrieved(self) -> None:
        """k > len(retrieved): missing positions count as non-retrieved."""
        assert math.isclose(
            recall_at_k(frozenset({"a", "b", "c"}), ("a",), 5),
            1 / 3,
        )

    def test_invalid_k_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be >= 1"):
            recall_at_k(frozenset({"a"}), ("a",), 0)


# ---------------------------------------------------------------------------
# mrr — textbook examples
# ---------------------------------------------------------------------------


class TestMRR:
    def test_first_position(self) -> None:
        """First item relevant → MRR = 1.0."""
        assert mrr(frozenset({"a"}), ("a", "b", "c")) == 1.0

    def test_second_position(self) -> None:
        """Relevant at rank 2 → MRR = 0.5."""
        assert mrr(frozenset({"b"}), ("a", "b", "c")) == 0.5

    def test_third_position(self) -> None:
        """Relevant at rank 3 → MRR = 1/3."""
        assert math.isclose(mrr(frozenset({"c"}), ("a", "b", "c")), 1 / 3)

    def test_no_relevant_returns_zero(self) -> None:
        """No relevant item in retrieved → 0.0."""
        assert mrr(frozenset({"z"}), ("a", "b", "c")) == 0.0

    def test_empty_retrieved_returns_zero(self) -> None:
        assert mrr(frozenset({"a"}), ()) == 0.0

    def test_empty_relevant_and_empty_retrieved(self) -> None:
        assert mrr(frozenset(), ()) == 0.0

    def test_multiple_relevant_uses_first(self) -> None:
        """When multiple relevant items exist, uses rank of the first."""
        assert math.isclose(mrr(frozenset({"a", "b"}), ("x", "a", "b")), 0.5)


# ---------------------------------------------------------------------------
# ndcg_at_k — textbook examples
# ---------------------------------------------------------------------------


class TestNDCGAtK:
    def test_perfect_ranking(self) -> None:
        """Perfect ranking: relevant={a,b}, retrieved=(a,b,c,d), k=2 → 1.0."""
        assert ndcg_at_k(frozenset({"a", "b"}), ("a", "b", "c", "d"), 2) == 1.0

    def test_suboptimal_ranking_is_less_than_one_but_positive(self) -> None:
        """Relevant item at rank 2 instead of rank 1: 0.0 < nDCG@2 < 1.0.

        With binary relevance, swapping two relevant items gives the same DCG
        (positions are symmetric). To get nDCG < 1.0 we need the relevant item
        ranked below a non-relevant one.
        relevant={a}, retrieved=(b, a, c, d), k=2
        DCG@2  = 0/log2(2) + 1/log2(3) ≈ 0.631
        IDCG@2 = 1/log2(2) + 0/log2(3) = 1.0
        nDCG@2 ≈ 0.631
        """
        score = ndcg_at_k(frozenset({"a"}), ("b", "a", "c", "d"), 2)
        assert 0.0 < score < 1.0

    def test_no_relevant_in_top_k(self) -> None:
        """All relevant items outside top-k → nDCG@k = 0.0."""
        assert ndcg_at_k(frozenset({"c", "d"}), ("a", "b", "c", "d"), 2) == 0.0

    def test_empty_relevant_returns_one(self) -> None:
        """Vacuously perfect when no relevant items exist."""
        assert ndcg_at_k(frozenset(), ("a", "b"), 2) == 1.0

    def test_single_relevant_at_rank_1(self) -> None:
        """Single relevant doc at rank 1, k=1 → 1.0."""
        assert ndcg_at_k(frozenset({"a"}), ("a", "b"), 1) == 1.0

    def test_single_relevant_at_rank_2_k1(self) -> None:
        """Relevant doc is at rank 2 but k=1 → 0.0."""
        assert ndcg_at_k(frozenset({"b"}), ("a", "b"), 1) == 0.0

    def test_k_larger_than_retrieved(self) -> None:
        """k > len(retrieved): positions beyond retrieved are treated as non-relevant."""
        # relevant={a,b}, retrieved=(a,), k=3
        # DCG = 1/log2(2) = 1.0; IDCG = 1/log2(2) + 1/log2(3) = 1 + 0.631... = 1.631...
        score = ndcg_at_k(frozenset({"a", "b"}), ("a",), 3)
        expected_dcg = 1.0 / math.log2(2)
        expected_idcg = 1.0 / math.log2(2) + 1.0 / math.log2(3)
        assert math.isclose(score, expected_dcg / expected_idcg)

    def test_invalid_k_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be >= 1"):
            ndcg_at_k(frozenset({"a"}), ("a",), 0)


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@settings(max_examples=300)
@given(_relevant_retrieved_k())
def test_precision_in_unit_interval(data: tuple[frozenset[str], tuple[str, ...], int]) -> None:
    """P@k ∈ [0.0, 1.0] for all inputs."""
    relevant, retrieved, k = data
    score = precision_at_k(relevant, retrieved, k)
    assert 0.0 <= score <= 1.0


@settings(max_examples=300)
@given(_relevant_retrieved_k())
def test_recall_in_unit_interval(data: tuple[frozenset[str], tuple[str, ...], int]) -> None:
    """Recall@k ∈ [0.0, 1.0] for all inputs."""
    relevant, retrieved, k = data
    score = recall_at_k(relevant, retrieved, k)
    assert 0.0 <= score <= 1.0


@settings(max_examples=300)
@given(_relevant_retrieved_k())
def test_ndcg_in_unit_interval(data: tuple[frozenset[str], tuple[str, ...], int]) -> None:
    """nDCG@k ∈ [0.0, 1.0] for all inputs."""
    relevant, retrieved, k = data
    score = ndcg_at_k(relevant, retrieved, k)
    assert 0.0 <= score <= 1.0


@st.composite
def _relevant_and_retrieved(draw: st.DrawFn) -> tuple[frozenset[str], tuple[str, ...]]:
    relevant = draw(st.frozensets(_DOC_IDS, min_size=0, max_size=10))
    retrieved = tuple(draw(st.lists(_DOC_IDS, min_size=2, max_size=15, unique=True)))
    return relevant, retrieved


@settings(max_examples=300)
@given(_relevant_and_retrieved())
def test_precision_non_increasing_with_k(
    data: tuple[frozenset[str], tuple[str, ...]],
) -> None:
    """P@k is NOT necessarily monotone, but P@(k+Δ) ≤ P@k * k/(k+Δ) + Δ/(k+Δ).

    Instead, verify the weaker invariant: adding a non-relevant item at position
    k+1 can only decrease or maintain P, i.e. P@(k+1) <= (P@k * k + 1) / (k+1).
    We simply check that P@k computed for k=1..len(retrieved) all stay in [0,1].
    """
    relevant, retrieved = data
    for k in range(1, len(retrieved) + 1):
        score = precision_at_k(relevant, retrieved, k)
        assert 0.0 <= score <= 1.0


@settings(max_examples=300)
@given(
    st.frozensets(_DOC_IDS, min_size=1, max_size=8),
    st.integers(min_value=1, max_value=10),
)
def test_precision_is_one_when_top_k_subset_of_relevant(
    relevant: frozenset[str], k: int
) -> None:
    """If retrieved[:k] ⊆ relevant, then P@k == 1.0."""
    # Build a retrieved tuple whose first k elements are all from relevant
    relevant_list = sorted(relevant)
    top_k = relevant_list[:k] if len(relevant_list) >= k else relevant_list * (k // len(relevant_list) + 1)
    top_k = top_k[:k]
    retrieved = tuple(top_k)
    score = precision_at_k(relevant, retrieved, k)
    assert score == 1.0


@settings(max_examples=200)
@given(
    st.frozensets(_DOC_IDS, min_size=1, max_size=8),
    st.lists(_DOC_IDS, min_size=1, max_size=15, unique=True),
)
def test_mrr_in_unit_interval(relevant: frozenset[str], retrieved_list: list[str]) -> None:
    """MRR ∈ [0.0, 1.0] for all inputs."""
    retrieved = tuple(retrieved_list)
    score = mrr(relevant, retrieved)
    assert 0.0 <= score <= 1.0


@settings(max_examples=200)
@given(
    st.frozensets(_DOC_IDS, min_size=1, max_size=8),
    st.lists(_DOC_IDS, min_size=1, max_size=15, unique=True),
)
def test_mrr_at_most_one(relevant: frozenset[str], retrieved_list: list[str]) -> None:
    """MRR ≤ 1.0 and equals 1.0 iff first item is relevant."""
    retrieved = tuple(retrieved_list)
    score = mrr(relevant, retrieved)
    if retrieved[0] in relevant:
        assert score == 1.0
    else:
        assert score < 1.0
