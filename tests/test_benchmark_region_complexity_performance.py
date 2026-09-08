# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from unittest.mock import patch

import pytest

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_cost_calculator import (
    RegionMergeCostCalculator,
)
from tools.benchmark_region_complexity_performance import (
    benchmark_full_candidate_recalculation,
    benchmark_full_candidate_recalculation_for_regions,
    benchmark_incremental_adjacency_updates,
    benchmark_incremental_adjacency_updates_for_regions,
    benchmark_incremental_candidate_maintenance,
    benchmark_incremental_candidate_maintenance_for_regions,
    benchmark_initial_candidate_construction,
    build_accepted_merge_pairs,
    build_parser,
    format_full_candidate_recalculation_benchmark,
    format_incremental_candidate_maintenance_benchmark,
    format_initial_candidate_construction_benchmark,
    summarize_durations,
)


class ZeroColorDistance(ColorDistance):
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


def _adjacent_regions() -> tuple[
    Region,
    Region,
]:
    return (
        Region(
            id=1,
            color=_color(1),
            pixels=pack_pixels(
                {
                    (0, 0),
                },
            ),
        ),
        Region(
            id=2,
            color=_color(2),
            pixels=pack_pixels(
                {
                    (1, 0),
                },
            ),
        ),
    )


def _paintable_adjacent_regions() -> tuple[
    Region,
    Region,
]:
    return (
        Region(
            id=1,
            color=_color(1),
            pixels=pack_pixels(
                {(x, y) for x in range(3) for y in range(3)},
            ),
        ),
        Region(
            id=2,
            color=_color(2),
            pixels=pack_pixels(
                {(x, y) for x in range(3, 6) for y in range(3)},
            ),
        ),
    )


def _paintable_region_chain() -> tuple[
    Region,
    Region,
    Region,
]:
    return (
        Region(
            id=1,
            color=_color(1),
            pixels=pack_pixels(
                {(x, y) for x in range(3) for y in range(3)},
            ),
        ),
        Region(
            id=2,
            color=_color(2),
            pixels=pack_pixels(
                {(x, y) for x in range(3, 6) for y in range(3)},
            ),
        ),
        Region(
            id=3,
            color=_color(3),
            pixels=pack_pixels(
                {(x, y) for x in range(6, 9) for y in range(3)},
            ),
        ),
    )


def _base_calculator() -> RegionMergeCostCalculator:
    """
    Return the weighting these measurements are taken against.

    Stated here rather than left to the calculator, which no longer supplies
    one: a benchmark that does not say which weighting it measured cannot be
    compared with another run.
    """
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    )


def test_summarize_durations_reports_distribution() -> None:
    summary = summarize_durations(
        (
            0.3,
            0.1,
            0.2,
        ),
    )

    assert summary.repeat_count == 3
    assert summary.minimum_seconds == pytest.approx(
        0.1,
    )
    assert summary.median_seconds == pytest.approx(
        0.2,
    )
    assert summary.mean_seconds == pytest.approx(
        0.2,
    )
    assert summary.maximum_seconds == pytest.approx(
        0.3,
    )


def test_benchmark_initial_candidate_construction() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_initial_candidate_construction(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            repeats=3,
        )

    assert result.region_count == 2
    assert result.candidate_count == 2
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_benchmark_initial_candidate_construction_rejects_invalid_repeats() -> None:
    with pytest.raises(
        ValueError,
        match="repeats must be greater than zero",
    ):
        benchmark_initial_candidate_construction(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            repeats=0,
        )


def test_format_initial_candidate_construction_benchmark() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_initial_candidate_construction(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            repeats=3,
        )

    assert format_initial_candidate_construction_benchmark(
        case="simple",
        benchmark=result,
    ) == (
        "simple: "
        "regions=2, "
        "candidates=2, "
        "repeats=3, "
        "minimum=0.100000s, "
        "median=0.200000s, "
        "mean=0.200000s, "
        "maximum=0.300000s"
    )


def test_benchmark_incremental_adjacency_updates() -> None:
    shared_borders = {
        1: {
            2: 1,
        },
        2: {
            1: 1,
            3: 1,
        },
        3: {
            2: 1,
        },
    }

    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_incremental_adjacency_updates(
            shared_borders=shared_borders,
            merge_pairs=(
                (1, 2),
                (2, 3),
            ),
            repeats=3,
        )

    assert shared_borders == {
        1: {
            2: 1,
        },
        2: {
            1: 1,
            3: 1,
        },
        3: {
            2: 1,
        },
    }

    assert result.update_count == 2
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_build_accepted_merge_pairs_uses_actual_reducer_trace() -> None:
    merge_pairs = build_accepted_merge_pairs(
        regions=_paintable_adjacent_regions(),
        color_distance=ZeroColorDistance(),
        cost_calculator=_base_calculator(),
        minimum_circle_diameter_px=1,
        max_regions=1,
        maximum_merge_cost=1.0,
    )

    assert len(merge_pairs) == 1
    assert set(merge_pairs[0]) == {
        1,
        2,
    }


def test_benchmark_incremental_adjacency_updates_for_regions() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_incremental_adjacency_updates_for_regions(
            regions=_paintable_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            minimum_circle_diameter_px=1,
            max_regions=1,
            maximum_merge_cost=1.0,
            repeats=3,
        )

    assert result.update_count == 1
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_benchmark_incremental_candidate_maintenance() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_incremental_candidate_maintenance(
            regions=_paintable_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            merge_pairs=((1, 2),),
            repeats=3,
        )

    assert result.maintenance_count == 1
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_benchmark_incremental_candidate_maintenance_for_regions() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_incremental_candidate_maintenance_for_regions(
            regions=_paintable_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            minimum_circle_diameter_px=1,
            max_regions=1,
            maximum_merge_cost=1.0,
            repeats=3,
        )

    assert result.maintenance_count == 1
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_format_incremental_candidate_maintenance_benchmark() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_incremental_candidate_maintenance(
            regions=_paintable_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            merge_pairs=((1, 2),),
            repeats=3,
        )

    assert format_incremental_candidate_maintenance_benchmark(
        case="simple",
        benchmark=result,
    ) == (
        "simple: "
        "incremental_candidate_maintenance=1, "
        "repeats=3, "
        "minimum=0.100000s, "
        "median=0.200000s, "
        "mean=0.200000s, "
        "maximum=0.300000s"
    )


def test_benchmark_full_candidate_recalculation() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_full_candidate_recalculation(
            regions=_paintable_region_chain(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            merge_pairs=((1, 2),),
            repeats=3,
        )

    assert result.recalculation_count == 1
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_benchmark_full_candidate_recalculation_for_regions() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_full_candidate_recalculation_for_regions(
            regions=_paintable_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            minimum_circle_diameter_px=1,
            max_regions=1,
            maximum_merge_cost=1.0,
            repeats=3,
        )

    assert result.recalculation_count == 1
    assert result.timings.repeat_count == 3
    assert result.timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.timings.maximum_seconds == pytest.approx(
        0.3,
    )


def test_format_full_candidate_recalculation_benchmark() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_full_candidate_recalculation(
            regions=_paintable_region_chain(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_base_calculator(),
            merge_pairs=((1, 2),),
            repeats=3,
        )

    assert format_full_candidate_recalculation_benchmark(
        case="simple",
        benchmark=result,
    ) == (
        "simple: "
        "full_candidate_recalculation=1, "
        "repeats=3, "
        "minimum=0.100000s, "
        "median=0.200000s, "
        "mean=0.200000s, "
        "maximum=0.300000s"
    )


def test_build_parser_accepts_benchmark_configuration() -> None:
    args = build_parser().parse_args(
        [
            "--cases",
            "simple",
            "medium",
            "--repeats",
            "5",
            "--minimum-region-size-mm",
            "1.0",
            "--target-fraction",
            "0.5",
        ],
    )

    assert args.cases == [
        "simple",
        "medium",
    ]
    assert args.repeats == 5
    assert args.minimum_region_size_mm == pytest.approx(
        1.0,
    )
    assert args.target_fraction == pytest.approx(
        0.5,
    )
