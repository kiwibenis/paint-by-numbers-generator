# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from unittest.mock import patch

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeCost,
    RegionMergeStep,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions import RegionAdjacency, RegionMerger
from pbn.regions.complexity_reducer import RegionComplexityReducer
from pbn.regions.merge_candidate_builder import RegionMergeCandidateBuilder
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator


class ConstantColorDistance(ColorDistance):
    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return 0.0


def _color(
    number: int,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=RGB(
            red=number,
            green=number,
            blue=number,
        ),
        lab=Lab(
            l=float(number),
            a=0.0,
            b=0.0,
        ),
    )


def _block_region(
    region_id: int,
    *,
    start_x: int,
    color_number: int | None = None,
) -> Region:
    return Region(
        id=region_id,
        color=_color(
            region_id if color_number is None else color_number,
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


def _base_calculator() -> RegionMergeCostCalculator:
    """
    Return the weighting this file's assertions are written against.

    Stated here rather than left to the calculator, which no longer supplies
    one of its own.
    """
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    )


def test_reduce_stops_when_max_regions_is_already_reached() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            second,
            first,
        ),
        minimum_circle_diameter_px=2,
        max_regions=2,
        maximum_merge_cost=1.0,
    )

    assert result == (
        first,
        second,
    )


def test_reduce_selects_cheapest_candidate_deterministically() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
        color_number=10,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
        color_number=20,
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            second,
            first,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert len(result) == 1

    merged = result[0]

    assert merged.id == second.id
    assert merged.color == second.color
    assert merged.pixels == frozenset(
        first.pixels | second.pixels,
    )


def test_reduce_stops_when_cheapest_candidate_exceeds_maximum_cost() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            first,
            second,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=0.0,
    )

    assert result == (
        first,
        second,
    )


def test_reduce_accepts_candidate_equal_to_maximum_merge_cost() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )

    fixed_cost = RegionMergeCost(
        color_penalty=0.5,
        affected_area_penalty=0.5,
        border_penalty=0.5,
        geometry_penalty=0.5,
        value=0.5,
    )

    with patch.object(
        RegionMergeCostCalculator,
        "calculate",
        autospec=True,
        return_value=fixed_cost,
    ):
        result = RegionComplexityReducer(
            color_distance=ConstantColorDistance(),
            cost_calculator=_base_calculator(),
        ).reduce(
            (
                first,
                second,
            ),
            minimum_circle_diameter_px=2,
            max_regions=1,
            maximum_merge_cost=0.5,
        )

    assert len(result) == 1


def test_reduce_uses_injected_merge_cost_calculator() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )

    cost_calculator = RegionMergeCostCalculator(
        color_weight=1.0,
        affected_area_weight=0.0,
        border_weight=0.0,
        geometry_weight=0.0,
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=cost_calculator,
    ).reduce(
        (
            first,
            second,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=0.0,
    )

    assert len(result) == 1


def test_reduce_continues_until_max_regions_is_reached() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )
    third = _block_region(
        region_id=3,
        start_x=8,
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            third,
            first,
            second,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert len(result) == 1
    assert result[0].pixels == frozenset(first.pixels | second.pixels | third.pixels)


def test_reduce_with_trace_reports_actual_accepted_merge_sequence() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )
    third = _block_region(
        region_id=3,
        start_x=8,
    )

    result, merge_steps = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce_with_trace(
        (
            third,
            first,
            second,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert len(result) == 1
    assert result[0].id == 2

    assert all(
        isinstance(
            merge_step,
            RegionMergeStep,
        )
        for merge_step in merge_steps
    )

    assert tuple(
        (
            merge_step.candidate.source_id,
            merge_step.candidate.target_id,
        )
        for merge_step in merge_steps
    ) == (
        (1, 2),
        (3, 2),
    )

    assert merge_steps[0].metrics.source_area == 16
    assert merge_steps[0].metrics.target_area == 16

    assert merge_steps[1].metrics.source_area == 16
    assert merge_steps[1].metrics.target_area == 32

    assert all(merge_step.cost.value <= 1.0 for merge_step in merge_steps)


def test_reduce_stops_above_target_when_no_candidate_is_acceptable() -> None:
    first = Region(
        id=1,
        color=_color(1),
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )
    second = Region(
        id=2,
        color=_color(2),
        pixels=pack_pixels(
            {
                (1, 0),
            },
        ),
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            first,
            second,
        ),
        minimum_circle_diameter_px=4,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert result == (
        first,
        second,
    )


def test_reduce_can_merge_unpaintable_source_into_paintable_target() -> None:
    target = _block_region(
        region_id=1,
        start_x=0,
    )
    source = Region(
        id=2,
        color=_color(2),
        pixels=pack_pixels(
            {
                (4, 1),
            },
        ),
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            source,
            target,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert len(result) == 1
    assert result[0].id == target.id
    assert result[0].color == target.color
    assert result[0].pixels == frozenset(
        target.pixels | source.pixels,
    )


def test_mandatory_merge_is_unchanged_by_optional_quality_boundary() -> None:
    mandatory_target = _block_region(
        region_id=1,
        start_x=0,
    )
    undersized = Region(
        id=2,
        color=_color(2),
        pixels=pack_pixels(
            {
                (4, 1),
            },
        ),
    )
    optional_neighbor = _block_region(
        region_id=3,
        start_x=5,
    )

    mandatory_result = RegionMerger().merge(
        (
            mandatory_target,
            undersized,
            optional_neighbor,
        ),
        minimum_circle_diameter_px=2,
    )

    assert len(mandatory_result) == 2

    merged_mandatory_target = next(
        region for region in mandatory_result if region.id == mandatory_target.id
    )

    assert merged_mandatory_target.color == mandatory_target.color
    assert merged_mandatory_target.pixels == frozenset(
        mandatory_target.pixels | undersized.pixels,
    )

    result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        mandatory_result,
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=0.0,
    )

    assert result == tuple(
        sorted(
            mandatory_result,
            key=lambda region: region.id,
        ),
    )


def test_reduce_reuses_initial_adjacency_across_multiple_merges() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )
    third = _block_region(
        region_id=3,
        start_x=8,
    )

    with patch.object(
        RegionAdjacency,
        "shared_borders_with_overlap_status",
        autospec=True,
        wraps=RegionAdjacency.shared_borders_with_overlap_status,
    ) as calculate_shared_borders:
        result = RegionComplexityReducer(
            color_distance=ConstantColorDistance(),
            cost_calculator=_base_calculator(),
        ).reduce(
            (
                third,
                first,
                second,
            ),
            minimum_circle_diameter_px=2,
            max_regions=1,
            maximum_merge_cost=1.0,
        )

    assert len(result) == 1
    assert calculate_shared_borders.call_count == 1


def test_reduce_recalculates_only_candidates_touching_changed_target() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )
    third = _block_region(
        region_id=3,
        start_x=8,
    )

    with patch.object(
        RegionMergeCandidateBuilder,
        "build_from_shared_borders",
        autospec=True,
        wraps=RegionMergeCandidateBuilder.build_from_shared_borders,
    ) as build_candidates:
        result = RegionComplexityReducer(
            color_distance=ConstantColorDistance(),
            cost_calculator=_base_calculator(),
        ).reduce(
            (
                third,
                first,
                second,
            ),
            minimum_circle_diameter_px=2,
            max_regions=1,
            maximum_merge_cost=1.0,
        )

    assert len(result) == 1

    touching_region_ids = tuple(
        call.kwargs["touching_region_ids"] for call in build_candidates.call_args_list
    )

    assert touching_region_ids == (
        None,
        frozenset(
            {
                2,
            },
        ),
        frozenset(
            {
                2,
            },
        ),
    )


def test_reduce_is_independent_from_input_region_order() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=4,
    )
    third = _block_region(
        region_id=3,
        start_x=8,
    )

    forward = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            first,
            second,
            third,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    reversed_order = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        (
            third,
            second,
            first,
        ),
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert forward == reversed_order


def test_reduce_is_reproducible_across_repeated_executions() -> None:
    regions = (
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
        _block_region(
            region_id=3,
            start_x=8,
        ),
    )

    first_result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        regions,
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    second_result = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    ).reduce(
        regions,
        minimum_circle_diameter_px=2,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert first_result == second_result
