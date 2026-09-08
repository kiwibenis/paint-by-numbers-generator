# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark memory retained by region merge-candidate tracking.

This developer-only module measures the Python heap retained by the initial
candidate-evaluation cache used by optional region complexity reduction.
"""

from __future__ import annotations

import gc
import tracemalloc
from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median

from pbn.application.region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)
from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    Region,
    RegionMergeCandidate,
)
from pbn.regions.merge_candidate_builder import RegionMergeCandidateBuilder
from pbn.regions.merge_candidate_ranker import (
    RankedCandidateEvaluation,
    RegionMergeCandidateRanker,
)
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    SUPPORTED_COLOR_DISTANCES,
    palette_path,
    prepare_case,
    resolve_color_distance,
)

CandidateEvaluationCache = dict[
    RegionMergeCandidate,
    RankedCandidateEvaluation,
]


@dataclass(frozen=True, slots=True)
class MemorySummary:
    """
    Summary of repeated retained-memory measurements.
    """

    repeat_count: int
    minimum_bytes: int
    median_bytes: float
    mean_bytes: float
    maximum_bytes: int


@dataclass(frozen=True, slots=True)
class CandidateTrackingMemoryBenchmark:
    """
    Memory retained by the candidate-evaluation tracking cache.
    """

    candidate_count: int
    retained_memory: MemorySummary

    @property
    def median_bytes_per_candidate(self) -> float:
        """
        Return median retained bytes per directed candidate.
        """
        if self.candidate_count == 0:
            return 0.0

        return self.retained_memory.median_bytes / self.candidate_count


def summarize_memory(
    measurements: tuple[int, ...],
) -> MemorySummary:
    """
    Summarize repeated retained-memory measurements.
    """
    if not measurements:
        raise ValueError(
            "measurements must not be empty",
        )

    return MemorySummary(
        repeat_count=len(measurements),
        minimum_bytes=min(measurements),
        median_bytes=median(measurements),
        mean_bytes=mean(measurements),
        maximum_bytes=max(measurements),
    )


def build_candidate_evaluation_cache(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
) -> CandidateEvaluationCache:
    """
    Build the same initial candidate tracking structure used by the reducer.
    """
    raw_evaluations = RegionMergeCandidateBuilder(
        color_distance=color_distance,
    ).build(
        regions,
    )

    ranked_evaluations = RegionMergeCandidateRanker(
        cost_calculator=cost_calculator,
    ).rank(
        raw_evaluations,
    )

    return {evaluation[0]: evaluation for evaluation in ranked_evaluations}


def benchmark_candidate_tracking_memory(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    repeats: int,
) -> CandidateTrackingMemoryBenchmark:
    """
    Measure memory retained by the initial candidate-evaluation cache.

    Region preparation happens before this benchmark. Each repetition starts
    tracing immediately before candidate tracking is constructed. The retained
    measurement is taken after the builder and ranking temporaries have left
    their scopes, while the returned candidate-evaluation cache remains alive.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    retained_measurements: list[int] = []
    candidate_count: int | None = None

    for _ in range(repeats):
        gc.collect()

        tracemalloc.start()

        try:
            baseline_bytes, _ = tracemalloc.get_traced_memory()

            candidate_evaluations = build_candidate_evaluation_cache(
                regions=regions,
                color_distance=color_distance,
                cost_calculator=cost_calculator,
            )

            retained_bytes, _ = tracemalloc.get_traced_memory()

            current_candidate_count = len(
                candidate_evaluations,
            )

            retained_measurements.append(
                max(
                    0,
                    retained_bytes - baseline_bytes,
                ),
            )

            if candidate_count is None:
                candidate_count = current_candidate_count
            elif current_candidate_count != candidate_count:
                raise RuntimeError(
                    "Candidate tracking produced "
                    "different candidate counts "
                    "between memory benchmark repeats.",
                )

            del candidate_evaluations
        finally:
            tracemalloc.stop()

    assert candidate_count is not None

    return CandidateTrackingMemoryBenchmark(
        candidate_count=candidate_count,
        retained_memory=summarize_memory(
            tuple(retained_measurements),
        ),
    )


def format_candidate_tracking_memory_benchmark(
    *,
    case: str,
    benchmark: CandidateTrackingMemoryBenchmark,
) -> str:
    """
    Format one candidate-tracking memory benchmark result.
    """
    memory = benchmark.retained_memory

    median_mib = memory.median_bytes / (1024.0 * 1024.0)

    return (
        f"{case}: "
        "candidate_evaluations="
        f"{benchmark.candidate_count}, "
        f"repeats={memory.repeat_count}, "
        "retained_min="
        f"{memory.minimum_bytes}B, "
        "retained_median="
        f"{memory.median_bytes:.0f}B, "
        "retained_mean="
        f"{memory.mean_bytes:.0f}B, "
        "retained_max="
        f"{memory.maximum_bytes}B, "
        "retained_median="
        f"{median_mib:.3f}MiB, "
        "retained_bytes_per_candidate="
        f"{benchmark.median_bytes_per_candidate:.1f}B"
    )


def build_parser() -> ArgumentParser:
    """
    Build the candidate-tracking memory benchmark parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark retained memory for region "
            "merge-candidate and metric tracking."
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
    Measure candidate-tracking memory on representative image cases.
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
            minimum_region_size_mm=(args.minimum_region_size_mm),
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
            palette_version=(selected_palette_version),
        ),
    )

    color_distance = resolve_color_distance(
        selected_color_distance,
    )

    cost_calculator = build_region_merge_cost_calculator(
        config.region_complexity.merge_cost,
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

        benchmark = benchmark_candidate_tracking_memory(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=cost_calculator,
            repeats=args.repeats,
        )

        print(
            format_candidate_tracking_memory_benchmark(
                case=case,
                benchmark=benchmark,
            ),
        )


if __name__ == "__main__":
    main()
