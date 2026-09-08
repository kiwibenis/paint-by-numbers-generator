# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tools.benchmark_region_neighbor_contrast_performance as performance
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
from tools.benchmark_region_complexity_performance import (
    AllNeighborColorContrastCalculationBenchmark,
    DurationSummary,
    benchmark_all_neighbor_color_contrast_calculation,
    benchmark_all_neighbor_color_contrast_calculation_for_regions,
)
from tools.benchmark_region_neighbor_contrast_performance import (
    format_all_neighbor_color_contrast_calculation_benchmark,
)


class CountingColorDistance(ColorDistance):
    def __init__(self) -> None:
        self.call_count = 0

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        self.call_count += 1

        return abs(first.l - second.l)


def _color(
    number: int,
    lightness: float,
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
            l=lightness,
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
            color=_color(
                1,
                10.0,
            ),
            pixels=pack_pixels(
                {(x, y) for x in range(3) for y in range(3)},
            ),
        ),
        Region(
            id=2,
            color=_color(
                2,
                20.0,
            ),
            pixels=pack_pixels(
                {(x, y) for x in range(3, 6) for y in range(3)},
            ),
        ),
    )


def _merge_steps() -> tuple[RegionMergeStep,]:
    return (
        RegionMergeStep(
            candidate=RegionMergeCandidate(
                source_id=1,
                target_id=2,
            ),
            metrics=RegionMergeMetrics(
                color_difference=10.0,
                source_area=9,
                target_area=9,
                merged_area=18,
                affected_area_ratio=0.5,
                shared_border_length=3,
                source_perimeter=12,
                target_perimeter=12,
                merged_perimeter=18,
            ),
            cost=RegionMergeCost(
                color_penalty=0.5,
                affected_area_penalty=0.5,
                border_penalty=0.75,
                geometry_penalty=0.0,
                value=0.5,
            ),
        ),
    )


def _cost_calculator() -> RegionMergeCostCalculator:
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    )


def test_benchmark_all_neighbor_color_contrast_calculation() -> None:
    color_distance = CountingColorDistance()

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
        result = benchmark_all_neighbor_color_contrast_calculation(
            regions=_adjacent_regions(),
            merge_steps=_merge_steps(),
            color_distance=color_distance,
            repeats=3,
        )

    assert result.evaluation_count == 1
    assert result.neighbor_measurement_count == 1

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

    assert color_distance.call_count == 3


def test_benchmark_all_neighbor_color_contrast_calculation_for_regions() -> None:
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
        result = benchmark_all_neighbor_color_contrast_calculation_for_regions(
            regions=_adjacent_regions(),
            color_distance=CountingColorDistance(),
            cost_calculator=_cost_calculator(),
            minimum_circle_diameter_px=1,
            max_regions=1,
            maximum_merge_cost=1.0,
            repeats=3,
        )

    assert result.evaluation_count == 1
    assert result.neighbor_measurement_count == 1

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


def test_format_all_neighbor_color_contrast_calculation_benchmark() -> None:
    benchmark = AllNeighborColorContrastCalculationBenchmark(
        evaluation_count=4,
        neighbor_measurement_count=20,
        timings=DurationSummary(
            repeat_count=5,
            minimum_seconds=0.001,
            median_seconds=0.002,
            mean_seconds=0.0025,
            maximum_seconds=0.004,
        ),
    )

    assert format_all_neighbor_color_contrast_calculation_benchmark(
        case="simple",
        benchmark=benchmark,
    ) == (
        "simple: "
        "all_neighbor_color_contrast_evaluations=4, "
        "neighbor_measurements=20, "
        "repeats=5, "
        "minimum=0.001000s, "
        "median=0.002000s, "
        "mean=0.002500s, "
        "maximum=0.004000s, "
        "median_per_neighbor=100.000us"
    )


def test_main_reports_all_neighbor_color_contrast_benchmark(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    merge_cost_config = object()

    config = SimpleNamespace(
        palette="test-palette",
        palette_version=1,
        color_distance="delta_e_2000",
        minimum_region_size_mm=1.0,
        region_complexity=SimpleNamespace(
            maximum_merge_cost=0.3,
            merge_cost=merge_cost_config,
        ),
    )

    prepared = SimpleNamespace(
        regions=_adjacent_regions(),
        minimum_circle_diameter_px=1,
    )

    color_distance = CountingColorDistance()
    cost_calculator = _cost_calculator()

    benchmark_result = object()

    benchmark = Mock(
        return_value=benchmark_result,
    )
    formatter = Mock(
        return_value="simple: all-neighbor-contrast",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_region_neighbor_contrast_performance",
            "--cases",
            "simple",
            "--repeats",
            "3",
        ],
    )

    monkeypatch.setattr(
        performance,
        "load_config",
        Mock(
            return_value=config,
        ),
    )
    monkeypatch.setattr(
        performance,
        "palette_path",
        Mock(
            return_value=object(),
        ),
    )
    monkeypatch.setattr(
        performance,
        "load_palette",
        Mock(
            return_value=object(),
        ),
    )
    monkeypatch.setattr(
        performance,
        "resolve_color_distance",
        Mock(
            return_value=color_distance,
        ),
    )
    build_cost_calculator = Mock(
        return_value=cost_calculator,
    )

    monkeypatch.setattr(
        performance,
        "build_region_merge_cost_calculator",
        build_cost_calculator,
    )
    monkeypatch.setattr(
        performance,
        "prepare_case",
        Mock(
            return_value=prepared,
        ),
    )
    resolve_regions = Mock(
        return_value=1,
    )

    monkeypatch.setattr(
        performance,
        "resolve_max_regions",
        resolve_regions,
    )
    monkeypatch.setattr(
        performance,
        "benchmark_all_neighbor_color_contrast_calculation_for_regions",
        benchmark,
    )
    monkeypatch.setattr(
        performance,
        "format_all_neighbor_color_contrast_calculation_benchmark",
        formatter,
    )

    performance.main()

    build_cost_calculator.assert_called_once_with(
        merge_cost_config,
    )

    resolve_regions.assert_called_once_with(
        baseline_region_count=2,
        target_fraction=0.5,
    )

    benchmark.assert_called_once_with(
        regions=prepared.regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        minimum_circle_diameter_px=1,
        max_regions=1,
        maximum_merge_cost=0.3,
        repeats=3,
    )

    formatter.assert_called_once_with(
        case="simple",
        benchmark=benchmark_result,
    )

    assert "simple: all-neighbor-contrast" in capsys.readouterr().out
