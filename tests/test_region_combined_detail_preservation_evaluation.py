# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.infrastructure.config_loader import load_config
from pbn.models import (
    RegionMergeMetrics,
)
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    ComplexityReductionResult,
)
from tools.evaluate_region_combined_detail_preservation import (
    DEFAULT_BASE_WEIGHT_SET,
    BaseWeightSet,
    CombinedDetailPreservingRegionMergeCostCalculator,
    EvaluationInput,
    build_parser,
    combined_preview_output_path,
    compactness_detail_preservation_penalty,
    resolve_base_weight_sets,
    resolve_evaluation_inputs,
)
from tools.evaluate_region_detail_preservation import (
    DetailPreservingRegionMergeCostCalculator,
    adjusted_detail_preservation_cost,
    detail_preservation_penalty_from_components,
)

_BASE_WEIGHT_SET = BaseWeightSet(
    color_weight=0.40,
    affected_area_weight=0.25,
    border_weight=0.15,
    geometry_weight=0.20,
)
"""
The base weighting these tests are written against.

Stated here rather than left to the calculator, which no longer supplies a
weighting of its own.
"""

_BASE_WEIGHTS = {
    "color_weight": _BASE_WEIGHT_SET.color_weight,
    "affected_area_weight": (_BASE_WEIGHT_SET.affected_area_weight),
    "border_weight": _BASE_WEIGHT_SET.border_weight,
    "geometry_weight": _BASE_WEIGHT_SET.geometry_weight,
}


def _metrics() -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=20.0,
        source_area=20,
        target_area=80,
        merged_area=100,
        affected_area_ratio=0.20,
        shared_border_length=10,
        source_perimeter=20,
        target_perimeter=40,
        merged_perimeter=40,
    )


def _result() -> ComplexityReductionResult:
    return ComplexityReductionResult(
        case="portrait",
        baseline_region_count=376,
        target_fraction=0.50,
        max_regions=188,
        maximum_merge_cost=0.28,
        final_region_count=330,
        reduction_seconds=1.0,
    )


def test_compactness_penalty_combines_non_compactness_and_color() -> None:
    metrics = _metrics()

    color_penalty = metrics.color_difference / (metrics.color_difference + 10.0)

    assert compactness_detail_preservation_penalty(
        metrics=metrics,
        color_penalty=color_penalty,
    ) == pytest.approx(
        metrics.source_non_compactness
        * color_penalty
        * (1.0 - metrics.affected_area_ratio),
    )


def test_zero_compactness_strength_preserves_enclosure_result() -> None:
    metrics = _metrics()

    enclosure_result = DetailPreservingRegionMergeCostCalculator(
        strength=0.50,
        **_BASE_WEIGHTS,
    ).calculate(
        metrics,
    )

    combined_result = CombinedDetailPreservingRegionMergeCostCalculator(
        enclosure_strength=0.50,
        compactness_strength=0.0,
        base_weights=_BASE_WEIGHT_SET,
    ).calculate(
        metrics,
    )

    assert combined_result == enclosure_result


def test_combined_calculator_uses_the_given_base_weighting() -> None:
    """
    The base weighting is supplied as one weight set.

    It used to be a calculator that could be omitted, in which case the Core
    class supplied a weighting of its own that no profile ships.
    """
    metrics = _metrics()

    base_weights = BaseWeightSet(
        color_weight=0.70,
        affected_area_weight=0.10,
        border_weight=0.10,
        geometry_weight=0.10,
    )

    combined_calculator = CombinedDetailPreservingRegionMergeCostCalculator(
        enclosure_strength=0.0,
        compactness_strength=0.0,
        base_weights=base_weights,
    )

    assert combined_calculator.calculate(
        metrics,
    ) == base_weights.build_calculator().calculate(
        metrics,
    )


def test_combined_calculator_applies_compactness_after_enclosure() -> None:
    metrics = _metrics()

    calculator = CombinedDetailPreservingRegionMergeCostCalculator(
        enclosure_strength=0.50,
        compactness_strength=0.10,
        base_weights=_BASE_WEIGHT_SET,
    )

    result = calculator.calculate(
        metrics,
    )

    base_cost = calculator.base_calculator.calculate(
        metrics,
    )

    enclosure_penalty = detail_preservation_penalty_from_components(
        source_shared_border_ratio=(metrics.source_shared_border_ratio),
        color_penalty=base_cost.color_penalty,
        affected_area_ratio=(metrics.affected_area_ratio),
    )

    enclosure_adjusted_cost = adjusted_detail_preservation_cost(
        base_cost=base_cost.value,
        protection_penalty=enclosure_penalty,
        strength=0.50,
    )

    compactness_penalty = compactness_detail_preservation_penalty(
        metrics=metrics,
        color_penalty=base_cost.color_penalty,
    )

    expected_value = adjusted_detail_preservation_cost(
        base_cost=enclosure_adjusted_cost,
        protection_penalty=compactness_penalty,
        strength=0.10,
    )

    assert result.color_penalty == base_cost.color_penalty
    assert result.affected_area_penalty == base_cost.affected_area_penalty
    assert result.border_penalty == base_cost.border_penalty
    assert result.geometry_penalty == base_cost.geometry_penalty

    assert result.value == pytest.approx(
        expected_value,
    )


@pytest.mark.parametrize(
    (
        "enclosure_strength",
        "compactness_strength",
    ),
    (
        (-0.01, 0.10),
        (1.01, 0.10),
        (0.50, -0.01),
        (0.50, 1.01),
    ),
)
def test_combined_calculator_rejects_invalid_strengths(
    enclosure_strength: float,
    compactness_strength: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="strength must be between zero and one",
    ):
        CombinedDetailPreservingRegionMergeCostCalculator(
            enclosure_strength=enclosure_strength,
            compactness_strength=compactness_strength,
            base_weights=_BASE_WEIGHT_SET,
        )


def test_base_weight_sets_default_to_production_weights() -> None:
    assert resolve_base_weight_sets(
        None,
    ) == (DEFAULT_BASE_WEIGHT_SET,)


def test_the_default_weights_are_the_weights_the_project_ships() -> None:
    """
    The check the test above cannot perform.

    That one compares the constant to itself, so it stayed green while
    the constant drifted from the four weights the shipped profiles
    configure, and the recorded cross-image calibration of
    `maximum_merge_cost` was produced against the drifted values.

    Read from the shipped profile rather than repeated as literals, or
    this test would be the same tautology one level up.
    """
    merge_cost = load_config(
        Path("config/example.toml"),
    ).region_complexity.merge_cost

    assert DEFAULT_BASE_WEIGHT_SET == BaseWeightSet(
        color_weight=merge_cost.color_weight,
        affected_area_weight=merge_cost.affected_area_weight,
        border_weight=merge_cost.border_weight,
        geometry_weight=merge_cost.geometry_weight,
    )


def test_base_weight_sets_validate_each_weighting() -> None:
    with pytest.raises(
        ValueError,
        match="Region merge-cost weights",
    ):
        resolve_base_weight_sets(
            [
                [
                    0.50,
                    0.20,
                    0.20,
                    0.20,
                ],
            ],
        )


def test_parser_accepts_repeated_base_weight_sets() -> None:
    args = build_parser().parse_args(
        [
            "--base-weights",
            "0.40",
            "0.20",
            "0.20",
            "0.20",
            "--base-weights",
            "0.50",
            "0.20",
            "0.15",
            "0.15",
            "--enclosure-strength",
            "0.50",
            "--compactness-strengths",
            "0.15",
            "--target-fraction",
            "0.50",
            "--maximum-merge-costs",
            "0.25",
        ],
    )

    assert args.base_weights == [
        [
            0.40,
            0.20,
            0.20,
            0.20,
        ],
        [
            0.50,
            0.20,
            0.15,
            0.15,
        ],
    ]


def test_custom_base_weights_make_preview_path_unique() -> None:
    production_path = combined_preview_output_path(
        output_directory=Path("output"),
        case="portrait",
        result=_result(),
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )

    custom_path = combined_preview_output_path(
        output_directory=Path("output"),
        case="portrait",
        result=_result(),
        enclosure_strength=0.50,
        compactness_strength=0.15,
        base_weights=BaseWeightSet(
            color_weight=0.50,
            affected_area_weight=0.20,
            border_weight=0.15,
            geometry_weight=0.15,
        ),
    )

    assert production_path != custom_path
    assert "weights-0p500-0p200-0p150-0p150" in custom_path.name


def test_parser_accepts_minimum_region_size_override() -> None:
    args = build_parser().parse_args(
        [
            "--minimum-region-size-mm",
            "1.0",
            "--enclosure-strength",
            "0.50",
            "--compactness-strengths",
            "0.15",
            "--target-fraction",
            "0.75",
            "--maximum-merge-costs",
            "0.52",
        ],
    )

    assert args.minimum_region_size_mm == 1.0


def test_parser_accepts_local_input_images() -> None:
    args = build_parser().parse_args(
        [
            "--input-images",
            "evaluation/portrait.jpg",
            "evaluation/architecture.png",
            "--enclosure-strength",
            "0.50",
            "--compactness-strengths",
            "0.15",
            "--target-fraction",
            "0.50",
            "--maximum-merge-costs",
            "0.20",
        ],
    )

    assert args.cases is None
    assert args.input_images == [
        Path("evaluation/portrait.jpg"),
        Path("evaluation/architecture.png"),
    ]


def test_evaluation_inputs_default_to_standard_cases() -> None:
    result = resolve_evaluation_inputs(
        cases=None,
        input_images=(),
    )

    assert result == tuple(
        EvaluationInput(
            case=case,
        )
        for case in EVALUATION_CASES
    )


def test_local_images_do_not_implicitly_add_standard_cases() -> None:
    portrait_path = Path(
        "evaluation/portrait.jpg",
    )
    architecture_path = Path(
        "evaluation/architecture.png",
    )

    result = resolve_evaluation_inputs(
        cases=None,
        input_images=(
            portrait_path,
            architecture_path,
        ),
    )

    assert result == (
        EvaluationInput(
            case="portrait",
            image_path=portrait_path,
        ),
        EvaluationInput(
            case="architecture",
            image_path=architecture_path,
        ),
    )


def test_evaluation_inputs_can_combine_cases_and_local_images() -> None:
    portrait_path = Path(
        "evaluation/portrait.jpg",
    )

    result = resolve_evaluation_inputs(
        cases=("simple",),
        input_images=(portrait_path,),
    )

    assert result == (
        EvaluationInput(
            case="simple",
        ),
        EvaluationInput(
            case="portrait",
            image_path=portrait_path,
        ),
    )


def test_evaluation_inputs_reject_duplicate_case_names() -> None:
    with pytest.raises(
        ValueError,
        match="Duplicate evaluation case name: medium",
    ):
        resolve_evaluation_inputs(
            cases=("medium",),
            input_images=(
                Path(
                    "evaluation/medium.jpg",
                ),
            ),
        )
