# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark all-neighbor color-contrast calculation performance.

This developer-only module measures the isolated cost of evaluating all
neighbors for the source regions of actual accepted complexity merges.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import replace
from pathlib import Path

from pbn.application.region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    SUPPORTED_COLOR_DISTANCES,
    palette_path,
    prepare_case,
    resolve_color_distance,
    resolve_max_regions,
)
from tools.benchmark_region_complexity_performance import (
    AllNeighborColorContrastCalculationBenchmark,
    benchmark_all_neighbor_color_contrast_calculation_for_regions,
)


def format_all_neighbor_color_contrast_calculation_benchmark(
    *,
    case: str,
    benchmark: AllNeighborColorContrastCalculationBenchmark,
) -> str:
    """
    Format one all-neighbor color-contrast benchmark result.
    """
    timings = benchmark.timings

    if benchmark.neighbor_measurement_count == 0:
        median_per_neighbor_microseconds = 0.0
    else:
        median_per_neighbor_microseconds = (
            timings.median_seconds / benchmark.neighbor_measurement_count * 1_000_000.0
        )

    return (
        f"{case}: "
        "all_neighbor_color_contrast_evaluations="
        f"{benchmark.evaluation_count}, "
        "neighbor_measurements="
        f"{benchmark.neighbor_measurement_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s, "
        "median_per_neighbor="
        f"{median_per_neighbor_microseconds:.3f}us"
    )


def build_parser() -> ArgumentParser:
    """
    Build the all-neighbor color-contrast performance parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark isolated all-neighbor color-contrast "
            "calculation for accepted region-complexity merges."
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
        "--target-fraction",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
    )

    return parser


def main() -> None:
    """
    Benchmark all-neighbor contrast on representative image cases.
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

    if not 0.0 < args.target_fraction <= 1.0:
        parser.error(
            "--target-fraction must be greater than zero and at most one",
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

    cost_calculator = build_region_merge_cost_calculator(
        config.region_complexity.merge_cost,
    )

    maximum_merge_cost = config.region_complexity.maximum_merge_cost

    print(
        (
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            "minimum_region_size_mm="
            f"{config.minimum_region_size_mm:g}, "
            "maximum_merge_cost="
            f"{maximum_merge_cost:g}, "
            "target_fraction="
            f"{args.target_fraction:g}, "
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

        max_regions = resolve_max_regions(
            baseline_region_count=len(
                prepared.regions,
            ),
            target_fraction=args.target_fraction,
        )

        benchmark = benchmark_all_neighbor_color_contrast_calculation_for_regions(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=cost_calculator,
            minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            repeats=args.repeats,
        )

        print(
            format_all_neighbor_color_contrast_calculation_benchmark(
                case=case,
                benchmark=benchmark,
            ),
        )


if __name__ == "__main__":
    main()
