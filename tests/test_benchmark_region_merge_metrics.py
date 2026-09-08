# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.models import (
    RegionMergeCandidate,
    RegionMergeMetrics,
)
from tools.benchmark_region_merge_metrics import (
    WeightingStrategy,
    evaluate_weighting_strategy,
    format_distribution,
    normalize_merge_metrics,
    summarize_merge_metrics,
    summarize_values,
)


def _metrics(
    *,
    color_difference: float,
    source_area: int,
    affected_area_ratio: float,
    shared_border_length: int,
    source_perimeter: int,
    target_perimeter: int,
    target_area: int,
    merged_area: int,
    merged_perimeter: int,
) -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=color_difference,
        source_area=source_area,
        target_area=target_area,
        merged_area=merged_area,
        affected_area_ratio=affected_area_ratio,
        shared_border_length=shared_border_length,
        source_perimeter=source_perimeter,
        target_perimeter=target_perimeter,
        merged_perimeter=merged_perimeter,
    )


def test_summarize_values_reports_distribution_percentiles() -> None:
    distribution = summarize_values(
        name="test",
        values=(
            0.0,
            10.0,
            20.0,
            30.0,
            40.0,
        ),
    )

    assert distribution.name == "test"
    assert distribution.count == 5
    assert distribution.minimum == 0.0
    assert distribution.percentile_05 == pytest.approx(
        2.0,
    )
    assert distribution.percentile_25 == pytest.approx(
        10.0,
    )
    assert distribution.median == pytest.approx(
        20.0,
    )
    assert distribution.percentile_75 == pytest.approx(
        30.0,
    )
    assert distribution.percentile_95 == pytest.approx(
        38.0,
    )
    assert distribution.maximum == 40.0


def test_summarize_values_rejects_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match="values must not be empty",
    ):
        summarize_values(
            name="test",
            values=(),
        )


def test_summarize_merge_metrics_preserves_metric_order() -> None:
    metrics = (
        _metrics(
            color_difference=5.0,
            source_area=2,
            affected_area_ratio=0.25,
            shared_border_length=1,
            source_perimeter=6,
            target_perimeter=8,
            target_area=6,
            merged_area=8,
            merged_perimeter=12,
        ),
        _metrics(
            color_difference=15.0,
            source_area=6,
            affected_area_ratio=0.5,
            shared_border_length=3,
            source_perimeter=10,
            target_perimeter=12,
            target_area=6,
            merged_area=12,
            merged_perimeter=16,
        ),
    )

    distributions = summarize_merge_metrics(
        metrics,
    )

    assert tuple(distribution.name for distribution in distributions) == (
        "color_difference",
        "source_area",
        "target_area",
        "merged_area",
        "affected_area_ratio",
        "shared_border_length",
        "source_shared_border_ratio",
        "target_shared_border_ratio",
        "source_geometry_complexity",
        "target_geometry_complexity",
        "merged_geometry_complexity",
        "geometry_change",
    )

    color_distribution = distributions[0]

    assert color_distribution.minimum == 5.0
    assert color_distribution.median == 10.0
    assert color_distribution.maximum == 15.0


def test_format_distribution_contains_scale_information() -> None:
    distribution = summarize_values(
        name="color_difference",
        values=(
            10.0,
            20.0,
            30.0,
        ),
    )

    assert format_distribution(
        distribution,
    ) == (
        "color_difference: "
        "count=3, "
        "min=10.000000, "
        "p05=11.000000, "
        "p25=15.000000, "
        "median=20.000000, "
        "p75=25.000000, "
        "p95=29.000000, "
        "max=30.000000"
    )


def test_normalize_merge_metrics_produces_bounded_components() -> None:
    metrics = _metrics(
        color_difference=20.0,
        source_area=2,
        affected_area_ratio=0.25,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=8,
        target_area=4,
        merged_area=8,
        merged_perimeter=12,
    )

    components = normalize_merge_metrics(
        metrics,
        color_scale=20.0,
    )

    assert components.color_penalty == pytest.approx(
        0.5,
    )
    assert components.affected_area_penalty == pytest.approx(
        0.25,
    )
    assert components.border_penalty == pytest.approx(
        0.75,
    )
    assert components.geometry_penalty == pytest.approx(
        2 / 18,
    )


def test_normalize_merge_metrics_does_not_penalize_geometry_improvement() -> None:
    metrics = _metrics(
        color_difference=10.0,
        source_area=4,
        affected_area_ratio=0.5,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=6,
        target_area=2,
        merged_area=6,
        merged_perimeter=10,
    )

    assert metrics.geometry_change < 0

    components = normalize_merge_metrics(
        metrics,
        color_scale=20.0,
    )

    assert components.geometry_penalty == 0.0


def test_weighting_strategy_combines_normalized_components() -> None:
    metrics = _metrics(
        color_difference=20.0,
        source_area=2,
        affected_area_ratio=0.25,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=8,
        target_area=4,
        merged_area=8,
        merged_perimeter=12,
    )

    strategy = WeightingStrategy(
        name="test",
        color_scale=20.0,
        color_weight=0.4,
        affected_area_weight=0.2,
        border_weight=0.2,
        geometry_weight=0.2,
    )

    evaluation = evaluate_weighting_strategy(
        (
            (
                RegionMergeCandidate(
                    source_id=1,
                    target_id=2,
                ),
                metrics,
            ),
        ),
        strategy=strategy,
    )

    assert evaluation.cost_distribution.minimum == pytest.approx(
        0.4222222222,
    )
    assert evaluation.cost_distribution.maximum == pytest.approx(
        0.4222222222,
    )


def test_equal_cost_candidates_use_region_ids_for_evaluation_order() -> None:
    metrics = _metrics(
        color_difference=10.0,
        source_area=2,
        affected_area_ratio=0.5,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=8,
        target_area=2,
        merged_area=4,
        merged_perimeter=8,
    )

    strategy = WeightingStrategy(
        name="test",
        color_scale=20.0,
        color_weight=0.4,
        affected_area_weight=0.2,
        border_weight=0.2,
        geometry_weight=0.2,
    )

    evaluation = evaluate_weighting_strategy(
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
                    target_id=2,
                ),
                metrics,
            ),
        ),
        strategy=strategy,
    )

    assert evaluation.low_cost_candidates[0].candidate == (
        RegionMergeCandidate(
            source_id=1,
            target_id=2,
        )
    )
