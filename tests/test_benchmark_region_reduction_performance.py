# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tools.benchmark_region_reduction_performance as performance
from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
from tools.benchmark_region_complexity_performance import DurationSummary
from tools.benchmark_region_reduction_performance import (
    OptionalComplexityReductionBenchmark,
    benchmark_optional_complexity_reduction,
    format_optional_complexity_reduction_benchmark,
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


def _cost_calculator() -> RegionMergeCostCalculator:
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    )


def test_benchmark_optional_complexity_reduction() -> None:
    with patch(
        "tools.benchmark_region_reduction_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            1.0,
            1.2,
            2.0,
            2.3,
        ),
    ):
        result = benchmark_optional_complexity_reduction(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_cost_calculator(),
            minimum_circle_diameter_px=1,
            max_regions=1,
            maximum_merge_cost=1.0,
            repeats=3,
        )

    assert result.baseline_region_count == 2
    assert result.max_regions == 1
    assert result.final_region_count == 1
    assert result.accepted_merge_count == 1

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


def test_benchmark_optional_complexity_reduction_rejects_invalid_repeats() -> None:
    with pytest.raises(
        ValueError,
        match="repeats must be greater than zero",
    ):
        benchmark_optional_complexity_reduction(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_cost_calculator(),
            minimum_circle_diameter_px=1,
            max_regions=1,
            maximum_merge_cost=1.0,
            repeats=0,
        )


def test_format_optional_complexity_reduction_benchmark() -> None:
    benchmark = OptionalComplexityReductionBenchmark(
        baseline_region_count=100,
        max_regions=50,
        final_region_count=75,
        accepted_merge_count=25,
        timings=DurationSummary(
            repeat_count=5,
            minimum_seconds=0.001,
            median_seconds=0.002,
            mean_seconds=0.0025,
            maximum_seconds=0.004,
        ),
    )

    assert format_optional_complexity_reduction_benchmark(
        case="simple",
        benchmark=benchmark,
    ) == (
        "simple: "
        "baseline_regions=100, "
        "max_regions=50, "
        "final_regions=75, "
        "accepted_merges=25, "
        "repeats=5, "
        "minimum=0.001000s, "
        "median=0.002000s, "
        "mean=0.002500s, "
        "maximum=0.004000s, "
        "median_per_merge=0.080ms"
    )


def test_main_reports_optional_complexity_reduction_benchmark(
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

    color_distance = ZeroColorDistance()
    cost_calculator = _cost_calculator()
    benchmark_result = object()

    benchmark = Mock(
        return_value=benchmark_result,
    )
    formatter = Mock(
        return_value="simple: optional-reduction",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_region_reduction_performance",
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
        "benchmark_optional_complexity_reduction",
        benchmark,
    )
    monkeypatch.setattr(
        performance,
        "format_optional_complexity_reduction_benchmark",
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

    assert "simple: optional-reduction" in capsys.readouterr().out
