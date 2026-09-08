# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeCandidate,
    RegionMergeCost,
    RegionMergeMetrics,
    RegionMergeStep,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
from tools.benchmark_region_complexity import (
    CandidateDiagnostic,
    ComplexityReductionResult,
)
from tools.evaluate_region_detail_preservation import (
    DetailPreservingRegionMergeCostCalculator,
    adjusted_detail_preservation_cost,
    build_accepted_merge_diagnostics,
    detail_preservation_penalty,
    detail_preview_output_path,
    evaluate_detail_preservation,
    execute_detail_reduction,
    format_accepted_merge_diagnostic,
)

_BASE_WEIGHTS = {
    "color_weight": 0.40,
    "affected_area_weight": 0.25,
    "border_weight": 0.15,
    "geometry_weight": 0.20,
}
"""
The base weighting these tests are written against.

Stated here rather than left to the calculator, which no longer supplies a
weighting of its own.
"""


class ConstantColorDistance(ColorDistance):
    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return 0.0


def _diagnostic(
    *,
    source_id: int,
    target_id: int,
    base_cost: float,
    color_penalty: float,
    affected_area_ratio: float,
    source_shared_border_ratio: float,
) -> CandidateDiagnostic:
    source_perimeter = 100
    shared_border_length = round(
        source_perimeter * source_shared_border_ratio,
    )

    metrics = RegionMergeMetrics(
        color_difference=20.0,
        source_area=20,
        target_area=80,
        merged_area=100,
        affected_area_ratio=affected_area_ratio,
        shared_border_length=shared_border_length,
        source_perimeter=source_perimeter,
        target_perimeter=200,
        merged_perimeter=220,
    )

    return CandidateDiagnostic(
        candidate=RegionMergeCandidate(
            source_id=source_id,
            target_id=target_id,
        ),
        source_color_number=101,
        source_color_name="Source",
        target_color_number=102,
        target_color_name="Target",
        source_bounds=(0, 0, 9, 9),
        target_bounds=(0, 0, 19, 19),
        metrics=metrics,
        cost=RegionMergeCost(
            color_penalty=color_penalty,
            affected_area_penalty=affected_area_ratio,
            border_penalty=(1.0 - metrics.source_shared_border_ratio),
            geometry_penalty=0.0,
            value=base_cost,
        ),
    )


def _region(
    region_id: int,
    *,
    start_x: int,
) -> Region:
    return Region(
        id=region_id,
        color=PaletteColor(
            number=region_id,
            name=f"Color {region_id}",
            rgb=RGB(
                red=region_id,
                green=region_id,
                blue=region_id,
            ),
            lab=Lab(
                l=float(region_id),
                a=0.0,
                b=0.0,
            ),
        ),
        pixels=pack_pixels(
            {
                (x, y)
                for x in range(
                    start_x,
                    start_x + 4,
                )
                for y in range(4)
            },
        ),
    )


def test_detail_preservation_penalty_combines_existing_signals() -> None:
    diagnostic = _diagnostic(
        source_id=1,
        target_id=2,
        base_cost=0.30,
        color_penalty=0.70,
        affected_area_ratio=0.10,
        source_shared_border_ratio=1.0,
    )

    assert detail_preservation_penalty(
        diagnostic,
    ) == pytest.approx(
        1.0 * 0.70 * 0.90,
    )


def test_detail_preservation_penalty_is_zero_without_enclosure() -> None:
    diagnostic = _diagnostic(
        source_id=1,
        target_id=2,
        base_cost=0.30,
        color_penalty=0.70,
        affected_area_ratio=0.10,
        source_shared_border_ratio=0.0,
    )

    assert (
        detail_preservation_penalty(
            diagnostic,
        )
        == 0.0
    )


def test_zero_strength_preserves_base_cost() -> None:
    assert adjusted_detail_preservation_cost(
        base_cost=0.30,
        protection_penalty=0.80,
        strength=0.0,
    ) == pytest.approx(
        0.30,
    )


def test_full_strength_moves_cost_toward_one() -> None:
    assert adjusted_detail_preservation_cost(
        base_cost=0.30,
        protection_penalty=0.80,
        strength=1.0,
    ) == pytest.approx(
        0.30 + 0.80 * 0.70,
    )


@pytest.mark.parametrize(
    "strength",
    (
        -0.01,
        1.01,
    ),
)
def test_adjusted_detail_preservation_cost_rejects_invalid_strength(
    strength: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="strength must be between zero and one",
    ):
        adjusted_detail_preservation_cost(
            base_cost=0.30,
            protection_penalty=0.80,
            strength=strength,
        )


def test_evaluate_detail_preservation_reranks_protected_candidate() -> None:
    enclosed = _diagnostic(
        source_id=1,
        target_id=2,
        base_cost=0.30,
        color_penalty=0.80,
        affected_area_ratio=0.05,
        source_shared_border_ratio=1.0,
    )
    less_enclosed = _diagnostic(
        source_id=3,
        target_id=4,
        base_cost=0.35,
        color_penalty=0.60,
        affected_area_ratio=0.10,
        source_shared_border_ratio=0.40,
    )

    evaluations = evaluate_detail_preservation(
        diagnostics=(
            enclosed,
            less_enclosed,
        ),
        strength=0.5,
    )

    assert tuple(
        evaluation.diagnostic.candidate.source_id for evaluation in evaluations
    ) == (
        3,
        1,
    )


def test_evaluate_detail_preservation_uses_ids_for_equal_costs() -> None:
    second = _diagnostic(
        source_id=2,
        target_id=3,
        base_cost=0.30,
        color_penalty=0.0,
        affected_area_ratio=0.5,
        source_shared_border_ratio=0.5,
    )
    first = _diagnostic(
        source_id=1,
        target_id=3,
        base_cost=0.30,
        color_penalty=0.0,
        affected_area_ratio=0.5,
        source_shared_border_ratio=0.5,
    )

    evaluations = evaluate_detail_preservation(
        diagnostics=(
            second,
            first,
        ),
        strength=0.5,
    )

    assert tuple(
        evaluation.diagnostic.candidate.source_id for evaluation in evaluations
    ) == (
        1,
        2,
    )


def test_detail_preserving_calculator_adjusts_full_merge_cost() -> None:
    metrics = RegionMergeMetrics(
        color_difference=20.0,
        source_area=20,
        target_area=80,
        merged_area=100,
        affected_area_ratio=0.20,
        shared_border_length=8,
        source_perimeter=10,
        target_perimeter=40,
        merged_perimeter=34,
    )

    base_cost = RegionMergeCostCalculator(
        **_BASE_WEIGHTS,
    ).calculate(
        metrics,
    )

    result = DetailPreservingRegionMergeCostCalculator(
        strength=0.50,
        **_BASE_WEIGHTS,
    ).calculate(
        metrics,
    )

    protection_penalty = (
        metrics.source_shared_border_ratio
        * base_cost.color_penalty
        * (1.0 - metrics.affected_area_ratio)
    )

    expected_value = adjusted_detail_preservation_cost(
        base_cost=base_cost.value,
        protection_penalty=protection_penalty,
        strength=0.50,
    )

    assert result.color_penalty == base_cost.color_penalty
    assert result.affected_area_penalty == base_cost.affected_area_penalty
    assert result.border_penalty == base_cost.border_penalty
    assert result.geometry_penalty == base_cost.geometry_penalty
    assert result.value == pytest.approx(
        expected_value,
    )


@pytest.mark.parametrize(
    "strength",
    (
        -0.01,
        1.01,
    ),
)
def test_detail_preserving_calculator_rejects_invalid_strength(
    strength: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="strength must be between zero and one",
    ):
        DetailPreservingRegionMergeCostCalculator(
            strength=strength,
            **_BASE_WEIGHTS,
        )


def test_execute_detail_reduction_returns_actual_merge_sequence() -> None:
    regions = (
        _region(
            region_id=3,
            start_x=8,
        ),
        _region(
            region_id=1,
            start_x=0,
        ),
        _region(
            region_id=2,
            start_x=4,
        ),
    )

    execution = execute_detail_reduction(
        case="test",
        regions=regions,
        color_distance=ConstantColorDistance(),
        minimum_circle_diameter_px=2,
        target_fraction=0.25,
        maximum_merge_cost=1.0,
        cost_calculator=(
            DetailPreservingRegionMergeCostCalculator(
                strength=0.0,
                **_BASE_WEIGHTS,
            )
        ),
    )

    assert execution.result.final_region_count == 1

    assert tuple(
        (
            merge_step.candidate.source_id,
            merge_step.candidate.target_id,
        )
        for merge_step in execution.merge_steps
    ) == (
        (1, 2),
        (3, 2),
    )


def test_build_accepted_merge_diagnostics_replays_dynamic_bounds() -> None:
    first = _region(
        region_id=1,
        start_x=0,
    )
    second = _region(
        region_id=2,
        start_x=4,
    )
    third = _region(
        region_id=3,
        start_x=8,
    )

    first_evaluation = _diagnostic(
        source_id=1,
        target_id=2,
        base_cost=0.30,
        color_penalty=0.70,
        affected_area_ratio=0.50,
        source_shared_border_ratio=0.25,
    )
    second_evaluation = _diagnostic(
        source_id=3,
        target_id=2,
        base_cost=0.31,
        color_penalty=0.70,
        affected_area_ratio=1 / 3,
        source_shared_border_ratio=0.25,
    )

    diagnostics = build_accepted_merge_diagnostics(
        regions=(
            first,
            second,
            third,
        ),
        merge_steps=(
            RegionMergeStep(
                candidate=first_evaluation.candidate,
                metrics=first_evaluation.metrics,
                cost=first_evaluation.cost,
            ),
            RegionMergeStep(
                candidate=second_evaluation.candidate,
                metrics=second_evaluation.metrics,
                cost=second_evaluation.cost,
            ),
        ),
    )

    assert diagnostics[0].source_bounds == (
        0,
        0,
        3,
        3,
    )
    assert diagnostics[0].target_bounds == (
        4,
        0,
        7,
        3,
    )

    assert diagnostics[1].source_bounds == (
        8,
        0,
        11,
        3,
    )
    assert diagnostics[1].target_bounds == (
        0,
        0,
        7,
        3,
    )


def test_format_accepted_merge_diagnostic_reports_step_metrics() -> None:
    first = _region(
        region_id=1,
        start_x=0,
    )
    second = _region(
        region_id=2,
        start_x=4,
    )

    evaluation = _diagnostic(
        source_id=1,
        target_id=2,
        base_cost=0.30,
        color_penalty=0.70,
        affected_area_ratio=0.50,
        source_shared_border_ratio=0.25,
    )

    diagnostic = build_accepted_merge_diagnostics(
        regions=(
            first,
            second,
        ),
        merge_steps=(
            RegionMergeStep(
                candidate=evaluation.candidate,
                metrics=evaluation.metrics,
                cost=evaluation.cost,
            ),
        ),
    )[0]

    formatted = format_accepted_merge_diagnostic(
        diagnostic,
        step_number=1,
    )

    assert "step=1" in formatted
    assert "source_id=1" in formatted
    assert "target_id=2" in formatted
    assert "source_bounds=(0, 0, 3, 3)" in formatted
    assert "target_bounds=(4, 0, 7, 3)" in formatted
    assert "cost=0.300000" in formatted
    assert "source_area=20" in formatted
    assert "source_perimeter=100" in formatted
    assert "source_shared_border_ratio=0.250000" in formatted


def test_detail_preview_output_path_identifies_reduction() -> None:
    result = ComplexityReductionResult(
        case="simple",
        baseline_region_count=33,
        target_fraction=0.25,
        max_regions=9,
        maximum_merge_cost=0.50,
        final_region_count=20,
        reduction_seconds=1.0,
    )

    path = detail_preview_output_path(
        output_directory=Path("output"),
        case="simple",
        result=result,
        strength=0.50,
    )

    assert path == Path(
        "output/"
        "region-detail-preservation-simple-"
        "strength-0p500-"
        "max-9-"
        "cost-0p500.bmp"
    )


def test_detail_preview_output_path_identifies_baseline() -> None:
    path = detail_preview_output_path(
        output_directory=Path("output"),
        case="simple",
        result=None,
        strength=0.50,
    )

    assert path == Path("output/" "region-detail-preservation-simple-baseline.bmp")
