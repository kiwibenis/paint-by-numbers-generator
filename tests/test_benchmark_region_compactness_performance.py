# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tools.benchmark_region_compactness_performance as performance
from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeMetrics,
)
from pbn.models.pixel_index import pack_pixels
from tools.benchmark_region_compactness_performance import (
    SourceCompactnessCalculationBenchmark,
    benchmark_source_compactness_calculation,
    benchmark_source_compactness_calculation_for_regions,
    format_source_compactness_calculation_benchmark,
)
from tools.benchmark_region_complexity_performance import DurationSummary


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


def _metrics() -> tuple[
    RegionMergeMetrics,
    RegionMergeMetrics,
]:
    return (
        RegionMergeMetrics(
            color_difference=12.0,
            source_area=20,
            target_area=80,
            merged_area=100,
            affected_area_ratio=0.2,
            shared_border_length=10,
            source_perimeter=20,
            target_perimeter=40,
            merged_perimeter=50,
        ),
        RegionMergeMetrics(
            color_difference=5.0,
            source_area=30,
            target_area=70,
            merged_area=100,
            affected_area_ratio=0.3,
            shared_border_length=6,
            source_perimeter=24,
            target_perimeter=36,
            merged_perimeter=48,
        ),
    )


def test_benchmark_source_compactness_calculation() -> None:
    with patch(
        "tools.benchmark_region_compactness_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_source_compactness_calculation(
            metrics=_metrics(),
            repeats=3,
        )

    assert result.evaluation_count == 2
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


def test_benchmark_source_compactness_calculation_for_regions() -> None:
    with patch(
        "tools.benchmark_region_compactness_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_source_compactness_calculation_for_regions(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            repeats=3,
        )

    assert result.evaluation_count == 2
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


def test_format_source_compactness_calculation_benchmark() -> None:
    benchmark = SourceCompactnessCalculationBenchmark(
        evaluation_count=20,
        timings=DurationSummary(
            repeat_count=5,
            minimum_seconds=0.001,
            median_seconds=0.002,
            mean_seconds=0.0025,
            maximum_seconds=0.004,
        ),
    )

    assert format_source_compactness_calculation_benchmark(
        case="simple",
        benchmark=benchmark,
    ) == (
        "simple: "
        "source_compactness_evaluations=20, "
        "repeats=5, "
        "minimum=0.001000s, "
        "median=0.002000s, "
        "mean=0.002500s, "
        "maximum=0.004000s, "
        "median_per_evaluation=100.000us"
    )


def test_main_reports_source_compactness_benchmark(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = SimpleNamespace(
        palette="test-palette",
        palette_version=1,
        color_distance="delta_e_2000",
        minimum_region_size_mm=1.0,
    )

    prepared = SimpleNamespace(
        regions=_adjacent_regions(),
    )

    color_distance = ZeroColorDistance()
    benchmark_result = object()

    benchmark = Mock(
        return_value=benchmark_result,
    )
    formatter = Mock(
        return_value="simple: source-compactness",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_region_compactness_performance",
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
    monkeypatch.setattr(
        performance,
        "prepare_case",
        Mock(
            return_value=prepared,
        ),
    )
    monkeypatch.setattr(
        performance,
        "benchmark_source_compactness_calculation_for_regions",
        benchmark,
    )
    monkeypatch.setattr(
        performance,
        "format_source_compactness_calculation_benchmark",
        formatter,
    )

    performance.main()

    benchmark.assert_called_once_with(
        regions=prepared.regions,
        color_distance=color_distance,
        repeats=3,
    )

    formatter.assert_called_once_with(
        case="simple",
        benchmark=benchmark_result,
    )

    assert "simple: source-compactness" in capsys.readouterr().out
