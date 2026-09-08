# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
System calibration benchmark for parallel quantization.
"""

from __future__ import annotations

import os
import pickle
from argparse import ArgumentParser
from dataclasses import dataclass
from multiprocessing import get_context
from multiprocessing.connection import Connection
from statistics import median
from time import perf_counter

from pbn.application.parallel_image_quantizer import ParallelImageQuantizer
from pbn.color import DeltaE2000, ImageQuantizer
from pbn.color.rgb_to_lab import RgbToLabConverter
from pbn.infrastructure.process_quantization_executor import (
    ProcessQuantizationExecutor,
)
from pbn.models import RGB, InputImage, Palette, PaletteColor

CALIBRATION_COLOR_DISTANCE = "delta_e_2000"
CALIBRATION_UNIQUE_RGB_COUNT = 16_384
CALIBRATION_PALETTE_COLOR_COUNTS = tuple(
    range(
        8,
        161,
        2,
    ),
)

DEFAULT_MAX_WORKER_COUNT = 16
MIN_RECOMMENDED_PARALLEL_SPEEDUP = 1.25
MIN_RECOMMENDED_WORKER_SPEEDUP = 1.05
MIN_RECOMMENDED_WORKER_STABLE_POINTS = 3

_READY = "ready"
_STOP = "stop"

RgbPayload = tuple[tuple[int, int, int], ...]


@dataclass(frozen=True, slots=True)
class QuantizationBenchmarkCase:
    """
    Deterministic synthetic workload for isolated quantization measurement.
    """

    name: str
    width: int
    height: int
    unique_rgb_count: int


CALIBRATION_CASE = QuantizationBenchmarkCase(
    name="calibration",
    width=1024,
    height=1024,
    unique_rgb_count=CALIBRATION_UNIQUE_RGB_COUNT,
)


@dataclass(frozen=True, slots=True)
class QuantizationWorkerBenchmarkResult:
    """
    Quantization measurements for one worker count.
    """

    worker_count: int
    durations_seconds: tuple[float, ...]

    @property
    def median_seconds(self) -> float:
        """
        Return the median quantization duration.
        """
        return median(
            self.durations_seconds,
        )


@dataclass(frozen=True, slots=True)
class QuantizationBenchmarkResult:
    """
    Measurements for one isolated quantization benchmark case.
    """

    case: str
    pixel_count: int
    unique_rgb_count: int
    serialized_payload_bytes: int
    quantization_durations_seconds: tuple[float, ...]
    process_startup_durations_seconds: tuple[float, ...]
    process_transfer_durations_seconds: tuple[float, ...]
    worker_results: tuple[
        QuantizationWorkerBenchmarkResult,
        ...,
    ] = ()

    @property
    def median_quantization_seconds(self) -> float:
        """
        Return the median sequential quantization duration.
        """
        return median(
            self.quantization_durations_seconds,
        )

    @property
    def median_process_startup_seconds(self) -> float:
        """
        Return the median spawned-process startup duration.
        """
        return median(
            self.process_startup_durations_seconds,
        )

    @property
    def median_process_transfer_seconds(self) -> float:
        """
        Return the median payload round-trip duration.
        """
        return median(
            self.process_transfer_durations_seconds,
        )


@dataclass(frozen=True, slots=True)
class QuantizationCalibrationPoint:
    """
    One measured point in the parallel quantization calibration sweep.
    """

    palette_color_count: int
    result: QuantizationBenchmarkResult

    @property
    def estimated_workload(self) -> int:
        """
        Return the estimated number of palette comparisons.
        """
        return self.result.unique_rgb_count * self.palette_color_count

    @property
    def best_parallel_speedup(self) -> float:
        """
        Return the best measured speedup from parallel worker counts.
        """
        parallel_results = tuple(
            worker_result
            for worker_result in self.result.worker_results
            if worker_result.worker_count > 1
        )

        if not parallel_results:
            return 0.0

        sequential_seconds = self.result.median_quantization_seconds

        return max(
            _calculate_speedup(
                sequential_seconds,
                worker_result.median_seconds,
            )
            for worker_result in parallel_results
        )


def _rgb_from_index(
    index: int,
) -> RGB:
    value = (index * 2_654_435_761) & 0xFFFFFF

    return RGB(
        red=value & 0xFF,
        green=(value >> 8) & 0xFF,
        blue=(value >> 16) & 0xFF,
    )


def build_input_image(
    case: QuantizationBenchmarkCase,
) -> InputImage:
    """
    Build a deterministic image with the requested RGB diversity.
    """
    if case.width <= 0 or case.height <= 0:
        raise ValueError(
            "benchmark dimensions must be greater than zero",
        )

    pixel_count = case.width * case.height

    if case.unique_rgb_count <= 0:
        raise ValueError(
            "unique_rgb_count must be greater than zero",
        )

    if case.unique_rgb_count > pixel_count:
        raise ValueError(
            "unique_rgb_count must not exceed pixel count",
        )

    if case.unique_rgb_count > 256**3:
        raise ValueError(
            "unique_rgb_count exceeds the RGB color space",
        )

    unique_colors = tuple(
        _rgb_from_index(index)
        for index in range(
            case.unique_rgb_count,
        )
    )

    rows: list[tuple[RGB, ...]] = []

    for y in range(case.height):
        row_start = y * case.width

        row = tuple(
            unique_colors[(row_start + x) % case.unique_rgb_count]
            for x in range(
                case.width,
            )
        )

        rows.append(
            row,
        )

    return InputImage.from_rows(
        tuple(rows),
    )


def build_unique_rgb_payload(
    image: InputImage,
) -> RgbPayload:
    """
    Build a compact payload preserving first-seen RGB order.
    """
    unique_colors = dict.fromkeys(rgb for row in image.rows() for rgb in row)

    return tuple(rgb.as_tuple() for rgb in unique_colors)


def build_worker_counts(
    *,
    available_cpu_count: int | None,
    work_unit_count: int,
    max_worker_count: int,
) -> tuple[int, ...]:
    """
    Build a bounded worker-count scaling sequence.
    """
    if work_unit_count <= 0:
        raise ValueError(
            "work_unit_count must be greater than zero",
        )

    if max_worker_count <= 0:
        raise ValueError(
            "max_worker_count must be greater than zero",
        )

    cpu_count = available_cpu_count if available_cpu_count is not None else 1

    if cpu_count <= 0:
        cpu_count = 1

    effective_maximum = min(
        cpu_count,
        work_unit_count,
        max_worker_count,
    )

    if effective_maximum <= 1:
        return (1,)

    worker_counts: list[int] = [
        1,
    ]

    worker_count = 2

    while worker_count <= effective_maximum:
        worker_counts.append(
            worker_count,
        )
        worker_count *= 2

    if worker_counts[-1] != effective_maximum:
        worker_counts.append(
            effective_maximum,
        )

    return tuple(
        worker_counts,
    )


def serialized_size_bytes(
    payload: RgbPayload,
) -> int:
    """
    Return the serialized size of a representative worker payload.
    """
    return len(
        pickle.dumps(
            payload,
            protocol=pickle.HIGHEST_PROTOCOL,
        ),
    )


def roundtrip_payload(
    payload: RgbPayload,
) -> RgbPayload:
    """
    Return a payload unchanged for process round-trip measurement.
    """
    return payload


def build_calibration_palette(
    *,
    color_count: int,
) -> Palette:
    """
    Build a deterministic synthetic calibration palette prefix.
    """
    if color_count <= 0:
        raise ValueError(
            "palette color count must be greater than zero",
        )

    converter = RgbToLabConverter()

    colors: list[PaletteColor] = []

    for index in range(
        color_count,
    ):
        rgb = _rgb_from_index(
            index + 100_000,
        )

        colors.append(
            PaletteColor(
                number=index + 1,
                name=("Benchmark color " f"{index + 1}"),
                rgb=rgb,
                lab=converter.convert(
                    rgb,
                ),
            ),
        )

    return Palette(
        id=f"benchmark{color_count}",
        manufacturer="Benchmark",
        display_name=f"Benchmark {color_count}",
        version=1,
        colors=tuple(colors),
    )


def _startup_worker(
    connection: Connection,
) -> None:
    connection.send(
        _READY,
    )
    connection.close()


def _transfer_worker(
    connection: Connection,
) -> None:
    connection.send(
        _READY,
    )

    while True:
        message = connection.recv()

        if message == _STOP:
            break

        connection.send(
            roundtrip_payload(
                message,
            ),
        )

    connection.close()


def _measure_process_startup() -> float:
    context = get_context(
        "spawn",
    )

    (
        parent_connection,
        child_connection,
    ) = context.Pipe()

    process = context.Process(
        target=_startup_worker,
        args=(child_connection,),
    )

    started_at = perf_counter()

    process.start()
    child_connection.close()

    ready = parent_connection.recv()

    finished_at = perf_counter()

    parent_connection.close()
    process.join()

    if ready != _READY:
        raise RuntimeError(
            "process worker did not become ready",
        )

    if process.exitcode != 0:
        raise RuntimeError(
            "process worker exited unsuccessfully",
        )

    return finished_at - started_at


def _measure_process_transfer(
    payload: RgbPayload,
) -> float:
    context = get_context(
        "spawn",
    )

    (
        parent_connection,
        child_connection,
    ) = context.Pipe()

    process = context.Process(
        target=_transfer_worker,
        args=(child_connection,),
    )

    process.start()
    child_connection.close()

    ready = parent_connection.recv()

    if ready != _READY:
        parent_connection.close()
        process.join()

        raise RuntimeError(
            "process worker did not become ready",
        )

    started_at = perf_counter()

    parent_connection.send(
        payload,
    )

    result = parent_connection.recv()

    finished_at = perf_counter()

    parent_connection.send(
        _STOP,
    )

    parent_connection.close()
    process.join()

    if process.exitcode != 0:
        raise RuntimeError(
            "process worker exited unsuccessfully",
        )

    if result != payload:
        raise RuntimeError(
            "process worker returned an unexpected payload",
        )

    return finished_at - started_at


def _measure_quantization(
    image: InputImage,
    palette: Palette,
    worker_count: int,
) -> float:
    """
    Measure Delta E 2000 quantization at the requested execution width.
    """
    distance = DeltaE2000()

    if worker_count == 1:
        quantizer: ImageQuantizer | ParallelImageQuantizer = ImageQuantizer(
            color_distance=distance,
        )
    else:
        quantizer = ParallelImageQuantizer(
            color_distance=distance,
            executor=ProcessQuantizationExecutor(),
            worker_count=worker_count,
            break_even_workload=1,
        )

    started_at = perf_counter()

    quantizer.quantize(
        image,
        palette,
    )

    finished_at = perf_counter()

    return finished_at - started_at


def _run_image_case(
    *,
    case: str,
    image: InputImage,
    palette: Palette,
    runs: int,
    worker_counts: tuple[int, ...],
) -> QuantizationBenchmarkResult:
    """
    Measure Delta E 2000 quantization scaling for one prepared workload.
    """
    if runs <= 0:
        raise ValueError(
            "runs must be greater than zero",
        )

    if not worker_counts:
        raise ValueError(
            "worker_counts must not be empty",
        )

    if worker_counts[0] != 1:
        raise ValueError(
            "worker_counts must start with one",
        )

    if any(worker_count <= 0 for worker_count in worker_counts):
        raise ValueError(
            "worker counts must be greater than zero",
        )

    payload = build_unique_rgb_payload(
        image,
    )

    worker_durations: dict[
        int,
        list[float],
    ] = {worker_count: [] for worker_count in worker_counts}

    process_startup_durations: list[float] = []

    process_transfer_durations: list[float] = []

    for _ in range(runs):
        for worker_count in worker_counts:
            worker_durations[worker_count].append(
                _measure_quantization(
                    image,
                    palette,
                    worker_count,
                ),
            )

        process_startup_durations.append(
            _measure_process_startup(),
        )

        process_transfer_durations.append(
            _measure_process_transfer(
                payload,
            ),
        )

    worker_results = tuple(
        QuantizationWorkerBenchmarkResult(
            worker_count=worker_count,
            durations_seconds=tuple(
                worker_durations[worker_count],
            ),
        )
        for worker_count in worker_counts
    )

    sequential_durations = tuple(
        worker_durations[1],
    )

    return QuantizationBenchmarkResult(
        case=case,
        pixel_count=(image.width * image.height),
        unique_rgb_count=len(
            payload,
        ),
        serialized_payload_bytes=(
            serialized_size_bytes(
                payload,
            )
        ),
        quantization_durations_seconds=(sequential_durations),
        process_startup_durations_seconds=tuple(
            process_startup_durations,
        ),
        process_transfer_durations_seconds=tuple(
            process_transfer_durations,
        ),
        worker_results=worker_results,
    )


def run_case(
    case: QuantizationBenchmarkCase,
    *,
    runs: int,
    worker_counts: tuple[int, ...] = (1,),
    palette_color_count: int,
) -> QuantizationBenchmarkResult:
    """
    Measure one deterministic synthetic calibration workload.
    """
    image = build_input_image(
        case,
    )

    palette = build_calibration_palette(
        color_count=palette_color_count,
    )

    return _run_image_case(
        case=case.name,
        image=image,
        palette=palette,
        runs=runs,
        worker_counts=worker_counts,
    )


def format_result(
    result: QuantizationBenchmarkResult,
) -> str:
    """
    Format one isolated quantization benchmark result.
    """
    formatted = (
        f"{result.case}: "
        f"pixels={result.pixel_count}, "
        f"unique_rgb={result.unique_rgb_count}, "
        f"payload={result.serialized_payload_bytes} bytes, "
        "quantization="
        f"{result.median_quantization_seconds:.6f}s, "
        "process_startup="
        f"{result.median_process_startup_seconds:.6f}s, "
        "process_transfer="
        f"{result.median_process_transfer_seconds:.6f}s"
    )

    if not result.worker_results:
        return formatted

    sequential_seconds = result.median_quantization_seconds

    scaling = ", ".join(
        (
            f"workers={worker_result.worker_count}:"
            f"{worker_result.median_seconds:.6f}s/"
            f"{_calculate_speedup(
                sequential_seconds,
                worker_result.median_seconds,
            ):.2f}x"
        )
        for worker_result in result.worker_results
    )

    return f"{formatted}, " f"scaling=[{scaling}]"


def _calculate_speedup(
    sequential_seconds: float,
    worker_seconds: float,
) -> float:
    if worker_seconds == 0.0:
        return float("inf")

    return sequential_seconds / worker_seconds


def recommend_parallel_break_even(
    points: tuple[
        QuantizationCalibrationPoint,
        ...,
    ],
    *,
    minimum_speedup: float = MIN_RECOMMENDED_PARALLEL_SPEEDUP,
) -> int | None:
    """
    Recommend the lowest workload with stable meaningful parallel gain.
    """
    if not points:
        return None

    workloads = sorted(
        {point.estimated_workload for point in points},
    )

    for workload in workloads:
        larger_or_equal_points = (
            point for point in points if point.estimated_workload >= workload
        )

        if all(
            point.best_parallel_speedup >= minimum_speedup
            for point in larger_or_equal_points
        ):
            return workload

    return None


def _has_stable_worker_gain(
    points: tuple[
        QuantizationCalibrationPoint,
        ...,
    ],
    *,
    worker_count: int,
    minimum_speedup: float,
    stable_points: int,
) -> bool:
    """
    Return whether a worker count provides a stable incremental gain.
    """
    consecutive_points = 0

    for point in points:
        durations_by_worker = {
            worker_result.worker_count: worker_result.median_seconds
            for worker_result in point.result.worker_results
        }

        worker_seconds = durations_by_worker.get(
            worker_count,
        )

        if worker_seconds is None:
            consecutive_points = 0
            continue

        smaller_worker_durations = tuple(
            duration
            for measured_worker_count, duration in durations_by_worker.items()
            if measured_worker_count < worker_count
        )

        if not smaller_worker_durations:
            consecutive_points = 0
            continue

        best_smaller_worker_seconds = min(
            smaller_worker_durations,
        )

        incremental_speedup = _calculate_speedup(
            best_smaller_worker_seconds,
            worker_seconds,
        )

        if incremental_speedup >= minimum_speedup:
            consecutive_points += 1
        else:
            consecutive_points = 0

        if consecutive_points >= stable_points:
            return True

    return False


def recommend_parallel_max_workers(
    points: tuple[
        QuantizationCalibrationPoint,
        ...,
    ],
    *,
    parallel_break_even_workload: int | None,
    minimum_speedup: float = MIN_RECOMMENDED_WORKER_SPEEDUP,
    stable_points: int = MIN_RECOMMENDED_WORKER_STABLE_POINTS,
) -> int | None:
    """
    Recommend the highest worker count with stable incremental scaling.
    """
    if parallel_break_even_workload is None:
        return None

    eligible_points = tuple(
        sorted(
            (
                point
                for point in points
                if (point.estimated_workload >= parallel_break_even_workload)
            ),
            key=lambda point: point.estimated_workload,
        )
    )

    if not eligible_points:
        return None

    worker_counts = tuple(
        sorted(
            {
                worker_result.worker_count
                for point in eligible_points
                for worker_result in point.result.worker_results
                if worker_result.worker_count > 1
            }
        )
    )

    recommendation: int | None = None

    for worker_count in worker_counts:
        if _has_stable_worker_gain(
            eligible_points,
            worker_count=worker_count,
            minimum_speedup=minimum_speedup,
            stable_points=stable_points,
        ):
            recommendation = worker_count

    return recommendation


def format_parallel_break_even_recommendation(
    workload: int | None,
) -> str:
    """
    Format the calibrated parallel quantization break-even recommendation.
    """
    formatted_workload = str(workload) if workload is not None else "unavailable"

    return (
        "recommended_parallel_quantization_break_even_workload="
        f"{formatted_workload} "
        "(minimum_speedup="
        f"{MIN_RECOMMENDED_PARALLEL_SPEEDUP:.2f}x)"
    )


def format_parallel_max_workers_recommendation(
    worker_count: int | None,
) -> str:
    """
    Format the calibrated maximum worker-count recommendation.
    """
    formatted_worker_count = (
        str(worker_count) if worker_count is not None else "unavailable"
    )

    return (
        "recommended_parallel_quantization_max_workers="
        f"{formatted_worker_count} "
        "(minimum_incremental_speedup="
        f"{MIN_RECOMMENDED_WORKER_SPEEDUP:.2f}x, "
        "stable_points="
        f"{MIN_RECOMMENDED_WORKER_STABLE_POINTS})"
    )


def build_parser() -> ArgumentParser:
    """
    Build the parallel quantization calibration command-line parser.
    """
    parser = ArgumentParser(
        description=(
            "Calibrate Delta E 2000 parallel quantization " "for the current system."
        ),
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help=("Number of measured runs " "per calibration point."),
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKER_COUNT,
        help=("Maximum worker count included " "in the calibration sweep."),
    )

    return parser


def main() -> None:
    """
    Run the complete synthetic parallel quantization calibration sweep.
    """
    args = build_parser().parse_args()

    worker_counts = build_worker_counts(
        available_cpu_count=os.cpu_count(),
        work_unit_count=CALIBRATION_CASE.unique_rgb_count,
        max_worker_count=args.max_workers,
    )

    calibration_points: list[QuantizationCalibrationPoint] = []

    for palette_color_count in CALIBRATION_PALETTE_COLOR_COUNTS:
        print(
            f"palette_colors={palette_color_count}",
        )

        result = run_case(
            CALIBRATION_CASE,
            runs=args.runs,
            worker_counts=worker_counts,
            palette_color_count=palette_color_count,
        )

        print(
            format_result(
                result,
            ),
        )

        calibration_points.append(
            QuantizationCalibrationPoint(
                palette_color_count=palette_color_count,
                result=result,
            ),
        )

    points = tuple(
        calibration_points,
    )

    break_even_recommendation = recommend_parallel_break_even(
        points,
    )

    max_workers_recommendation = recommend_parallel_max_workers(
        points,
        parallel_break_even_workload=break_even_recommendation,
    )

    print(
        format_parallel_break_even_recommendation(
            break_even_recommendation,
        ),
    )

    print(
        format_parallel_max_workers_recommendation(
            max_workers_recommendation,
        ),
    )


if __name__ == "__main__":
    main()
