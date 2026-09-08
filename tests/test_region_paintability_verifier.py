# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions import RegionMerger
from pbn.regions.complexity_reducer import RegionComplexityReducer
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
from pbn.regions.paintability_verifier import (
    RegionPaintabilityStatus,
    RegionPaintabilityVerifier,
)


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
) -> Region:
    return Region(
        id=region_id,
        color=_color(region_id),
        pixels=pack_pixels(
            {
                (x, y)
                for x in range(
                    start_x,
                    start_x + 5,
                )
                for y in range(5)
            },
        ),
    )


def test_evaluate_reports_mergeable_undersized_region() -> None:
    large = _block_region(
        region_id=1,
        start_x=0,
    )
    undersized = Region(
        id=2,
        color=_color(2),
        pixels=pack_pixels(
            {
                (5, 2),
            },
        ),
    )

    result = RegionPaintabilityVerifier().evaluate(
        (
            large,
            undersized,
        ),
        minimum_circle_diameter_px=4,
    )

    assert result == RegionPaintabilityStatus(
        undersized_region_ids=(2,),
        mergeable_undersized_region_ids=(2,),
    )


def test_evaluate_keeps_isolated_undersized_region_visible() -> None:
    large = _block_region(
        region_id=1,
        start_x=0,
    )
    isolated = Region(
        id=2,
        color=_color(2),
        pixels=pack_pixels(
            {
                (10, 10),
            },
        ),
    )

    result = RegionPaintabilityVerifier().evaluate(
        (
            large,
            isolated,
        ),
        minimum_circle_diameter_px=4,
    )

    assert result == RegionPaintabilityStatus(
        undersized_region_ids=(2,),
        mergeable_undersized_region_ids=(),
    )


def test_mandatory_merge_removes_all_mergeable_undersized_regions() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    undersized = Region(
        id=2,
        color=_color(2),
        pixels=pack_pixels(
            {
                (5, 2),
            },
        ),
    )
    second = _block_region(
        region_id=3,
        start_x=6,
    )

    mandatory_result = RegionMerger().merge(
        (
            first,
            undersized,
            second,
        ),
        minimum_circle_diameter_px=4,
    )

    result = RegionPaintabilityVerifier().evaluate(
        mandatory_result,
        minimum_circle_diameter_px=4,
    )

    assert result.undersized_region_ids == ()
    assert result.mergeable_undersized_region_ids == ()


def test_optional_merges_preserve_paintability_invariant() -> None:
    first = _block_region(
        region_id=1,
        start_x=0,
    )
    second = _block_region(
        region_id=2,
        start_x=5,
    )
    third = _block_region(
        region_id=3,
        start_x=10,
    )

    verifier = RegionPaintabilityVerifier()

    initial_status = verifier.evaluate(
        (
            first,
            second,
            third,
        ),
        minimum_circle_diameter_px=4,
    )

    assert initial_status.undersized_region_ids == ()
    assert initial_status.mergeable_undersized_region_ids == ()

    reducer = RegionComplexityReducer(
        color_distance=ConstantColorDistance(),
        cost_calculator=RegionMergeCostCalculator(
            color_weight=1.0,
            affected_area_weight=0.0,
            border_weight=0.0,
            geometry_weight=0.0,
        ),
    )

    after_first_merge = reducer.reduce(
        (
            first,
            second,
            third,
        ),
        minimum_circle_diameter_px=4,
        max_regions=2,
        maximum_merge_cost=0.0,
    )

    assert len(after_first_merge) == 2

    first_merge_status = verifier.evaluate(
        after_first_merge,
        minimum_circle_diameter_px=4,
    )

    assert first_merge_status.undersized_region_ids == ()
    assert first_merge_status.mergeable_undersized_region_ids == ()

    after_second_merge = reducer.reduce(
        after_first_merge,
        minimum_circle_diameter_px=4,
        max_regions=1,
        maximum_merge_cost=0.0,
    )

    assert len(after_second_merge) == 1

    second_merge_status = verifier.evaluate(
        after_second_merge,
        minimum_circle_diameter_px=4,
    )

    assert second_merge_status.undersized_region_ids == ()
    assert second_merge_status.mergeable_undersized_region_ids == ()
