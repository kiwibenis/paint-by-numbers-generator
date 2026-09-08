# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import os
import pickle
import sys

import pytest

from pbn.models import RGB, InputImage, Palette
from tools import benchmark_quantization


def create_calibration_result(
    *,
    unique_rgb_count: int,
    sequential_seconds: float,
    parallel_seconds: float,
    worker_count: int = 4,
) -> benchmark_quantization.QuantizationBenchmarkResult:
    return benchmark_quantization.QuantizationBenchmarkResult(
        case="calibration",
        pixel_count=unique_rgb_count,
        unique_rgb_count=unique_rgb_count,
        serialized_payload_bytes=1,
        quantization_durations_seconds=(sequential_seconds,),
        process_startup_durations_seconds=(0.1,),
        process_transfer_durations_seconds=(0.01,),
        worker_results=(
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=1,
                durations_seconds=(sequential_seconds,),
            ),
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=worker_count,
                durations_seconds=(parallel_seconds,),
            ),
        ),
    )


def create_worker_scaling_result(
    *,
    unique_rgb_count: int,
    worker_durations: tuple[
        tuple[int, float],
        ...,
    ],
) -> benchmark_quantization.QuantizationBenchmarkResult:
    sequential_seconds = next(
        duration for worker_count, duration in worker_durations if worker_count == 1
    )

    return benchmark_quantization.QuantizationBenchmarkResult(
        case="calibration",
        pixel_count=unique_rgb_count,
        unique_rgb_count=unique_rgb_count,
        serialized_payload_bytes=1,
        quantization_durations_seconds=(sequential_seconds,),
        process_startup_durations_seconds=(0.1,),
        process_transfer_durations_seconds=(0.01,),
        worker_results=tuple(
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=worker_count,
                durations_seconds=(duration,),
            )
            for worker_count, duration in worker_durations
        ),
    )


def create_worker_scaling_point(
    *,
    palette_color_count: int,
    worker_durations: tuple[
        tuple[int, float],
        ...,
    ],
    unique_rgb_count: int = 10_000,
) -> benchmark_quantization.QuantizationCalibrationPoint:
    return benchmark_quantization.QuantizationCalibrationPoint(
        palette_color_count=palette_color_count,
        result=create_worker_scaling_result(
            unique_rgb_count=unique_rgb_count,
            worker_durations=worker_durations,
        ),
    )


def test_calibration_case_uses_established_unique_rgb_workload() -> None:
    assert benchmark_quantization.CALIBRATION_CASE == (
        benchmark_quantization.QuantizationBenchmarkCase(
            name="calibration",
            width=1024,
            height=1024,
            unique_rgb_count=16_384,
        )
    )


def test_calibration_palette_counts_cover_8_to_160_in_steps_of_two() -> None:
    assert benchmark_quantization.CALIBRATION_PALETTE_COLOR_COUNTS == tuple(
        range(
            8,
            161,
            2,
        ),
    )


def test_calibration_palette_counts_have_expected_number_of_points() -> None:
    assert (
        len(
            benchmark_quantization.CALIBRATION_PALETTE_COLOR_COUNTS,
        )
        == 77
    )


def test_calibration_uses_delta_e_2000() -> None:
    assert benchmark_quantization.CALIBRATION_COLOR_DISTANCE == "delta_e_2000"


def test_calibration_uses_meaningful_parallel_speedup() -> None:
    assert benchmark_quantization.MIN_RECOMMENDED_PARALLEL_SPEEDUP == 1.25


def test_calibration_uses_meaningful_incremental_worker_speedup() -> None:
    assert benchmark_quantization.MIN_RECOMMENDED_WORKER_SPEEDUP == 1.05


def test_calibration_requires_stable_worker_scaling_points() -> None:
    assert benchmark_quantization.MIN_RECOMMENDED_WORKER_STABLE_POINTS == 3


def test_calibration_defaults_to_sixteen_workers() -> None:
    assert benchmark_quantization.DEFAULT_MAX_WORKER_COUNT == 16


def test_build_calibration_palette_uses_requested_color_count() -> None:
    palette = benchmark_quantization.build_calibration_palette(
        color_count=32,
    )

    assert palette.id == "benchmark32"
    assert palette.display_name == "Benchmark 32"
    assert len(palette.colors) == 32


def test_build_calibration_palette_rejects_non_positive_color_count() -> None:
    with pytest.raises(
        ValueError,
        match="palette color count must be greater than zero",
    ):
        benchmark_quantization.build_calibration_palette(
            color_count=0,
        )


def test_build_calibration_palette_is_prefix_stable() -> None:
    smaller = benchmark_quantization.build_calibration_palette(
        color_count=8,
    )
    larger = benchmark_quantization.build_calibration_palette(
        color_count=10,
    )

    assert larger.colors[:8] == smaller.colors


def test_build_input_image_uses_requested_dimensions() -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=3,
        height=2,
        unique_rgb_count=4,
    )

    image = benchmark_quantization.build_input_image(
        case,
    )

    assert image.width == 3
    assert image.height == 2
    assert len(tuple(image.rows())) == 2
    assert all(len(row) == 3 for row in tuple(image.rows()))


def test_build_input_image_uses_requested_unique_rgb_count() -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=4,
        height=3,
        unique_rgb_count=5,
    )

    image = benchmark_quantization.build_input_image(
        case,
    )

    unique_colors = {rgb for row in tuple(image.rows()) for rgb in row}

    assert len(unique_colors) == 5


def test_build_input_image_rejects_non_positive_dimensions() -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=0,
        height=1,
        unique_rgb_count=1,
    )

    with pytest.raises(
        ValueError,
        match="benchmark dimensions must be greater than zero",
    ):
        benchmark_quantization.build_input_image(
            case,
        )


def test_build_input_image_rejects_non_positive_unique_rgb_count() -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=1,
        height=1,
        unique_rgb_count=0,
    )

    with pytest.raises(
        ValueError,
        match="unique_rgb_count must be greater than zero",
    ):
        benchmark_quantization.build_input_image(
            case,
        )


def test_build_input_image_rejects_unique_count_above_pixel_count() -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=2,
        height=2,
        unique_rgb_count=5,
    )

    with pytest.raises(
        ValueError,
        match="unique_rgb_count must not exceed pixel count",
    ):
        benchmark_quantization.build_input_image(
            case,
        )


def test_build_unique_rgb_payload_preserves_first_seen_order() -> None:
    first = RGB(
        red=1,
        green=2,
        blue=3,
    )
    second = RGB(
        red=4,
        green=5,
        blue=6,
    )
    third = RGB(
        red=7,
        green=8,
        blue=9,
    )

    image = InputImage.from_rows(
        (
            (
                first,
                second,
                first,
            ),
            (
                third,
                second,
                first,
            ),
        )
    )

    payload = benchmark_quantization.build_unique_rgb_payload(
        image,
    )

    assert payload == (
        (
            1,
            2,
            3,
        ),
        (
            4,
            5,
            6,
        ),
        (
            7,
            8,
            9,
        ),
    )


def test_serialized_size_bytes_measures_highest_pickle_protocol() -> None:
    payload = (
        (
            1,
            2,
            3,
        ),
        (
            4,
            5,
            6,
        ),
    )

    expected_size = len(
        pickle.dumps(
            payload,
            protocol=pickle.HIGHEST_PROTOCOL,
        ),
    )

    assert (
        benchmark_quantization.serialized_size_bytes(
            payload,
        )
        == expected_size
    )


def test_roundtrip_payload_preserves_payload() -> None:
    payload = (
        (
            1,
            2,
            3,
        ),
        (
            4,
            5,
            6,
        ),
    )

    assert (
        benchmark_quantization.roundtrip_payload(
            payload,
        )
        == payload
    )


def test_build_worker_counts_uses_bounded_scaling_sequence() -> None:
    assert benchmark_quantization.build_worker_counts(
        available_cpu_count=32,
        work_unit_count=16_384,
        max_worker_count=16,
    ) == (
        1,
        2,
        4,
        8,
        16,
    )


def test_build_worker_counts_respects_available_cpu_count() -> None:
    assert benchmark_quantization.build_worker_counts(
        available_cpu_count=12,
        work_unit_count=16_384,
        max_worker_count=16,
    ) == (
        1,
        2,
        4,
        8,
        12,
    )


def test_build_worker_counts_respects_work_unit_count() -> None:
    assert benchmark_quantization.build_worker_counts(
        available_cpu_count=16,
        work_unit_count=3,
        max_worker_count=16,
    ) == (
        1,
        2,
        3,
    )


def test_build_worker_counts_falls_back_to_one_cpu() -> None:
    assert benchmark_quantization.build_worker_counts(
        available_cpu_count=None,
        work_unit_count=16_384,
        max_worker_count=16,
    ) == (1,)


def test_build_worker_counts_rejects_non_positive_work_unit_count() -> None:
    with pytest.raises(
        ValueError,
        match="work_unit_count must be greater than zero",
    ):
        benchmark_quantization.build_worker_counts(
            available_cpu_count=16,
            work_unit_count=0,
            max_worker_count=16,
        )


def test_build_worker_counts_rejects_non_positive_maximum() -> None:
    with pytest.raises(
        ValueError,
        match="max_worker_count must be greater than zero",
    ):
        benchmark_quantization.build_worker_counts(
            available_cpu_count=16,
            work_unit_count=16_384,
            max_worker_count=0,
        )


def test_worker_result_reports_median_duration() -> None:
    result = benchmark_quantization.QuantizationWorkerBenchmarkResult(
        worker_count=4,
        durations_seconds=(
            3.0,
            1.0,
            2.0,
        ),
    )

    assert result.median_seconds == 2.0


def test_calibration_point_calculates_estimated_workload() -> None:
    result = create_calibration_result(
        unique_rgb_count=16_384,
        sequential_seconds=1.25,
        parallel_seconds=1.0,
    )

    point = benchmark_quantization.QuantizationCalibrationPoint(
        palette_color_count=52,
        result=result,
    )

    assert point.estimated_workload == 851_968


def test_calibration_point_reports_best_parallel_speedup() -> None:
    result = benchmark_quantization.QuantizationBenchmarkResult(
        case="calibration",
        pixel_count=100,
        unique_rgb_count=100,
        serialized_payload_bytes=1,
        quantization_durations_seconds=(1.6,),
        process_startup_durations_seconds=(0.1,),
        process_transfer_durations_seconds=(0.01,),
        worker_results=(
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=1,
                durations_seconds=(1.6,),
            ),
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=2,
                durations_seconds=(1.2,),
            ),
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=4,
                durations_seconds=(1.0,),
            ),
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=8,
                durations_seconds=(1.1,),
            ),
        ),
    )

    point = benchmark_quantization.QuantizationCalibrationPoint(
        palette_color_count=60,
        result=result,
    )

    assert point.best_parallel_speedup == pytest.approx(
        1.6,
    )


def test_calibration_point_reports_zero_without_parallel_result() -> None:
    result = benchmark_quantization.QuantizationBenchmarkResult(
        case="calibration",
        pixel_count=100,
        unique_rgb_count=100,
        serialized_payload_bytes=1,
        quantization_durations_seconds=(1.0,),
        process_startup_durations_seconds=(0.1,),
        process_transfer_durations_seconds=(0.01,),
        worker_results=(
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=1,
                durations_seconds=(1.0,),
            ),
        ),
    )

    point = benchmark_quantization.QuantizationCalibrationPoint(
        palette_color_count=60,
        result=result,
    )

    assert point.best_parallel_speedup == 0.0


def test_recommend_parallel_break_even_requires_stable_speedup() -> None:
    points = (
        benchmark_quantization.QuantizationCalibrationPoint(
            palette_color_count=40,
            result=create_calibration_result(
                unique_rgb_count=10_000,
                sequential_seconds=1.30,
                parallel_seconds=1.0,
            ),
        ),
        benchmark_quantization.QuantizationCalibrationPoint(
            palette_color_count=60,
            result=create_calibration_result(
                unique_rgb_count=10_000,
                sequential_seconds=1.20,
                parallel_seconds=1.0,
            ),
        ),
        benchmark_quantization.QuantizationCalibrationPoint(
            palette_color_count=90,
            result=create_calibration_result(
                unique_rgb_count=10_000,
                sequential_seconds=1.25,
                parallel_seconds=1.0,
            ),
        ),
        benchmark_quantization.QuantizationCalibrationPoint(
            palette_color_count=100,
            result=create_calibration_result(
                unique_rgb_count=10_000,
                sequential_seconds=1.30,
                parallel_seconds=1.0,
            ),
        ),
    )

    recommendation = benchmark_quantization.recommend_parallel_break_even(
        points,
    )

    assert recommendation == 900_000


def test_recommend_parallel_break_even_returns_none_without_stable_gain() -> None:
    points = (
        benchmark_quantization.QuantizationCalibrationPoint(
            palette_color_count=40,
            result=create_calibration_result(
                unique_rgb_count=10_000,
                sequential_seconds=1.20,
                parallel_seconds=1.0,
            ),
        ),
        benchmark_quantization.QuantizationCalibrationPoint(
            palette_color_count=60,
            result=create_calibration_result(
                unique_rgb_count=10_000,
                sequential_seconds=1.24,
                parallel_seconds=1.0,
            ),
        ),
    )

    recommendation = benchmark_quantization.recommend_parallel_break_even(
        points,
    )

    assert recommendation is None


def test_recommend_parallel_break_even_accepts_exact_speedup_boundary() -> None:
    point = benchmark_quantization.QuantizationCalibrationPoint(
        palette_color_count=50,
        result=create_calibration_result(
            unique_rgb_count=10_000,
            sequential_seconds=1.25,
            parallel_seconds=1.0,
        ),
    )

    recommendation = benchmark_quantization.recommend_parallel_break_even(
        (point,),
    )

    assert recommendation == 500_000


def test_recommend_parallel_max_workers_selects_highest_stable_gain() -> None:
    points = tuple(
        create_worker_scaling_point(
            palette_color_count=palette_color_count,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.88,
                ),
            ),
        )
        for palette_color_count in (
            40,
            50,
            60,
            70,
        )
    )

    recommendation = benchmark_quantization.recommend_parallel_max_workers(
        points,
        parallel_break_even_workload=400_000,
    )

    assert recommendation == 8


def test_recommend_parallel_max_workers_accepts_stable_higher_worker_gain() -> None:
    points = tuple(
        create_worker_scaling_point(
            palette_color_count=palette_color_count,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.80,
                ),
            ),
        )
        for palette_color_count in (
            40,
            50,
            60,
        )
    )

    recommendation = benchmark_quantization.recommend_parallel_max_workers(
        points,
        parallel_break_even_workload=400_000,
    )

    assert recommendation == 12


def test_recommend_parallel_max_workers_rejects_single_higher_worker_spike() -> None:
    points = (
        create_worker_scaling_point(
            palette_color_count=40,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.80,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=50,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.89,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=60,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.89,
                ),
            ),
        ),
    )

    recommendation = benchmark_quantization.recommend_parallel_max_workers(
        points,
        parallel_break_even_workload=400_000,
    )

    assert recommendation == 8


def test_recommend_parallel_max_workers_ignores_pre_break_even_points() -> None:
    points = (
        create_worker_scaling_point(
            palette_color_count=10,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.70,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=20,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.70,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=30,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.70,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=40,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.88,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=50,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.88,
                ),
            ),
        ),
        create_worker_scaling_point(
            palette_color_count=60,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    12,
                    0.88,
                ),
            ),
        ),
    )

    recommendation = benchmark_quantization.recommend_parallel_max_workers(
        points,
        parallel_break_even_workload=400_000,
    )

    assert recommendation == 8


def test_recommend_parallel_max_workers_returns_none_without_stable_gain() -> None:
    points = tuple(
        create_worker_scaling_point(
            palette_color_count=palette_color_count,
            worker_durations=(
                (
                    1,
                    1.0,
                ),
                (
                    2,
                    0.97,
                ),
                (
                    4,
                    0.95,
                ),
                (
                    8,
                    0.94,
                ),
            ),
        )
        for palette_color_count in (
            40,
            50,
            60,
        )
    )

    recommendation = benchmark_quantization.recommend_parallel_max_workers(
        points,
        parallel_break_even_workload=400_000,
    )

    assert recommendation is None


def test_recommend_parallel_max_workers_returns_none_without_break_even() -> None:
    point = create_worker_scaling_point(
        palette_color_count=40,
        worker_durations=(
            (
                1,
                2.0,
            ),
            (
                2,
                1.0,
            ),
        ),
    )

    recommendation = benchmark_quantization.recommend_parallel_max_workers(
        (point,),
        parallel_break_even_workload=None,
    )

    assert recommendation is None


def test_run_case_forces_parallel_calibration_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=2,
        height=2,
        unique_rgb_count=4,
    )

    captured: dict[str, int] = {}

    class FakeParallelImageQuantizer:
        def __init__(
            self,
            color_distance: object,
            executor: object,
            worker_count: int,
            break_even_workload: int,
        ) -> None:
            captured["worker_count"] = worker_count
            captured["break_even_workload"] = break_even_workload

        def quantize(
            self,
            image: InputImage,
            palette: Palette,
        ) -> None:
            pass

    def fake_measure_process_startup() -> float:
        return 0.1

    def fake_measure_process_transfer(
        payload: benchmark_quantization.RgbPayload,
    ) -> float:
        return 0.01

    monkeypatch.setattr(
        benchmark_quantization,
        "ParallelImageQuantizer",
        FakeParallelImageQuantizer,
    )
    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_process_startup",
        fake_measure_process_startup,
    )
    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_process_transfer",
        fake_measure_process_transfer,
    )

    result = benchmark_quantization.run_case(
        case,
        runs=1,
        worker_counts=(
            1,
            2,
        ),
        palette_color_count=8,
    )

    assert result.worker_results[1].worker_count == 2
    assert captured == {
        "worker_count": 2,
        "break_even_workload": 1,
    }


def test_run_case_measures_each_requested_worker_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=2,
        height=2,
        unique_rgb_count=4,
    )

    calls: list[int] = []

    durations = iter(
        (
            2.0,
            1.0,
            0.5,
            4.0,
            2.0,
            1.0,
        ),
    )

    def fake_measure_quantization(
        image: InputImage,
        palette: Palette,
        worker_count: int,
    ) -> float:
        calls.append(
            worker_count,
        )

        return next(
            durations,
        )

    def fake_measure_process_startup() -> float:
        return 0.1

    def fake_measure_process_transfer(
        payload: benchmark_quantization.RgbPayload,
    ) -> float:
        return 0.01

    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_quantization",
        fake_measure_quantization,
    )
    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_process_startup",
        fake_measure_process_startup,
    )
    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_process_transfer",
        fake_measure_process_transfer,
    )

    result = benchmark_quantization.run_case(
        case,
        runs=2,
        worker_counts=(
            1,
            2,
            4,
        ),
        palette_color_count=32,
    )

    assert calls == [
        1,
        2,
        4,
        1,
        2,
        4,
    ]

    assert result.quantization_durations_seconds == (
        2.0,
        4.0,
    )

    assert result.worker_results == (
        benchmark_quantization.QuantizationWorkerBenchmarkResult(
            worker_count=1,
            durations_seconds=(
                2.0,
                4.0,
            ),
        ),
        benchmark_quantization.QuantizationWorkerBenchmarkResult(
            worker_count=2,
            durations_seconds=(
                1.0,
                2.0,
            ),
        ),
        benchmark_quantization.QuantizationWorkerBenchmarkResult(
            worker_count=4,
            durations_seconds=(
                0.5,
                1.0,
            ),
        ),
    )


def test_format_result_reports_quantization_and_transfer_metrics() -> None:
    result = benchmark_quantization.QuantizationBenchmarkResult(
        case="test",
        pixel_count=100,
        unique_rgb_count=20,
        serialized_payload_bytes=512,
        quantization_durations_seconds=(
            3.0,
            1.0,
            2.0,
        ),
        process_startup_durations_seconds=(
            0.3,
            0.1,
            0.2,
        ),
        process_transfer_durations_seconds=(
            0.03,
            0.01,
            0.02,
        ),
    )

    formatted = benchmark_quantization.format_result(
        result,
    )

    assert "test" in formatted
    assert "pixels=100" in formatted
    assert "unique_rgb=20" in formatted
    assert "payload=512 bytes" in formatted
    assert "quantization=2.000000s" in formatted
    assert "process_startup=0.200000s" in formatted
    assert "process_transfer=0.020000s" in formatted


def test_format_result_reports_worker_scaling() -> None:
    result = benchmark_quantization.QuantizationBenchmarkResult(
        case="test",
        pixel_count=100,
        unique_rgb_count=20,
        serialized_payload_bytes=512,
        quantization_durations_seconds=(2.0,),
        process_startup_durations_seconds=(0.2,),
        process_transfer_durations_seconds=(0.02,),
        worker_results=(
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=1,
                durations_seconds=(2.0,),
            ),
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=2,
                durations_seconds=(1.0,),
            ),
            benchmark_quantization.QuantizationWorkerBenchmarkResult(
                worker_count=4,
                durations_seconds=(0.5,),
            ),
        ),
    )

    formatted = benchmark_quantization.format_result(
        result,
    )

    assert "workers=1:2.000000s/1.00x" in formatted
    assert "workers=2:1.000000s/2.00x" in formatted
    assert "workers=4:0.500000s/4.00x" in formatted


def test_format_parallel_break_even_recommendation_reports_workload() -> None:
    formatted = benchmark_quantization.format_parallel_break_even_recommendation(
        851_968,
    )

    assert formatted == (
        "recommended_parallel_quantization_break_even_workload="
        "851968 (minimum_speedup=1.25x)"
    )


def test_format_parallel_break_even_recommendation_reports_unavailable() -> None:
    formatted = benchmark_quantization.format_parallel_break_even_recommendation(
        None,
    )

    assert formatted == (
        "recommended_parallel_quantization_break_even_workload="
        "unavailable (minimum_speedup=1.25x)"
    )


def test_format_parallel_max_workers_recommendation_reports_worker_count() -> None:
    formatted = benchmark_quantization.format_parallel_max_workers_recommendation(
        8,
    )

    assert formatted == (
        "recommended_parallel_quantization_max_workers=8 "
        "(minimum_incremental_speedup=1.05x, stable_points=3)"
    )


def test_format_parallel_max_workers_recommendation_reports_unavailable() -> None:
    formatted = benchmark_quantization.format_parallel_max_workers_recommendation(
        None,
    )

    assert formatted == (
        "recommended_parallel_quantization_max_workers=unavailable "
        "(minimum_incremental_speedup=1.05x, stable_points=3)"
    )


def test_parser_accepts_run_count() -> None:
    args = benchmark_quantization.build_parser().parse_args(
        [
            "--runs",
            "5",
        ],
    )

    assert args.runs == 5


def test_parser_accepts_max_worker_count() -> None:
    args = benchmark_quantization.build_parser().parse_args(
        [
            "--max-workers",
            "6",
        ],
    )

    assert args.max_workers == 6


def test_parser_defaults_to_sixteen_max_workers() -> None:
    args = benchmark_quantization.build_parser().parse_args(
        [],
    )

    assert args.max_workers == 16


@pytest.mark.parametrize(
    "arguments",
    (
        ("--real-images",),
        (
            "--cases",
            "simple",
        ),
        (
            "--color-distance",
            "delta_e_76",
        ),
        (
            "--palette-color-counts",
            "60",
        ),
        (
            "--palette",
            "faberCastellPolychromos60",
        ),
        (
            "--palette-version",
            "1",
        ),
    ),
)
def test_parser_rejects_removed_benchmark_options(
    arguments: tuple[str, ...],
) -> None:
    with pytest.raises(
        SystemExit,
    ):
        benchmark_quantization.build_parser().parse_args(
            list(
                arguments,
            ),
        )


def test_main_runs_complete_synthetic_palette_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[
        tuple[
            benchmark_quantization.QuantizationBenchmarkCase,
            int,
            tuple[int, ...],
        ]
    ] = []

    def fake_run_case(
        case: benchmark_quantization.QuantizationBenchmarkCase,
        *,
        runs: int,
        worker_counts: tuple[int, ...],
        palette_color_count: int,
    ) -> benchmark_quantization.QuantizationBenchmarkResult:
        assert runs == 1

        calls.append(
            (
                case,
                palette_color_count,
                worker_counts,
            ),
        )

        return create_calibration_result(
            unique_rgb_count=case.unique_rgb_count,
            sequential_seconds=1.25,
            parallel_seconds=1.0,
        )

    monkeypatch.setattr(
        benchmark_quantization,
        "run_case",
        fake_run_case,
    )
    monkeypatch.setattr(
        os,
        "cpu_count",
        lambda: 16,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_quantization.py",
            "--runs",
            "1",
        ],
    )

    benchmark_quantization.main()

    assert len(calls) == 77

    assert [palette_color_count for _, palette_color_count, _ in calls] == list(
        range(
            8,
            161,
            2,
        ),
    )

    assert all(case == benchmark_quantization.CALIBRATION_CASE for case, _, _ in calls)

    assert all(
        worker_counts
        == (
            1,
            2,
            4,
            8,
            16,
        )
        for _, _, worker_counts in calls
    )


def test_main_reports_calibrated_break_even(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_case(
        case: benchmark_quantization.QuantizationBenchmarkCase,
        *,
        runs: int,
        worker_counts: tuple[int, ...],
        palette_color_count: int,
    ) -> benchmark_quantization.QuantizationBenchmarkResult:
        speedup = 1.20 if palette_color_count < 40 else 1.25

        return create_calibration_result(
            unique_rgb_count=case.unique_rgb_count,
            sequential_seconds=speedup,
            parallel_seconds=1.0,
        )

    monkeypatch.setattr(
        benchmark_quantization,
        "run_case",
        fake_run_case,
    )
    monkeypatch.setattr(
        os,
        "cpu_count",
        lambda: 16,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_quantization.py",
            "--runs",
            "1",
        ],
    )

    benchmark_quantization.main()

    captured = capsys.readouterr()

    assert (
        "recommended_parallel_quantization_break_even_workload="
        "655360 (minimum_speedup=1.25x)" in captured.out
    )


def test_main_reports_recommended_max_workers(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_case(
        case: benchmark_quantization.QuantizationBenchmarkCase,
        *,
        runs: int,
        worker_counts: tuple[int, ...],
        palette_color_count: int,
    ) -> benchmark_quantization.QuantizationBenchmarkResult:
        return create_worker_scaling_result(
            unique_rgb_count=case.unique_rgb_count,
            worker_durations=(
                (
                    1,
                    2.0,
                ),
                (
                    2,
                    1.5,
                ),
                (
                    4,
                    1.0,
                ),
                (
                    8,
                    0.90,
                ),
                (
                    16,
                    0.88,
                ),
            ),
        )

    monkeypatch.setattr(
        benchmark_quantization,
        "run_case",
        fake_run_case,
    )
    monkeypatch.setattr(
        os,
        "cpu_count",
        lambda: 16,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_quantization.py",
            "--runs",
            "1",
        ],
    )

    benchmark_quantization.main()

    captured = capsys.readouterr()

    assert (
        "recommended_parallel_quantization_max_workers=8 "
        "(minimum_incremental_speedup=1.05x, stable_points=3)" in captured.out
    )


def test_run_case_uses_typed_process_transfer_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = benchmark_quantization.QuantizationBenchmarkCase(
        name="test",
        width=1,
        height=1,
        unique_rgb_count=1,
    )

    def fake_measure_quantization(
        image: InputImage,
        palette: Palette,
        worker_count: int,
    ) -> float:
        return 1.0

    def fake_measure_process_startup() -> float:
        return 0.1

    def fake_measure_process_transfer(
        payload: benchmark_quantization.RgbPayload,
    ) -> float:
        assert payload
        return 0.01

    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_quantization",
        fake_measure_quantization,
    )
    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_process_startup",
        fake_measure_process_startup,
    )
    monkeypatch.setattr(
        benchmark_quantization,
        "_measure_process_transfer",
        fake_measure_process_transfer,
    )

    result = benchmark_quantization.run_case(
        case,
        runs=1,
        worker_counts=(1,),
        palette_color_count=8,
    )

    assert result.median_process_transfer_seconds == 0.01
