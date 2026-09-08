# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark source-region compactness calculation performance.

This developer-only module measures the isolated cost of calculating
normalized source non-compactness from already prepared merge metrics.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter

from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import Region, RegionMergeMetrics
from pbn.regions.merge_candidate_builder import RegionMergeCandidateBuilder
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    SUPPORTED_COLOR_DISTANCES,
    palette_path,
    prepare_case,
    resolve_color_distance,
)
from tools.benchmark_region_complexity_performance import (
    DurationSummary,
    summarize_durations,
)


@dataclass(frozen=True, slots=True)
class SourceCompactnessCalculationBenchmark:
    """
    Benchmark result for normalized source-compactness calculation.
    """

    evaluation_count: int
    timings: DurationSummary


def benchmark_source_compactness_calculation(
    *,
    metrics: tuple[RegionMergeMetrics, ...],
    repeats: int,
) -> SourceCompactnessCalculationBenchmark:
    """
    Benchmark source non-compactness on already prepared merge metrics.

    Candidate construction, adjacency processing, perimeter calculation and
    raw metric construction remain outside the measured durations.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    durations: list[float] = []

    for _ in range(repeats):
        started_at = perf_counter()

        tuple(metric.source_non_compactness for metric in metrics)

        finished_at = perf_counter()

        durations.append(
            finished_at - started_at,
        )

    return SourceCompactnessCalculationBenchmark(
        evaluation_count=len(metrics),
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def benchmark_source_compactness_calculation_for_regions(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    repeats: int,
) -> SourceCompactnessCalculationBenchmark:
    """
    Benchmark compactness calculation for real directed merge candidates.

    Candidate and raw metric construction are completed before timing so the
    measured duration contains only normalized source-compactness calculation.
    """
    candidate_builder = RegionMergeCandidateBuilder(
        color_distance=color_distance,
    )

    evaluations = candidate_builder.build(
        regions,
    )

    metrics = tuple(candidate_metrics for _, candidate_metrics in evaluations)

    return benchmark_source_compactness_calculation(
        metrics=metrics,
        repeats=repeats,
    )


def format_source_compactness_calculation_benchmark(
    *,
    case: str,
    benchmark: SourceCompactnessCalculationBenchmark,
) -> str:
    """
    Format one source-compactness calculation benchmark result.
    """
    timings = benchmark.timings

    if benchmark.evaluation_count == 0:
        median_per_evaluation_microseconds = 0.0
    else:
        median_per_evaluation_microseconds = (
            timings.median_seconds / benchmark.evaluation_count * 1_000_000.0
        )

    return (
        f"{case}: "
        "source_compactness_evaluations="
        f"{benchmark.evaluation_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s, "
        "median_per_evaluation="
        f"{median_per_evaluation_microseconds:.3f}us"
    )


def build_parser() -> ArgumentParser:
    """
    Build the source-compactness performance benchmark parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark isolated source-region compactness "
            "calculation for region-complexity candidates."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
    )

    parser.add_argument(
        "--cases",
        nargs="+",
        choices=EVALUATION_CASES,
        default=EVALUATION_CASES,
    )

    parser.add_argument(
        "--palette",
        default=None,
    )

    parser.add_argument(
        "--palette-version",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--color-distance",
        choices=SUPPORTED_COLOR_DISTANCES,
        default=None,
    )

    parser.add_argument(
        "--minimum-region-size-mm",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
    )

    return parser


def main() -> None:
    """
    Benchmark source compactness on representative image cases.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.repeats <= 0:
        parser.error(
            "--repeats must be greater than zero",
        )

    if args.minimum_region_size_mm is not None and args.minimum_region_size_mm <= 0.0:
        parser.error(
            "--minimum-region-size-mm must be greater than zero",
        )

    config = load_config(
        args.config,
    )

    if args.minimum_region_size_mm is not None:
        config = replace(
            config,
            minimum_region_size_mm=args.minimum_region_size_mm,
        )

    selected_palette = args.palette if args.palette is not None else config.palette

    selected_palette_version = (
        args.palette_version
        if args.palette_version is not None
        else config.palette_version
    )

    selected_color_distance = (
        args.color_distance
        if args.color_distance is not None
        else config.color_distance
    )

    palette = load_palette(
        palette_path(
            palette_id=selected_palette,
            palette_version=selected_palette_version,
        ),
    )

    color_distance = resolve_color_distance(
        selected_color_distance,
    )

    print(
        (
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            "minimum_region_size_mm="
            f"{config.minimum_region_size_mm:g}, "
            f"repeats={args.repeats}"
        ),
    )

    for case in args.cases:
        prepared = prepare_case(
            case=case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

        benchmark = benchmark_source_compactness_calculation_for_regions(
            regions=prepared.regions,
            color_distance=color_distance,
            repeats=args.repeats,
        )

        print(
            format_source_compactness_calculation_benchmark(
                case=case,
                benchmark=benchmark,
            ),
        )


if __name__ == "__main__":
    main()
