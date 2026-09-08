# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark downstream performance after optional region complexity reduction.

This developer-only module compares the mandatory-merge baseline with the
optionally reduced region set on the downstream stages that consume regions.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter

from pbn.application.region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.label import LabelPlacer
from pbn.models import Outline, Region
from pbn.outline.topology_simplifier import OutlineTopologySimplifier
from tools.benchmark_region_complexity import (
    REPOSITORY_ROOT,
    SUPPORTED_COLOR_DISTANCES,
    execute_reduction,
    palette_path,
    prepare_case,
    resolve_color_distance,
)
from tools.benchmark_region_complexity_performance import (
    DurationSummary,
    summarize_durations,
)

BENCHMARK_CASE = "complex"


@dataclass(frozen=True, slots=True)
class RegionSetStats:
    """
    Structural statistics for one region set.
    """

    region_count: int
    total_pixel_count: int
    maximum_region_pixel_count: int
    total_bounding_box_area: int
    maximum_bounding_box_area: int


@dataclass(frozen=True, slots=True)
class OutlineSetStats:
    """
    Structural statistics for one simplified outline set.
    """

    outline_count: int
    hole_count: int
    outer_vertex_count: int
    hole_vertex_count: int
    total_vertex_count: int
    maximum_region_vertex_count: int


@dataclass(frozen=True, slots=True)
class PairedStageBenchmark:
    """
    Timings for one downstream stage before and after optional reduction.
    """

    mandatory_timings: DurationSummary
    reduced_timings: DurationSummary

    @property
    def repeat_count(self) -> int:
        """
        Return the number of paired benchmark repetitions.
        """
        return self.mandatory_timings.repeat_count

    @property
    def median_delta_seconds(self) -> float:
        """
        Return reduced minus mandatory median duration.
        """
        return (
            self.reduced_timings.median_seconds - self.mandatory_timings.median_seconds
        )

    @property
    def median_delta_fraction(self) -> float:
        """
        Return relative reduced-stage duration change.
        """
        mandatory_seconds = self.mandatory_timings.median_seconds

        if mandatory_seconds == 0.0:
            if self.reduced_timings.median_seconds == 0.0:
                return 0.0

            return float("inf")

        return self.median_delta_seconds / mandatory_seconds

    @property
    def reduced_to_mandatory_ratio(self) -> float:
        """
        Return reduced median divided by mandatory median.
        """
        mandatory_seconds = self.mandatory_timings.median_seconds

        if mandatory_seconds == 0.0:
            if self.reduced_timings.median_seconds == 0.0:
                return 1.0

            return float("inf")

        return self.reduced_timings.median_seconds / mandatory_seconds


@dataclass(frozen=True, slots=True)
class OutlineStageBenchmark:
    """
    Paired outline timing together with resulting outline statistics.
    """

    timings: PairedStageBenchmark
    mandatory_stats: OutlineSetStats
    reduced_stats: OutlineSetStats


def summarize_region_set(
    regions: tuple[Region, ...],
) -> RegionSetStats:
    """
    Summarize region size and bounding-box characteristics.
    """
    if not regions:
        raise ValueError(
            "regions must not be empty",
        )

    total_pixel_count = 0
    maximum_region_pixel_count = 0
    total_bounding_box_area = 0
    maximum_bounding_box_area = 0

    for region in regions:
        if not region.pixels:
            raise ValueError(
                "region pixels must not be empty",
            )

        pixel_count = len(
            region.pixels,
        )

        total_pixel_count += pixel_count
        maximum_region_pixel_count = max(
            maximum_region_pixel_count,
            pixel_count,
        )

        pixel_iterator = region.coordinates()

        first_x, first_y = next(
            pixel_iterator,
        )

        min_x = first_x
        max_x = first_x
        min_y = first_y
        max_y = first_y

        for x, y in pixel_iterator:
            min_x = min(
                min_x,
                x,
            )
            max_x = max(
                max_x,
                x,
            )
            min_y = min(
                min_y,
                y,
            )
            max_y = max(
                max_y,
                y,
            )

        bounding_box_area = (max_x - min_x + 1) * (max_y - min_y + 1)

        total_bounding_box_area += bounding_box_area

        maximum_bounding_box_area = max(
            maximum_bounding_box_area,
            bounding_box_area,
        )

    return RegionSetStats(
        region_count=len(
            regions,
        ),
        total_pixel_count=total_pixel_count,
        maximum_region_pixel_count=(maximum_region_pixel_count),
        total_bounding_box_area=(total_bounding_box_area),
        maximum_bounding_box_area=(maximum_bounding_box_area),
    )


def summarize_outline_set(
    outlines: tuple[Outline, ...],
) -> OutlineSetStats:
    """
    Summarize simplified outline vertex and hole counts.
    """
    hole_count = 0
    outer_vertex_count = 0
    hole_vertex_count = 0
    maximum_region_vertex_count = 0

    for outline in outlines:
        current_outer_vertex_count = len(
            outline.points,
        )

        current_hole_vertex_count = sum(
            len(
                hole_ring,
            )
            for hole_ring in outline.hole_rings
        )

        current_region_vertex_count = (
            current_outer_vertex_count + current_hole_vertex_count
        )

        hole_count += len(
            outline.hole_rings,
        )
        outer_vertex_count += current_outer_vertex_count
        hole_vertex_count += current_hole_vertex_count
        maximum_region_vertex_count = max(
            maximum_region_vertex_count,
            current_region_vertex_count,
        )

    return OutlineSetStats(
        outline_count=len(
            outlines,
        ),
        hole_count=hole_count,
        outer_vertex_count=outer_vertex_count,
        hole_vertex_count=hole_vertex_count,
        total_vertex_count=(outer_vertex_count + hole_vertex_count),
        maximum_region_vertex_count=(maximum_region_vertex_count),
    )


def benchmark_label_placement(
    *,
    mandatory_regions: tuple[Region, ...],
    reduced_regions: tuple[Region, ...],
    repeats: int,
) -> PairedStageBenchmark:
    """
    Benchmark label placement on mandatory and reduced region sets.
    """
    _validate_repeats(
        repeats,
    )

    mandatory_durations: list[float] = []
    reduced_durations: list[float] = []

    for repeat_index in range(repeats):
        execution_order = (
            (
                (
                    False,
                    mandatory_regions,
                ),
                (
                    True,
                    reduced_regions,
                ),
            )
            if repeat_index % 2 == 0
            else (
                (
                    True,
                    reduced_regions,
                ),
                (
                    False,
                    mandatory_regions,
                ),
            )
        )

        for reduced, regions in execution_order:
            placer = LabelPlacer()

            started_at = perf_counter()

            labels = placer.place(
                regions,
            )

            finished_at = perf_counter()

            if len(labels) != len(regions):
                raise RuntimeError(
                    "Label placement produced an unexpected " "number of labels.",
                )

            duration = finished_at - started_at

            if reduced:
                reduced_durations.append(
                    duration,
                )
            else:
                mandatory_durations.append(
                    duration,
                )

    return PairedStageBenchmark(
        mandatory_timings=summarize_durations(
            tuple(
                mandatory_durations,
            ),
        ),
        reduced_timings=summarize_durations(
            tuple(
                reduced_durations,
            ),
        ),
    )


def benchmark_outline_simplification(
    *,
    mandatory_regions: tuple[Region, ...],
    reduced_regions: tuple[Region, ...],
    tolerance: float,
    repeats: int,
) -> OutlineStageBenchmark:
    """
    Benchmark complete topology simplification for both region sets.
    """
    _validate_repeats(
        repeats,
    )

    mandatory_durations: list[float] = []
    reduced_durations: list[float] = []

    mandatory_stats: OutlineSetStats | None = None
    reduced_stats: OutlineSetStats | None = None

    for repeat_index in range(repeats):
        execution_order = (
            (
                (
                    False,
                    mandatory_regions,
                ),
                (
                    True,
                    reduced_regions,
                ),
            )
            if repeat_index % 2 == 0
            else (
                (
                    True,
                    reduced_regions,
                ),
                (
                    False,
                    mandatory_regions,
                ),
            )
        )

        for reduced, regions in execution_order:
            simplifier = OutlineTopologySimplifier()

            started_at = perf_counter()

            outlines = simplifier.simplify(
                regions,
                tolerance=tolerance,
            )

            finished_at = perf_counter()

            current_stats = summarize_outline_set(
                outlines,
            )

            duration = finished_at - started_at

            if reduced:
                reduced_durations.append(
                    duration,
                )

                if reduced_stats is None:
                    reduced_stats = current_stats
                elif current_stats != reduced_stats:
                    raise RuntimeError(
                        "Reduced outline structure changed "
                        "between benchmark repetitions.",
                    )
            else:
                mandatory_durations.append(
                    duration,
                )

                if mandatory_stats is None:
                    mandatory_stats = current_stats
                elif current_stats != mandatory_stats:
                    raise RuntimeError(
                        "Mandatory outline structure changed "
                        "between benchmark repetitions.",
                    )

    assert mandatory_stats is not None
    assert reduced_stats is not None

    return OutlineStageBenchmark(
        timings=PairedStageBenchmark(
            mandatory_timings=summarize_durations(
                tuple(
                    mandatory_durations,
                ),
            ),
            reduced_timings=summarize_durations(
                tuple(
                    reduced_durations,
                ),
            ),
        ),
        mandatory_stats=mandatory_stats,
        reduced_stats=reduced_stats,
    )


def format_region_set_stats(
    *,
    name: str,
    stats: RegionSetStats,
) -> str:
    """
    Format one region-set structural summary.
    """
    return (
        f"{name}: "
        f"regions={stats.region_count}, "
        "total_pixels="
        f"{stats.total_pixel_count}, "
        "max_region_pixels="
        f"{stats.maximum_region_pixel_count}, "
        "total_bbox_area="
        f"{stats.total_bounding_box_area}, "
        "max_bbox_area="
        f"{stats.maximum_bounding_box_area}"
    )


def format_outline_set_stats(
    *,
    name: str,
    stats: OutlineSetStats,
) -> str:
    """
    Format one simplified-outline structural summary.
    """
    return (
        f"{name}: "
        f"outlines={stats.outline_count}, "
        f"holes={stats.hole_count}, "
        "outer_vertices="
        f"{stats.outer_vertex_count}, "
        "hole_vertices="
        f"{stats.hole_vertex_count}, "
        "total_vertices="
        f"{stats.total_vertex_count}, "
        "max_region_vertices="
        f"{stats.maximum_region_vertex_count}"
    )


def format_paired_stage_benchmark(
    *,
    name: str,
    benchmark: PairedStageBenchmark,
) -> str:
    """
    Format one paired downstream-stage benchmark.
    """
    return (
        f"{name}: "
        f"repeats={benchmark.repeat_count}, "
        "mandatory_median="
        f"{benchmark.mandatory_timings.median_seconds:.6f}s, "
        "reduced_median="
        f"{benchmark.reduced_timings.median_seconds:.6f}s, "
        "delta="
        f"{benchmark.median_delta_seconds:+.6f}s, "
        "delta_percent="
        f"{benchmark.median_delta_fraction * 100.0:+.2f}%, "
        "reduced_to_mandatory="
        f"{benchmark.reduced_to_mandatory_ratio:.3f}x"
    )


def _validate_repeats(
    repeats: int,
) -> None:
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )


def build_parser() -> ArgumentParser:
    """
    Build the complex downstream-performance parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark downstream region-processing stages "
            "for the complex representative image."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
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
        default=1,
        help=(
            "Number of paired downstream-stage repetitions. "
            "One is the default because complex outline "
            "simplification can be very expensive."
        ),
    )

    return parser


def main() -> None:
    """
    Benchmark complex downstream stages before and after reduction.
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

    loaded_config = load_config(
        args.config,
    )

    config = (
        loaded_config
        if args.minimum_region_size_mm is None
        else replace(
            loaded_config,
            minimum_region_size_mm=(args.minimum_region_size_mm),
        )
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

    prepared = prepare_case(
        case=BENCHMARK_CASE,
        config=config,
        palette=palette,
        color_distance=color_distance,
    )

    execution = execute_reduction(
        case=BENCHMARK_CASE,
        regions=prepared.regions,
        color_distance=color_distance,
        minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
        target_fraction=args.target_fraction,
        maximum_merge_cost=(config.region_complexity.maximum_merge_cost),
        cost_calculator=cost_calculator,
    )

    mandatory_regions = prepared.regions
    reduced_regions = execution.regions

    print(
        (
            f"case={BENCHMARK_CASE}, "
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            "minimum_region_size_mm="
            f"{config.minimum_region_size_mm:g}, "
            "maximum_merge_cost="
            f"{config.region_complexity.maximum_merge_cost:g}, "
            "target_fraction="
            f"{args.target_fraction:g}, "
            f"repeats={args.repeats}"
        ),
    )

    print(
        (
            "reduction_preparation: "
            "mandatory_regions="
            f"{len(mandatory_regions)}, "
            "max_regions="
            f"{execution.result.max_regions}, "
            "reduced_regions="
            f"{len(reduced_regions)}, "
            "accepted_merges="
            f"{len(mandatory_regions) - len(reduced_regions)}, "
            "reduction_seconds="
            f"{execution.result.reduction_seconds:.6f}s"
        ),
    )

    mandatory_region_stats = summarize_region_set(
        mandatory_regions,
    )

    reduced_region_stats = summarize_region_set(
        reduced_regions,
    )

    print(
        format_region_set_stats(
            name="mandatory_region_structure",
            stats=mandatory_region_stats,
        ),
    )

    print(
        format_region_set_stats(
            name="reduced_region_structure",
            stats=reduced_region_stats,
        ),
    )

    label_benchmark = benchmark_label_placement(
        mandatory_regions=mandatory_regions,
        reduced_regions=reduced_regions,
        repeats=args.repeats,
    )

    print(
        format_paired_stage_benchmark(
            name="label_placement",
            benchmark=label_benchmark,
        ),
    )

    outline_benchmark = benchmark_outline_simplification(
        mandatory_regions=mandatory_regions,
        reduced_regions=reduced_regions,
        tolerance=(config.outline_simplification_tolerance_px),
        repeats=args.repeats,
    )

    print(
        format_paired_stage_benchmark(
            name="outline_simplification",
            benchmark=outline_benchmark.timings,
        ),
    )

    print(
        format_outline_set_stats(
            name="mandatory_outline_structure",
            stats=outline_benchmark.mandatory_stats,
        ),
    )

    print(
        format_outline_set_stats(
            name="reduced_outline_structure",
            stats=outline_benchmark.reduced_stats,
        ),
    )


if __name__ == "__main__":
    main()
