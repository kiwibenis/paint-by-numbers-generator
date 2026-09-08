# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import math

import pytest

from pbn.models import RegionMergeMetrics
from pbn.regions.merge_cost_calculator import (
    DetailPreservingRegionMergeCostCalculator,
    RegionMergeCostCalculator,
)


def _metrics(
    *,
    color_difference: float = 20.0,
    affected_area_ratio: float = 0.25,
    shared_border_length: int = 2,
    source_perimeter: int = 8,
    target_area: int = 4,
    target_perimeter: int = 8,
    merged_area: int = 8,
    merged_perimeter: int = 12,
) -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=color_difference,
        source_area=2,
        target_area=target_area,
        merged_area=merged_area,
        affected_area_ratio=affected_area_ratio,
        shared_border_length=shared_border_length,
        source_perimeter=source_perimeter,
        target_perimeter=target_perimeter,
        merged_perimeter=merged_perimeter,
    )


def _base_calculator() -> RegionMergeCostCalculator:
    """
    Return the weighting this file's arithmetic assertions are written against.

    These are the test's own weights, chosen so the expected values below can
    be read off the call. They are deliberately not the shipped profile's
    weighting, which `config/example.toml` owns and
    `tests/test_readme_example_configuration.py` covers.
    """
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.20,
        border_weight=0.20,
        geometry_weight=0.20,
    )


def _detail_preserving_calculator(
    *,
    enclosure_strength: float = 0.50,
    compactness_strength: float = 0.15,
) -> DetailPreservingRegionMergeCostCalculator:
    return DetailPreservingRegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=enclosure_strength,
        compactness_strength=compactness_strength,
    )


def test_calculate_final_region_merge_cost() -> None:
    cost = _base_calculator().calculate(
        _metrics(),
    )

    assert cost.color_penalty == pytest.approx(
        2 / 3,
    )
    assert cost.affected_area_penalty == pytest.approx(
        0.25,
    )
    assert cost.border_penalty == pytest.approx(
        0.75,
    )
    assert cost.geometry_penalty == pytest.approx(
        1 / 9,
    )
    assert cost.value == pytest.approx(
        0.4 * (2 / 3) + 0.2 * 0.25 + 0.2 * 0.75 + 0.2 * (1 / 9),
    )


def test_detail_preserving_calculator_applies_final_formula() -> None:
    metrics = _metrics()

    cost = _detail_preserving_calculator().calculate(
        metrics,
    )

    base_cost = 0.40 * (2 / 3) + 0.25 * 0.25 + 0.15 * 0.75 + 0.20 * (1 / 9)

    enclosure_penalty = (
        metrics.source_shared_border_ratio
        * (2 / 3)
        * (1.0 - metrics.affected_area_ratio)
    )

    enclosure_adjusted_cost = base_cost + 0.50 * enclosure_penalty * (1.0 - base_cost)

    compactness_penalty = (
        metrics.source_non_compactness * (2 / 3) * (1.0 - metrics.affected_area_ratio)
    )

    expected_value = enclosure_adjusted_cost + 0.15 * compactness_penalty * (
        1.0 - enclosure_adjusted_cost
    )

    assert cost.color_penalty == pytest.approx(
        2 / 3,
    )
    assert cost.affected_area_penalty == pytest.approx(
        0.25,
    )
    assert cost.border_penalty == pytest.approx(
        0.75,
    )
    assert cost.geometry_penalty == pytest.approx(
        1 / 9,
    )
    assert cost.value == pytest.approx(
        expected_value,
    )


def test_detail_preserving_cost_exceeds_configured_base_cost() -> None:
    metrics = _metrics()

    base_cost = RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    ).calculate(
        metrics,
    )

    protected_cost = _detail_preserving_calculator().calculate(
        metrics,
    )

    assert protected_cost.value > base_cost.value

    assert protected_cost.color_penalty == (base_cost.color_penalty)
    assert protected_cost.affected_area_penalty == (base_cost.affected_area_penalty)
    assert protected_cost.border_penalty == (base_cost.border_penalty)
    assert protected_cost.geometry_penalty == (base_cost.geometry_penalty)


def test_zero_protection_strengths_preserve_configured_base_cost() -> None:
    metrics = _metrics()

    base_cost = RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    ).calculate(
        metrics,
    )

    protected_cost = _detail_preserving_calculator(
        enclosure_strength=0.0,
        compactness_strength=0.0,
    ).calculate(
        metrics,
    )

    assert protected_cost == base_cost


@pytest.mark.parametrize(
    (
        "enclosure_strength",
        "compactness_strength",
    ),
    (
        (
            -0.01,
            0.15,
        ),
        (
            1.01,
            0.15,
        ),
        (
            math.nan,
            0.15,
        ),
        (
            0.50,
            -0.01,
        ),
        (
            0.50,
            1.01,
        ),
        (
            0.50,
            math.inf,
        ),
    ),
)
def test_detail_preserving_calculator_rejects_invalid_strengths(
    enclosure_strength: float,
    compactness_strength: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be finite and between zero and one",
    ):
        _detail_preserving_calculator(
            enclosure_strength=enclosure_strength,
            compactness_strength=compactness_strength,
        )


def test_zero_color_difference_has_no_color_penalty() -> None:
    cost = _base_calculator().calculate(
        _metrics(
            color_difference=0.0,
        ),
    )

    assert cost.color_penalty == 0.0


def test_geometry_improvement_has_no_geometry_penalty() -> None:
    metrics = _metrics(
        target_area=2,
        target_perimeter=6,
        merged_area=6,
        merged_perimeter=10,
    )

    assert metrics.geometry_change < 0.0

    cost = _base_calculator().calculate(
        metrics,
    )

    assert cost.geometry_penalty == 0.0


def test_source_shared_border_ratio_controls_border_penalty() -> None:
    cost = _base_calculator().calculate(
        _metrics(
            shared_border_length=6,
            source_perimeter=8,
        ),
    )

    assert cost.border_penalty == pytest.approx(
        0.25,
    )


def test_directed_affected_area_ratio_is_preserved_as_penalty() -> None:
    cost = _base_calculator().calculate(
        _metrics(
            affected_area_ratio=0.125,
        ),
    )

    assert cost.affected_area_penalty == pytest.approx(
        0.125,
    )


def test_custom_weights_change_only_weighted_total() -> None:
    metrics = _metrics()

    cost = RegionMergeCostCalculator(
        color_weight=0.60,
        affected_area_weight=0.15,
        border_weight=0.15,
        geometry_weight=0.10,
    ).calculate(
        metrics,
    )

    assert cost.color_penalty == pytest.approx(
        2 / 3,
    )
    assert cost.affected_area_penalty == pytest.approx(
        0.25,
    )
    assert cost.border_penalty == pytest.approx(
        0.75,
    )
    assert cost.geometry_penalty == pytest.approx(
        1 / 9,
    )
    assert cost.value == pytest.approx(
        0.60 * (2 / 3) + 0.15 * 0.25 + 0.15 * 0.75 + 0.10 * (1 / 9),
    )


@pytest.mark.parametrize(
    (
        "color_weight",
        "affected_area_weight",
        "border_weight",
        "geometry_weight",
    ),
    (
        (
            0.50,
            0.20,
            0.20,
            0.20,
        ),
        (
            -0.10,
            0.40,
            0.40,
            0.30,
        ),
        (
            math.nan,
            0.20,
            0.20,
            0.60,
        ),
    ),
)
def test_rejects_invalid_custom_weights(
    color_weight: float,
    affected_area_weight: float,
    border_weight: float,
    geometry_weight: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="merge-cost weights",
    ):
        RegionMergeCostCalculator(
            color_weight=color_weight,
            affected_area_weight=affected_area_weight,
            border_weight=border_weight,
            geometry_weight=geometry_weight,
        )
