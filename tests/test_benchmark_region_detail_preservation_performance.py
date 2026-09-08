# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tools.benchmark_region_complexity_performance as performance
from pbn.color.color_distance import ColorDistance
from pbn.config import RegionMergeCostConfig
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeMetrics,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_cost_calculator import (
    DetailPreservingRegionMergeCostCalculator,
    RegionMergeCostCalculator,
)
from tools.benchmark_region_complexity_performance import (
    benchmark_detail_preservation_cost_calculation,
    benchmark_detail_preservation_cost_calculation_for_regions,
    build_base_region_merge_cost_calculator,
    format_detail_preservation_cost_calculation_benchmark,
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


def _merge_cost_config() -> RegionMergeCostConfig:
    return RegionMergeCostConfig(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )


def _base_calculator() -> RegionMergeCostCalculator:
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    )


def _detail_calculator() -> DetailPreservingRegionMergeCostCalculator:
    return DetailPreservingRegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )


def test_build_base_region_merge_cost_calculator() -> None:
    calculator = build_base_region_merge_cost_calculator(
        _merge_cost_config(),
    )

    metric = _metrics()[0]

    assert calculator.calculate(
        metric,
    ) == _base_calculator().calculate(
        metric,
    )


def test_benchmark_detail_preservation_cost_calculation() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            0.2,
            0.4,
            1.0,
            1.2,
            1.4,
            1.7,
            2.0,
            2.3,
            2.5,
            2.9,
        ),
    ):
        result = benchmark_detail_preservation_cost_calculation(
            metrics=_metrics(),
            base_calculator=_base_calculator(),
            detail_calculator=_detail_calculator(),
            repeats=3,
        )

    assert result.evaluation_count == 2

    assert result.base_timings.repeat_count == 3
    assert result.base_timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.base_timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.base_timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.base_timings.maximum_seconds == pytest.approx(
        0.3,
    )

    assert result.detail_timings.repeat_count == 3
    assert result.detail_timings.minimum_seconds == pytest.approx(
        0.2,
    )
    assert result.detail_timings.median_seconds == pytest.approx(
        0.3,
    )
    assert result.detail_timings.mean_seconds == pytest.approx(
        0.3,
    )
    assert result.detail_timings.maximum_seconds == pytest.approx(
        0.4,
    )


def test_benchmark_detail_preservation_cost_calculation_for_regions() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            0.2,
            0.4,
            1.0,
            1.2,
            1.4,
            1.7,
            2.0,
            2.3,
            2.5,
            2.9,
        ),
    ):
        result = benchmark_detail_preservation_cost_calculation_for_regions(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            base_calculator=_base_calculator(),
            detail_calculator=_detail_calculator(),
            repeats=3,
        )

    assert result.evaluation_count == 2

    assert result.base_timings.repeat_count == 3
    assert result.base_timings.minimum_seconds == pytest.approx(
        0.1,
    )
    assert result.base_timings.median_seconds == pytest.approx(
        0.2,
    )
    assert result.base_timings.mean_seconds == pytest.approx(
        0.2,
    )
    assert result.base_timings.maximum_seconds == pytest.approx(
        0.3,
    )

    assert result.detail_timings.repeat_count == 3
    assert result.detail_timings.minimum_seconds == pytest.approx(
        0.2,
    )
    assert result.detail_timings.median_seconds == pytest.approx(
        0.3,
    )
    assert result.detail_timings.mean_seconds == pytest.approx(
        0.3,
    )
    assert result.detail_timings.maximum_seconds == pytest.approx(
        0.4,
    )


def test_format_detail_preservation_cost_calculation_benchmark() -> None:
    with patch(
        "tools.benchmark_region_complexity_performance.perf_counter",
        side_effect=(
            0.0,
            0.1,
            0.2,
            0.4,
            1.0,
            1.2,
            1.4,
            1.7,
            2.0,
            2.3,
            2.5,
            2.9,
        ),
    ):
        result = benchmark_detail_preservation_cost_calculation(
            metrics=_metrics(),
            base_calculator=_base_calculator(),
            detail_calculator=_detail_calculator(),
            repeats=3,
        )

    assert format_detail_preservation_cost_calculation_benchmark(
        case="simple",
        benchmark=result,
    ) == (
        "simple: "
        "detail_preservation_evaluations=2, "
        "repeats=3, "
        "base_median=0.200000s, "
        "detail_median=0.300000s, "
        "median_overhead=0.100000s, "
        "detail_to_base=1.500x"
    )


def test_main_reports_detail_preservation_cost_benchmark(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    merge_cost_config = _merge_cost_config()

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
    base_calculator = _base_calculator()
    detail_calculator = _detail_calculator()

    detail_result = object()

    build_base_calculator = Mock(
        return_value=base_calculator,
    )
    detail_benchmark = Mock(
        return_value=detail_result,
    )
    detail_formatter = Mock(
        return_value="simple: detail-preservation-benchmark",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_region_complexity_performance",
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
        "build_region_merge_cost_calculator",
        Mock(
            return_value=detail_calculator,
        ),
    )
    monkeypatch.setattr(
        performance,
        "build_base_region_merge_cost_calculator",
        build_base_calculator,
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
        "resolve_max_regions",
        Mock(
            return_value=1,
        ),
    )

    monkeypatch.setattr(
        performance,
        "benchmark_initial_candidate_construction",
        Mock(
            return_value=object(),
        ),
    )
    monkeypatch.setattr(
        performance,
        "format_initial_candidate_construction_benchmark",
        Mock(
            return_value="simple: initial-candidates",
        ),
    )

    monkeypatch.setattr(
        performance,
        "benchmark_incremental_adjacency_updates_for_regions",
        Mock(
            return_value=object(),
        ),
    )
    monkeypatch.setattr(
        performance,
        "format_incremental_adjacency_update_benchmark",
        Mock(
            return_value="simple: adjacency",
        ),
    )

    monkeypatch.setattr(
        performance,
        "benchmark_incremental_candidate_maintenance_for_regions",
        Mock(
            return_value=object(),
        ),
    )
    monkeypatch.setattr(
        performance,
        "format_incremental_candidate_maintenance_benchmark",
        Mock(
            return_value="simple: candidate-maintenance",
        ),
    )

    monkeypatch.setattr(
        performance,
        "benchmark_full_candidate_recalculation_for_regions",
        Mock(
            return_value=object(),
        ),
    )
    monkeypatch.setattr(
        performance,
        "format_full_candidate_recalculation_benchmark",
        Mock(
            return_value="simple: full-recalculation",
        ),
    )

    monkeypatch.setattr(
        performance,
        "benchmark_detail_preservation_cost_calculation_for_regions",
        detail_benchmark,
    )
    monkeypatch.setattr(
        performance,
        "format_detail_preservation_cost_calculation_benchmark",
        detail_formatter,
    )

    performance.main()

    build_base_calculator.assert_called_once_with(
        merge_cost_config,
    )

    detail_benchmark.assert_called_once_with(
        regions=prepared.regions,
        color_distance=color_distance,
        base_calculator=base_calculator,
        detail_calculator=detail_calculator,
        repeats=3,
    )

    detail_formatter.assert_called_once_with(
        case="simple",
        benchmark=detail_result,
    )

    assert "simple: detail-preservation-benchmark" in capsys.readouterr().out
