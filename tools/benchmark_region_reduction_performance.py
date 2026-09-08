# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark complete optional region-complexity reduction performance.

This developer-only module measures the complete optional reducer stage on
already prepared mandatory-merge baselines.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter

from pbn.application.region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)
from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import Region
from pbn.regions.complexity_reducer import RegionComplexityReducer
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
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
    DurationSummary,
    summarize_durations,
)


@dataclass(frozen=True, slots=True)
class OptionalComplexityReductionBenchmark:
    """
    Benchmark result for complete optional complexity reduction.
    """

    baseline_region_count: int
    max_regions: int
    final_region_count: int
    accepted_merge_count: int
    timings: DurationSummary


def benchmark_optional_complexity_reduction(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    minimum_circle_diameter_px: int,
    max_regions: int,
    maximum_merge_cost: float,
    repeats: int,
) -> OptionalComplexityReductionBenchmark:
    """
    Benchmark complete optional complexity reduction.

    The supplied regions are already the mandatory-merge baseline. A fresh
    reducer is created for every repetition so reducer-local metric caches do
    not carry across benchmark repetitions.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    if max_regions <= 0:
        raise ValueError(
            "max_regions must be greater than zero",
        )

    durations: list[float] = []
    final_region_count: int | None = None

    for _ in range(repeats):
        reducer = RegionComplexityReducer(
            color_distance=color_distance,
            cost_calculator=cost_calculator,
        )

        started_at = perf_counter()

        reduced_regions = reducer.reduce(
            regions,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
        )

        finished_at = perf_counter()

        durations.append(
            finished_at - started_at,
        )

        current_final_region_count = len(
            reduced_regions,
        )

        if final_region_count is None:
            final_region_count = current_final_region_count
        elif current_final_region_count != final_region_count:
            raise RuntimeError(
                "Optional complexity reduction produced "
                "different region counts between benchmark repeats.",
            )

    assert final_region_count is not None

    return OptionalComplexityReductionBenchmark(
        baseline_region_count=len(
            regions,
        ),
        max_regions=max_regions,
        final_region_count=final_region_count,
        accepted_merge_count=(len(regions) - final_region_count),
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def format_optional_complexity_reduction_benchmark(
    *,
    case: str,
    benchmark: OptionalComplexityReductionBenchmark,
) -> str:
    """
    Format one complete optional-reduction benchmark result.
    """
    timings = benchmark.timings

    if benchmark.accepted_merge_count == 0:
        median_per_merge_milliseconds = 0.0
    else:
        median_per_merge_milliseconds = (
            timings.median_seconds / benchmark.accepted_merge_count * 1_000.0
        )

    return (
        f"{case}: "
        "baseline_regions="
        f"{benchmark.baseline_region_count}, "
        f"max_regions={benchmark.max_regions}, "
        "final_regions="
        f"{benchmark.final_region_count}, "
        "accepted_merges="
        f"{benchmark.accepted_merge_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s, "
        "median_per_merge="
        f"{median_per_merge_milliseconds:.3f}ms"
    )


def build_parser() -> ArgumentParser:
    """
    Build the optional-complexity reduction performance parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark complete optional region-complexity "
            "reduction on mandatory-merge baselines."
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
    Benchmark optional reduction on representative image cases.
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

        benchmark = benchmark_optional_complexity_reduction(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=cost_calculator,
            minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            repeats=args.repeats,
        )

        print(
            format_optional_complexity_reduction_benchmark(
                case=case,
                benchmark=benchmark,
            ),
        )


if __name__ == "__main__":
    main()
