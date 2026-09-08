# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import (
    RegionMergeCandidate,
    RegionMergeMetrics,
)
from pbn.regions import RegionMergeCandidateRanker
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator


def _metrics(
    *,
    color_difference: float,
) -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=color_difference,
        source_area=1,
        target_area=3,
        merged_area=4,
        affected_area_ratio=0.25,
        shared_border_length=2,
        source_perimeter=4,
        target_perimeter=8,
        merged_perimeter=8,
    )


def _base_calculator() -> RegionMergeCostCalculator:
    """
    Return the weighting this file's assertions are written against.

    The expected cost values below were hand-computed from these weights.
    They are the test's own choice, stated here rather than left to the
    calculator, which no longer supplies a weighting of its own.
    """
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.20,
        border_weight=0.20,
        geometry_weight=0.20,
    )


def test_rank_orders_candidates_by_merge_cost() -> None:
    expensive_candidate = RegionMergeCandidate(
        source_id=1,
        target_id=2,
    )
    cheap_candidate = RegionMergeCandidate(
        source_id=2,
        target_id=1,
    )

    ranked = RegionMergeCandidateRanker(
        _base_calculator(),
    ).rank(
        (
            (
                expensive_candidate,
                _metrics(
                    color_difference=20.0,
                ),
            ),
            (
                cheap_candidate,
                _metrics(
                    color_difference=0.0,
                ),
            ),
        ),
    )

    assert tuple(candidate for candidate, _, _ in ranked) == (
        cheap_candidate,
        expensive_candidate,
    )

    assert ranked[0][2].value < ranked[1][2].value


def test_rank_calculates_cost_for_every_candidate() -> None:
    candidate = RegionMergeCandidate(
        source_id=1,
        target_id=2,
    )
    metrics = _metrics(
        color_difference=10.0,
    )

    ranked = RegionMergeCandidateRanker(
        _base_calculator(),
    ).rank(
        (
            (
                candidate,
                metrics,
            ),
        ),
    )

    ranked_candidate, ranked_metrics, cost = ranked[0]

    assert ranked_candidate == candidate
    assert ranked_metrics == metrics
    assert cost.color_penalty == 0.5
    assert cost.affected_area_penalty == 0.25
    assert cost.border_penalty == 0.5
    assert cost.geometry_penalty == 0.0
    assert cost.value == 0.35


def test_equal_cost_candidates_use_source_then_target_id() -> None:
    metrics = _metrics(
        color_difference=0.0,
    )

    ranked = RegionMergeCandidateRanker(
        _base_calculator(),
    ).rank(
        (
            (
                RegionMergeCandidate(
                    source_id=2,
                    target_id=1,
                ),
                metrics,
            ),
            (
                RegionMergeCandidate(
                    source_id=1,
                    target_id=3,
                ),
                metrics,
            ),
            (
                RegionMergeCandidate(
                    source_id=1,
                    target_id=2,
                ),
                metrics,
            ),
        ),
    )

    assert tuple(candidate for candidate, _, _ in ranked) == (
        RegionMergeCandidate(
            source_id=1,
            target_id=2,
        ),
        RegionMergeCandidate(
            source_id=1,
            target_id=3,
        ),
        RegionMergeCandidate(
            source_id=2,
            target_id=1,
        ),
    )


def test_equal_cost_order_is_independent_from_input_order() -> None:
    metrics = _metrics(
        color_difference=0.0,
    )

    first = (
        RegionMergeCandidate(
            source_id=1,
            target_id=2,
        ),
        metrics,
    )
    second = (
        RegionMergeCandidate(
            source_id=2,
            target_id=1,
        ),
        metrics,
    )

    ranker = RegionMergeCandidateRanker(
        _base_calculator(),
    )

    assert ranker.rank(
        (
            first,
            second,
        ),
    ) == ranker.rank(
        (
            second,
            first,
        ),
    )


def test_rank_returns_empty_result_for_no_candidates() -> None:
    assert (
        RegionMergeCandidateRanker(
            _base_calculator(),
        ).rank(())
        == ()
    )
