# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from unittest.mock import patch

import pytest

import tools.benchmark_region_complexity_downstream_performance as performance
from pbn.models import (
    RGB,
    Lab,
    Outline,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from tools.benchmark_region_complexity_downstream_performance import (
    OutlineSetStats,
    PairedStageBenchmark,
    RegionSetStats,
    benchmark_label_placement,
    benchmark_outline_simplification,
    format_outline_set_stats,
    format_paired_stage_benchmark,
    format_region_set_stats,
    summarize_outline_set,
    summarize_region_set,
)
from tools.benchmark_region_complexity_performance import (
    DurationSummary,
)


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


def _region(
    region_id: int,
    pixels: frozenset[tuple[int, int]],
) -> Region:
    return Region(
        id=region_id,
        color=_color(
            region_id,
        ),
        pixels=pack_pixels(
            pixels,
        ),
    )


def _mandatory_regions() -> tuple[
    Region,
    ...,
]:
    return (
        _region(
            1,
            frozenset(
                {
                    (0, 0),
                    (1, 0),
                    (0, 1),
                    (1, 1),
                },
            ),
        ),
        _region(
            2,
            frozenset(
                {
                    (3, 0),
                    (5, 0),
                    (3, 2),
                },
            ),
        ),
    )


def _reduced_regions() -> tuple[
    Region,
    ...,
]:
    return (
        _region(
            3,
            frozenset(
                {
                    (0, 0),
                    (1, 0),
                    (0, 1),
                    (1, 1),
                    (3, 0),
                    (5, 0),
                    (3, 2),
                },
            ),
        ),
    )


def test_summarize_region_set() -> None:
    result = summarize_region_set(
        _mandatory_regions(),
    )

    assert result == RegionSetStats(
        region_count=2,
        total_pixel_count=7,
        maximum_region_pixel_count=4,
        total_bounding_box_area=13,
        maximum_bounding_box_area=9,
    )


def test_summarize_region_set_rejects_empty_regions() -> None:
    with pytest.raises(
        ValueError,
        match="regions must not be empty",
    ):
        summarize_region_set(
            (),
        )


def test_summarize_outline_set() -> None:
    outlines = (
        Outline(
            region_id=1,
            points=(
                (0, 0),
                (2, 0),
                (2, 2),
                (0, 2),
            ),
            hole_rings=(
                (
                    (1, 1),
                    (2, 1),
                    (1, 2),
                ),
            ),
        ),
        Outline(
            region_id=2,
            points=(
                (3, 0),
                (4, 0),
                (4, 1),
            ),
        ),
    )

    assert summarize_outline_set(
        outlines,
    ) == OutlineSetStats(
        outline_count=2,
        hole_count=1,
        outer_vertex_count=7,
        hole_vertex_count=3,
        total_vertex_count=10,
        maximum_region_vertex_count=7,
    )


def test_benchmark_label_placement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    class FakeLabelPlacer:
        def place(
            self,
            regions: tuple[
                Region,
                ...,
            ],
        ) -> tuple[
            object,
            ...,
        ]:
            calls.append(
                len(regions),
            )

            return tuple(object() for _ in regions)

    monkeypatch.setattr(
        performance,
        "LabelPlacer",
        FakeLabelPlacer,
    )

    with patch(
        "tools.benchmark_region_complexity_downstream_performance." "perf_counter",
        side_effect=(
            0.0,
            1.0,
            10.0,
            13.0,
        ),
    ):
        result = benchmark_label_placement(
            mandatory_regions=(_mandatory_regions()),
            reduced_regions=(_reduced_regions()),
            repeats=1,
        )

    assert calls == [
        2,
        1,
    ]

    assert result.mandatory_timings.median_seconds == pytest.approx(
        1.0,
    )

    assert result.reduced_timings.median_seconds == pytest.approx(
        3.0,
    )

    assert result.median_delta_seconds == pytest.approx(
        2.0,
    )

    assert result.median_delta_fraction == pytest.approx(
        2.0,
    )

    assert result.reduced_to_mandatory_ratio == pytest.approx(
        3.0,
    )


def test_benchmark_outline_simplification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[
        tuple[
            int,
            float,
        ]
    ] = []

    class FakeOutlineTopologySimplifier:
        def simplify(
            self,
            regions: tuple[
                Region,
                ...,
            ],
            *,
            tolerance: float,
        ) -> tuple[
            Outline,
            ...,
        ]:
            calls.append(
                (
                    len(regions),
                    tolerance,
                ),
            )

            if len(regions) == 2:
                return (
                    Outline(
                        region_id=1,
                        points=(
                            (0, 0),
                            (1, 0),
                            (0, 1),
                        ),
                    ),
                    Outline(
                        region_id=2,
                        points=(
                            (2, 0),
                            (3, 0),
                            (2, 1),
                        ),
                    ),
                )

            return (
                Outline(
                    region_id=3,
                    points=(
                        (0, 0),
                        (3, 0),
                        (3, 3),
                        (0, 3),
                    ),
                    hole_rings=(
                        (
                            (1, 1),
                            (2, 1),
                            (1, 2),
                        ),
                    ),
                ),
            )

    monkeypatch.setattr(
        performance,
        "OutlineTopologySimplifier",
        FakeOutlineTopologySimplifier,
    )

    with patch(
        "tools.benchmark_region_complexity_downstream_performance." "perf_counter",
        side_effect=(
            0.0,
            2.0,
            10.0,
            15.0,
        ),
    ):
        result = benchmark_outline_simplification(
            mandatory_regions=(_mandatory_regions()),
            reduced_regions=(_reduced_regions()),
            tolerance=1.5,
            repeats=1,
        )

    assert calls == [
        (2, 1.5),
        (1, 1.5),
    ]

    assert result.timings.mandatory_timings.median_seconds == pytest.approx(
        2.0,
    )

    assert result.timings.reduced_timings.median_seconds == pytest.approx(
        5.0,
    )

    assert result.mandatory_stats == OutlineSetStats(
        outline_count=2,
        hole_count=0,
        outer_vertex_count=6,
        hole_vertex_count=0,
        total_vertex_count=6,
        maximum_region_vertex_count=3,
    )

    assert result.reduced_stats == OutlineSetStats(
        outline_count=1,
        hole_count=1,
        outer_vertex_count=4,
        hole_vertex_count=3,
        total_vertex_count=7,
        maximum_region_vertex_count=7,
    )


def test_benchmarks_reject_invalid_repeat_count() -> None:
    with pytest.raises(
        ValueError,
        match="repeats must be greater than zero",
    ):
        benchmark_label_placement(
            mandatory_regions=(_mandatory_regions()),
            reduced_regions=(_reduced_regions()),
            repeats=0,
        )

    with pytest.raises(
        ValueError,
        match="repeats must be greater than zero",
    ):
        benchmark_outline_simplification(
            mandatory_regions=(_mandatory_regions()),
            reduced_regions=(_reduced_regions()),
            tolerance=1.0,
            repeats=0,
        )


def test_format_region_set_stats() -> None:
    assert format_region_set_stats(
        name="mandatory",
        stats=RegionSetStats(
            region_count=10,
            total_pixel_count=1000,
            maximum_region_pixel_count=400,
            total_bounding_box_area=1500,
            maximum_bounding_box_area=700,
        ),
    ) == (
        "mandatory: "
        "regions=10, "
        "total_pixels=1000, "
        "max_region_pixels=400, "
        "total_bbox_area=1500, "
        "max_bbox_area=700"
    )


def test_format_outline_set_stats() -> None:
    assert format_outline_set_stats(
        name="reduced",
        stats=OutlineSetStats(
            outline_count=5,
            hole_count=2,
            outer_vertex_count=20,
            hole_vertex_count=6,
            total_vertex_count=26,
            maximum_region_vertex_count=9,
        ),
    ) == (
        "reduced: "
        "outlines=5, "
        "holes=2, "
        "outer_vertices=20, "
        "hole_vertices=6, "
        "total_vertices=26, "
        "max_region_vertices=9"
    )


def test_format_paired_stage_benchmark() -> None:
    benchmark = PairedStageBenchmark(
        mandatory_timings=DurationSummary(
            repeat_count=3,
            minimum_seconds=9.0,
            median_seconds=10.0,
            mean_seconds=10.0,
            maximum_seconds=11.0,
        ),
        reduced_timings=DurationSummary(
            repeat_count=3,
            minimum_seconds=19.0,
            median_seconds=20.0,
            mean_seconds=20.0,
            maximum_seconds=21.0,
        ),
    )

    assert format_paired_stage_benchmark(
        name="outline",
        benchmark=benchmark,
    ) == (
        "outline: "
        "repeats=3, "
        "mandatory_median=10.000000s, "
        "reduced_median=20.000000s, "
        "delta=+10.000000s, "
        "delta_percent=+100.00%, "
        "reduced_to_mandatory=2.000x"
    )


def test_parser_defaults_to_single_complex_diagnostic_run() -> None:
    args = performance.build_parser().parse_args(
        [],
    )

    assert args.minimum_region_size_mm is None
    assert args.target_fraction == pytest.approx(
        0.5,
    )
    assert args.repeats == 1


def test_the_paintability_minimum_is_left_to_the_profile() -> None:
    """
    The default was `1.0` while the shipped profile said `2.0`, and it was
    applied to the loaded profile unconditionally, so a run without
    arguments measured half the shipped paintability.

    `None` is the whole rule: the profile answers, unless the caller says
    otherwise in a command that then records what was measured.
    """
    assert (
        performance.build_parser()
        .parse_args(
            [],
        )
        .minimum_region_size_mm
        is None
    )

    assert performance.build_parser().parse_args(
        [
            "--minimum-region-size-mm",
            "1.0",
        ],
    ).minimum_region_size_mm == pytest.approx(
        1.0,
    )
