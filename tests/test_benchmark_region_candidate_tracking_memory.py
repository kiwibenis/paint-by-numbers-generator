# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tools.benchmark_region_candidate_tracking_memory as performance
from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
from tools.benchmark_region_candidate_tracking_memory import (
    CandidateTrackingMemoryBenchmark,
    MemorySummary,
    benchmark_candidate_tracking_memory,
    build_candidate_evaluation_cache,
    format_candidate_tracking_memory_benchmark,
    summarize_memory,
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


def test_summarize_memory() -> None:
    result = summarize_memory(
        (
            3000,
            1000,
            2000,
        ),
    )

    assert result.repeat_count == 3
    assert result.minimum_bytes == 1000
    assert result.median_bytes == 2000
    assert result.mean_bytes == 2000
    assert result.maximum_bytes == 3000


def test_build_candidate_evaluation_cache() -> None:
    result = build_candidate_evaluation_cache(
        regions=_adjacent_regions(),
        color_distance=ZeroColorDistance(),
        cost_calculator=_cost_calculator(),
    )

    assert len(result) == 2

    assert {
        (
            candidate.source_id,
            candidate.target_id,
        )
        for candidate in result
    } == {
        (1, 2),
        (2, 1),
    }

    assert all(evaluation[0] is candidate for candidate, evaluation in result.items())


def test_benchmark_candidate_tracking_memory() -> None:
    with (
        patch(
            "tools.benchmark_region_candidate_tracking_memory.gc.collect",
        ),
        patch(
            "tools.benchmark_region_candidate_tracking_memory." "tracemalloc.start",
        ),
        patch(
            "tools.benchmark_region_candidate_tracking_memory." "tracemalloc.stop",
        ),
        patch(
            "tools.benchmark_region_candidate_tracking_memory."
            "tracemalloc.get_traced_memory",
            side_effect=(
                (100, 100),
                (1100, 1300),
                (200, 200),
                (2200, 2500),
                (300, 300),
                (3300, 4000),
            ),
        ),
    ):
        result = benchmark_candidate_tracking_memory(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_cost_calculator(),
            repeats=3,
        )

    assert result.candidate_count == 2

    assert result.retained_memory.repeat_count == 3
    assert result.retained_memory.minimum_bytes == 1000
    assert result.retained_memory.median_bytes == 2000
    assert result.retained_memory.mean_bytes == 2000
    assert result.retained_memory.maximum_bytes == 3000

    assert result.median_bytes_per_candidate == pytest.approx(
        1000.0,
    )


def test_benchmark_candidate_tracking_memory_rejects_invalid_repeats() -> None:
    with pytest.raises(
        ValueError,
        match="repeats must be greater than zero",
    ):
        benchmark_candidate_tracking_memory(
            regions=_adjacent_regions(),
            color_distance=ZeroColorDistance(),
            cost_calculator=_cost_calculator(),
            repeats=0,
        )


def test_format_candidate_tracking_memory_benchmark() -> None:
    benchmark = CandidateTrackingMemoryBenchmark(
        candidate_count=20,
        retained_memory=MemorySummary(
            repeat_count=5,
            minimum_bytes=1000,
            median_bytes=2000,
            mean_bytes=2500,
            maximum_bytes=4000,
        ),
    )

    assert format_candidate_tracking_memory_benchmark(
        case="simple",
        benchmark=benchmark,
    ) == (
        "simple: "
        "candidate_evaluations=20, "
        "repeats=5, "
        "retained_min=1000B, "
        "retained_median=2000B, "
        "retained_mean=2500B, "
        "retained_max=4000B, "
        "retained_median=0.002MiB, "
        "retained_bytes_per_candidate=100.0B"
    )


def test_main_reports_candidate_tracking_memory_benchmark(
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
            merge_cost=merge_cost_config,
        ),
    )

    prepared = SimpleNamespace(
        regions=_adjacent_regions(),
    )

    color_distance = ZeroColorDistance()
    cost_calculator = _cost_calculator()
    benchmark_result = object()

    benchmark = Mock(
        return_value=benchmark_result,
    )
    formatter = Mock(
        return_value="simple: candidate-memory",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_region_candidate_tracking_memory",
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
    monkeypatch.setattr(
        performance,
        "benchmark_candidate_tracking_memory",
        benchmark,
    )
    monkeypatch.setattr(
        performance,
        "format_candidate_tracking_memory_benchmark",
        formatter,
    )

    performance.main()

    build_cost_calculator.assert_called_once_with(
        merge_cost_config,
    )

    benchmark.assert_called_once_with(
        regions=prepared.regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        repeats=3,
    )

    formatter.assert_called_once_with(
        case="simple",
        benchmark=benchmark_result,
    )

    assert "simple: candidate-memory" in capsys.readouterr().out
