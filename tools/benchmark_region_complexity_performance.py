# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark performance-critical optional region-complexity operations.

This developer-only module provides isolated timing measurements for
region-complexity processing without changing production behavior.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from pbn.application.region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)
from pbn.color.color_distance import ColorDistance
from pbn.config import RegionMergeCostConfig
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    Lab,
    Region,
    RegionMergeMetrics,
    RegionMergeStep,
)
from pbn.regions.adjacency import RegionAdjacency
from pbn.regions.complexity_reducer import RegionComplexityReducer
from pbn.regions.merge_candidate_builder import (
    RegionMergeCandidateBuilder,
)
from pbn.regions.merge_candidate_ranker import (
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
    resolve_max_regions,
)

NeighborContrastInput = tuple[
    Lab,
    tuple[
        tuple[
            int,
            Lab,
        ],
        ...,
    ],
]


@dataclass(frozen=True, slots=True)
class DurationSummary:
    """
    Timing distribution for repeated benchmark executions.
    """

    repeat_count: int
    minimum_seconds: float
    median_seconds: float
    mean_seconds: float
    maximum_seconds: float


@dataclass(frozen=True, slots=True)
class InitialCandidateConstructionBenchmark:
    """
    Benchmark result for initial merge-candidate construction.
    """

    region_count: int
    candidate_count: int
    timings: DurationSummary


@dataclass(frozen=True, slots=True)
class IncrementalAdjacencyUpdateBenchmark:
    """
    Benchmark result for incremental adjacency updates.
    """

    update_count: int
    timings: DurationSummary


@dataclass(frozen=True, slots=True)
class IncrementalCandidateMaintenanceBenchmark:
    """
    Benchmark result for incremental candidate maintenance.
    """

    maintenance_count: int
    timings: DurationSummary


@dataclass(frozen=True, slots=True)
class FullCandidateRecalculationBenchmark:
    """
    Benchmark result for full candidate recalculation.
    """

    recalculation_count: int
    timings: DurationSummary


@dataclass(frozen=True, slots=True)
class DetailPreservationCostCalculationBenchmark:
    """
    Benchmark result for detail-preservation cost calculation.
    """

    evaluation_count: int
    base_timings: DurationSummary
    detail_timings: DurationSummary


@dataclass(frozen=True, slots=True)
class AllNeighborColorContrastCalculationBenchmark:
    """
    Benchmark result for all-neighbor color-contrast calculation.
    """

    evaluation_count: int
    neighbor_measurement_count: int
    timings: DurationSummary


def summarize_durations(
    durations: tuple[float, ...],
) -> DurationSummary:
    """
    Summarize repeated benchmark durations.
    """
    if not durations:
        raise ValueError(
            "durations must not be empty",
        )

    return DurationSummary(
        repeat_count=len(durations),
        minimum_seconds=min(durations),
        median_seconds=median(durations),
        mean_seconds=mean(durations),
        maximum_seconds=max(durations),
    )


def build_base_region_merge_cost_calculator(
    config: RegionMergeCostConfig,
) -> RegionMergeCostCalculator:
    """
    Build the base merge-cost calculator from configured component weights.
    """
    return RegionMergeCostCalculator(
        color_weight=config.color_weight,
        affected_area_weight=config.affected_area_weight,
        border_weight=config.border_weight,
        geometry_weight=config.geometry_weight,
    )


def benchmark_initial_candidate_construction(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    repeats: int,
) -> InitialCandidateConstructionBenchmark:
    """
    Benchmark cold initial directed merge-candidate construction.

    A fresh candidate builder is created for every repetition so internal
    metric caches cannot make later repetitions cheaper than the first.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    durations: list[float] = []
    candidate_count: int | None = None

    for _ in range(repeats):
        builder = RegionMergeCandidateBuilder(
            color_distance=color_distance,
        )

        started_at = perf_counter()

        evaluations = builder.build(
            regions,
        )

        finished_at = perf_counter()

        durations.append(
            finished_at - started_at,
        )

        current_candidate_count = len(
            evaluations,
        )

        if candidate_count is None:
            candidate_count = current_candidate_count
        elif current_candidate_count != candidate_count:
            raise RuntimeError(
                "Initial candidate count changed between benchmark repeats.",
            )

    assert candidate_count is not None

    return InitialCandidateConstructionBenchmark(
        region_count=len(regions),
        candidate_count=candidate_count,
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def benchmark_detail_preservation_cost_calculation(
    *,
    metrics: tuple[RegionMergeMetrics, ...],
    base_calculator: RegionMergeCostCalculator,
    detail_calculator: RegionMergeCostCalculator,
    repeats: int,
) -> DetailPreservationCostCalculationBenchmark:
    """
    Benchmark base and detail-preserving merge-cost calculation separately.

    Raw merge metrics are supplied precomputed so candidate construction,
    adjacency processing and metric calculation remain outside the measured
    durations.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    base_durations: list[float] = []
    detail_durations: list[float] = []

    for _ in range(repeats):
        started_at = perf_counter()

        tuple(base_calculator.calculate(metric) for metric in metrics)

        finished_at = perf_counter()

        base_durations.append(
            finished_at - started_at,
        )

        started_at = perf_counter()

        tuple(detail_calculator.calculate(metric) for metric in metrics)

        finished_at = perf_counter()

        detail_durations.append(
            finished_at - started_at,
        )

    return DetailPreservationCostCalculationBenchmark(
        evaluation_count=len(metrics),
        base_timings=summarize_durations(
            tuple(base_durations),
        ),
        detail_timings=summarize_durations(
            tuple(detail_durations),
        ),
    )


def benchmark_detail_preservation_cost_calculation_for_regions(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    base_calculator: RegionMergeCostCalculator,
    detail_calculator: RegionMergeCostCalculator,
    repeats: int,
) -> DetailPreservationCostCalculationBenchmark:
    """
    Benchmark merge-cost calculation for real directed region candidates.

    Candidate construction and raw metric calculation are completed before
    timing so the measured durations cover only base and detail-preserving
    merge-cost calculation.
    """
    candidate_builder = RegionMergeCandidateBuilder(
        color_distance=color_distance,
    )

    evaluations = candidate_builder.build(
        regions,
    )

    metrics = tuple(candidate_metrics for _, candidate_metrics in evaluations)

    return benchmark_detail_preservation_cost_calculation(
        metrics=metrics,
        base_calculator=base_calculator,
        detail_calculator=detail_calculator,
        repeats=repeats,
    )


def benchmark_all_neighbor_color_contrast_calculation(
    *,
    regions: tuple[Region, ...],
    merge_steps: tuple[RegionMergeStep, ...],
    color_distance: ColorDistance,
    repeats: int,
) -> AllNeighborColorContrastCalculationBenchmark:
    """
    Benchmark all-neighbor color-contrast calculation for accepted merges.

    Dynamic region and adjacency states are reconstructed once before timing.
    The measured durations contain only per-neighbor color-distance evaluation
    and the derived aggregate contrast calculations.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    contrast_inputs = _prepare_all_neighbor_color_contrast_inputs(
        regions=regions,
        merge_steps=merge_steps,
    )

    neighbor_measurement_count = sum(len(neighbors) for _, neighbors in contrast_inputs)

    durations: list[float] = []

    for _ in range(repeats):
        started_at = perf_counter()

        for source_lab, neighbors in contrast_inputs:
            measurements = tuple(
                (
                    border_length,
                    color_distance.distance(
                        source_lab,
                        neighbor_lab,
                    ),
                )
                for border_length, neighbor_lab in neighbors
            )

            total_shared_border_length = sum(
                border_length for border_length, _ in measurements
            )

            if total_shared_border_length <= 0:
                raise ValueError(
                    "accepted merge source must have a shared border",
                )

            color_differences = tuple(
                color_difference for _, color_difference in measurements
            )

            if not color_differences:
                raise ValueError(
                    "accepted merge source must have at least one neighbor",
                )

            weighted_color_difference = sum(
                border_length * color_difference
                for border_length, color_difference in measurements
            )

            weighted_color_penalty = sum(
                border_length * (color_difference / (color_difference + 10.0))
                for border_length, color_difference in measurements
            )

            _ = (
                min(
                    color_differences,
                ),
                max(
                    color_differences,
                ),
                (
                    sum(
                        color_differences,
                    )
                    / len(
                        color_differences,
                    )
                ),
                (weighted_color_difference / total_shared_border_length),
                (weighted_color_penalty / total_shared_border_length),
            )

        finished_at = perf_counter()

        durations.append(
            finished_at - started_at,
        )

    return AllNeighborColorContrastCalculationBenchmark(
        evaluation_count=len(
            contrast_inputs,
        ),
        neighbor_measurement_count=neighbor_measurement_count,
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def benchmark_all_neighbor_color_contrast_calculation_for_regions(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    minimum_circle_diameter_px: int,
    max_regions: int,
    maximum_merge_cost: float,
    repeats: int,
) -> AllNeighborColorContrastCalculationBenchmark:
    """
    Benchmark all-neighbor contrast for an actual reducer merge sequence.

    The reducer trace is generated before the isolated benchmark so reducer
    execution itself remains outside the measured durations.
    """
    reducer = RegionComplexityReducer(
        color_distance=color_distance,
        cost_calculator=cost_calculator,
    )

    _, merge_steps = reducer.reduce_with_trace(
        regions,
        minimum_circle_diameter_px=minimum_circle_diameter_px,
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    return benchmark_all_neighbor_color_contrast_calculation(
        regions=regions,
        merge_steps=merge_steps,
        color_distance=color_distance,
        repeats=repeats,
    )


def _prepare_all_neighbor_color_contrast_inputs(
    *,
    regions: tuple[Region, ...],
    merge_steps: tuple[RegionMergeStep, ...],
) -> tuple[NeighborContrastInput, ...]:
    """
    Reconstruct all dynamic neighbor inputs without measuring preparation.
    """
    active_regions = {region.id: region for region in regions}

    adjacency = RegionAdjacency()

    (
        shared_borders,
        has_overlapping_pixels,
    ) = adjacency.shared_borders_with_overlap_status(
        regions,
    )

    contrast_inputs: list[NeighborContrastInput] = []

    for merge_step in merge_steps:
        source_id = merge_step.candidate.source_id
        target_id = merge_step.candidate.target_id

        source = active_regions[source_id]
        target = active_regions[target_id]

        source_borders = shared_borders[source_id]

        if target_id not in source_borders:
            raise ValueError(
                "accepted merge target must be adjacent to source",
            )

        neighbors = tuple(
            (
                border_length,
                active_regions[neighbor_id].color.lab,
            )
            for neighbor_id, border_length in sorted(
                source_borders.items(),
            )
        )

        contrast_inputs.append(
            (
                source.color.lab,
                neighbors,
            ),
        )

        active_regions.pop(
            source_id,
        )

        active_regions[target_id] = Region(
            id=target.id,
            color=target.color,
            pixels=frozenset(
                target.pixels | source.pixels,
            ),
        )

        if has_overlapping_pixels:
            (
                shared_borders,
                has_overlapping_pixels,
            ) = adjacency.shared_borders_with_overlap_status(
                tuple(
                    active_regions[region_id]
                    for region_id in sorted(
                        active_regions,
                    )
                ),
            )
        else:
            adjacency.update_after_merge(
                shared_borders,
                source_id=source_id,
                target_id=target_id,
            )

    return tuple(
        contrast_inputs,
    )


def benchmark_incremental_adjacency_updates(
    *,
    shared_borders: dict[int, dict[int, int]],
    merge_pairs: tuple[tuple[int, int], ...],
    repeats: int,
) -> IncrementalAdjacencyUpdateBenchmark:
    """
    Benchmark replayed incremental adjacency updates.

    The initial adjacency mapping is copied before each timed repetition so
    every repetition starts from the same state while copy overhead remains
    outside the measured update duration.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    adjacency = RegionAdjacency()
    durations: list[float] = []

    for _ in range(repeats):
        working_shared_borders = {
            region_id: dict(border_lengths)
            for region_id, border_lengths in shared_borders.items()
        }

        started_at = perf_counter()

        for source_id, target_id in merge_pairs:
            adjacency.update_after_merge(
                working_shared_borders,
                source_id=source_id,
                target_id=target_id,
            )

        finished_at = perf_counter()

        durations.append(
            finished_at - started_at,
        )

    return IncrementalAdjacencyUpdateBenchmark(
        update_count=len(merge_pairs),
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def benchmark_incremental_candidate_maintenance(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    merge_pairs: tuple[tuple[int, int], ...],
    repeats: int,
) -> IncrementalCandidateMaintenanceBenchmark:
    """
    Benchmark incremental candidate maintenance for accepted merges.

    Initial adjacency and candidate construction, region mutation and
    incremental adjacency updates remain outside the measured duration.
    Only stale-candidate invalidation and affected-candidate recalculation
    are timed.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    durations: list[float] = []

    for _ in range(repeats):
        adjacency = RegionAdjacency()
        candidate_builder = RegionMergeCandidateBuilder(
            color_distance=color_distance,
        )
        candidate_ranker = RegionMergeCandidateRanker(
            cost_calculator=cost_calculator,
        )

        active_regions = {region.id: region for region in regions}

        (
            shared_borders,
            has_overlapping_pixels,
        ) = adjacency.shared_borders_with_overlap_status(
            regions,
        )

        if has_overlapping_pixels:
            raise ValueError(
                "Incremental candidate benchmarking requires disjoint regions.",
            )

        initial_evaluations = candidate_ranker.rank(
            candidate_builder.build_from_shared_borders(
                regions_by_id=active_regions,
                shared_borders=shared_borders,
                touching_region_ids=None,
            ),
        )

        candidate_evaluations = {
            evaluation[0]: evaluation for evaluation in initial_evaluations
        }

        total_seconds = 0.0

        for source_id, target_id in merge_pairs:
            source = active_regions[source_id]
            target = active_regions[target_id]

            active_regions.pop(
                source_id,
            )
            active_regions[target_id] = Region(
                id=target.id,
                color=target.color,
                pixels=frozenset(
                    target.pixels | source.pixels,
                ),
            )

            adjacency.update_after_merge(
                shared_borders,
                source_id=source_id,
                target_id=target_id,
            )

            started_at = perf_counter()

            affected_region_ids = frozenset(
                {
                    source_id,
                    target_id,
                },
            )

            stale_candidates = tuple(
                candidate
                for candidate in candidate_evaluations
                if (
                    candidate.source_id in affected_region_ids
                    or candidate.target_id in affected_region_ids
                )
            )

            for candidate in stale_candidates:
                candidate_evaluations.pop(
                    candidate,
                )

            updated_evaluations = candidate_ranker.rank(
                candidate_builder.build_from_shared_borders(
                    regions_by_id=active_regions,
                    shared_borders=shared_borders,
                    touching_region_ids=frozenset(
                        {
                            target_id,
                        },
                    ),
                ),
            )

            candidate_evaluations.update(
                {evaluation[0]: evaluation for evaluation in updated_evaluations},
            )

            finished_at = perf_counter()

            total_seconds += finished_at - started_at

        durations.append(
            total_seconds,
        )

    return IncrementalCandidateMaintenanceBenchmark(
        maintenance_count=len(merge_pairs),
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def benchmark_full_candidate_recalculation(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    merge_pairs: tuple[tuple[int, int], ...],
    repeats: int,
) -> FullCandidateRecalculationBenchmark:
    """
    Benchmark full candidate recalculation after accepted merges.

    Region mutation and incremental adjacency updates remain outside the
    measured duration. Each timed step rebuilds and ranks every currently
    possible directed candidate from the updated adjacency information.
    """
    if repeats <= 0:
        raise ValueError(
            "repeats must be greater than zero",
        )

    durations: list[float] = []

    for _ in range(repeats):
        adjacency = RegionAdjacency()
        candidate_builder = RegionMergeCandidateBuilder(
            color_distance=color_distance,
        )
        candidate_ranker = RegionMergeCandidateRanker(
            cost_calculator=cost_calculator,
        )

        active_regions = {region.id: region for region in regions}

        (
            shared_borders,
            has_overlapping_pixels,
        ) = adjacency.shared_borders_with_overlap_status(
            regions,
        )

        if has_overlapping_pixels:
            raise ValueError(
                "Full candidate recalculation benchmarking "
                "requires disjoint regions.",
            )

        total_seconds = 0.0

        for source_id, target_id in merge_pairs:
            source = active_regions[source_id]
            target = active_regions[target_id]

            active_regions.pop(
                source_id,
            )
            active_regions[target_id] = Region(
                id=target.id,
                color=target.color,
                pixels=frozenset(
                    target.pixels | source.pixels,
                ),
            )

            adjacency.update_after_merge(
                shared_borders,
                source_id=source_id,
                target_id=target_id,
            )

            started_at = perf_counter()

            recalculated_evaluations = candidate_ranker.rank(
                candidate_builder.build_from_shared_borders(
                    regions_by_id=active_regions,
                    shared_borders=shared_borders,
                    touching_region_ids=None,
                ),
            )

            candidate_evaluations = {
                evaluation[0]: evaluation for evaluation in recalculated_evaluations
            }

            finished_at = perf_counter()

            total_seconds += finished_at - started_at

            if (
                not candidate_evaluations
                and len(active_regions) > 1
                and any(shared_borders[region_id] for region_id in shared_borders)
            ):
                raise RuntimeError(
                    "Full candidate recalculation produced "
                    "an inconsistent empty candidate cache.",
                )

        durations.append(
            total_seconds,
        )

    return FullCandidateRecalculationBenchmark(
        recalculation_count=len(merge_pairs),
        timings=summarize_durations(
            tuple(durations),
        ),
    )


def benchmark_incremental_candidate_maintenance_for_regions(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    minimum_circle_diameter_px: int,
    max_regions: int,
    maximum_merge_cost: float,
    repeats: int,
) -> IncrementalCandidateMaintenanceBenchmark:
    """
    Benchmark candidate maintenance for an actual reducer merge sequence.

    The reducer trace is generated outside the measured duration so only
    incremental stale-candidate invalidation and affected-candidate
    recalculation are benchmarked.
    """
    merge_pairs = build_accepted_merge_pairs(
        regions=regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        minimum_circle_diameter_px=minimum_circle_diameter_px,
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    return benchmark_incremental_candidate_maintenance(
        regions=regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        merge_pairs=merge_pairs,
        repeats=repeats,
    )


def benchmark_full_candidate_recalculation_for_regions(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    minimum_circle_diameter_px: int,
    max_regions: int,
    maximum_merge_cost: float,
    repeats: int,
) -> FullCandidateRecalculationBenchmark:
    """
    Benchmark full candidate recalculation for an actual reducer merge sequence.

    The reducer trace is generated outside the measured duration so the
    benchmark covers only complete candidate rebuilding and ranking after each
    accepted merge.
    """
    merge_pairs = build_accepted_merge_pairs(
        regions=regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        minimum_circle_diameter_px=minimum_circle_diameter_px,
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    return benchmark_full_candidate_recalculation(
        regions=regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        merge_pairs=merge_pairs,
        repeats=repeats,
    )


def build_accepted_merge_pairs(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    minimum_circle_diameter_px: int,
    max_regions: int,
    maximum_merge_cost: float,
) -> tuple[tuple[int, int], ...]:
    """
    Return the directed merge pairs accepted by the real reducer.
    """
    reducer = RegionComplexityReducer(
        color_distance=color_distance,
        cost_calculator=cost_calculator,
    )

    _, merge_steps = reducer.reduce_with_trace(
        regions,
        minimum_circle_diameter_px=minimum_circle_diameter_px,
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    return tuple(
        (
            step.candidate.source_id,
            step.candidate.target_id,
        )
        for step in merge_steps
    )


def benchmark_incremental_adjacency_updates_for_regions(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    minimum_circle_diameter_px: int,
    max_regions: int,
    maximum_merge_cost: float,
    repeats: int,
) -> IncrementalAdjacencyUpdateBenchmark:
    """
    Benchmark incremental adjacency updates for an actual reducer sequence.

    Initial adjacency construction and reducer tracing are intentionally
    performed outside the measured update duration.
    """
    adjacency = RegionAdjacency()

    shared_borders, has_overlapping_pixels = (
        adjacency.shared_borders_with_overlap_status(
            regions,
        )
    )

    if has_overlapping_pixels:
        raise ValueError(
            "Incremental adjacency benchmarking requires disjoint regions.",
        )

    merge_pairs = build_accepted_merge_pairs(
        regions=regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
        minimum_circle_diameter_px=minimum_circle_diameter_px,
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    return benchmark_incremental_adjacency_updates(
        shared_borders=shared_borders,
        merge_pairs=merge_pairs,
        repeats=repeats,
    )


def format_initial_candidate_construction_benchmark(
    *,
    case: str,
    benchmark: InitialCandidateConstructionBenchmark,
) -> str:
    """
    Format one initial candidate-construction benchmark result.
    """
    timings = benchmark.timings

    return (
        f"{case}: "
        f"regions={benchmark.region_count}, "
        f"candidates={benchmark.candidate_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s"
    )


def format_incremental_adjacency_update_benchmark(
    *,
    case: str,
    benchmark: IncrementalAdjacencyUpdateBenchmark,
) -> str:
    """
    Format one incremental adjacency-update benchmark result.
    """
    timings = benchmark.timings

    return (
        f"{case}: "
        "incremental_adjacency_updates="
        f"{benchmark.update_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s"
    )


def format_incremental_candidate_maintenance_benchmark(
    *,
    case: str,
    benchmark: IncrementalCandidateMaintenanceBenchmark,
) -> str:
    """
    Format one incremental candidate-maintenance benchmark result.
    """
    timings = benchmark.timings

    return (
        f"{case}: "
        "incremental_candidate_maintenance="
        f"{benchmark.maintenance_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s"
    )


def format_full_candidate_recalculation_benchmark(
    *,
    case: str,
    benchmark: FullCandidateRecalculationBenchmark,
) -> str:
    """
    Format one full candidate-recalculation benchmark result.
    """
    timings = benchmark.timings

    return (
        f"{case}: "
        "full_candidate_recalculation="
        f"{benchmark.recalculation_count}, "
        f"repeats={timings.repeat_count}, "
        f"minimum={timings.minimum_seconds:.6f}s, "
        f"median={timings.median_seconds:.6f}s, "
        f"mean={timings.mean_seconds:.6f}s, "
        f"maximum={timings.maximum_seconds:.6f}s"
    )


def format_detail_preservation_cost_calculation_benchmark(
    *,
    case: str,
    benchmark: DetailPreservationCostCalculationBenchmark,
) -> str:
    """
    Format one detail-preservation cost-calculation benchmark result.
    """
    base_median = benchmark.base_timings.median_seconds
    detail_median = benchmark.detail_timings.median_seconds
    median_overhead = detail_median - base_median

    if base_median == 0.0:
        detail_to_base = float("inf")
    else:
        detail_to_base = detail_median / base_median

    return (
        f"{case}: "
        "detail_preservation_evaluations="
        f"{benchmark.evaluation_count}, "
        f"repeats={benchmark.base_timings.repeat_count}, "
        f"base_median={base_median:.6f}s, "
        f"detail_median={detail_median:.6f}s, "
        f"median_overhead={median_overhead:.6f}s, "
        f"detail_to_base={detail_to_base:.3f}x"
    )


def build_parser() -> ArgumentParser:
    """
    Build the region-complexity performance benchmark parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark performance-critical optional " "region-complexity operations."
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
    Benchmark region-complexity operations on representative images.
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

    base_cost_calculator = build_base_region_merge_cost_calculator(
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

        candidate_benchmark = benchmark_initial_candidate_construction(
            regions=prepared.regions,
            color_distance=color_distance,
            repeats=args.repeats,
        )

        print(
            format_initial_candidate_construction_benchmark(
                case=case,
                benchmark=candidate_benchmark,
            ),
        )

        detail_preservation_benchmark = (
            benchmark_detail_preservation_cost_calculation_for_regions(
                regions=prepared.regions,
                color_distance=color_distance,
                base_calculator=base_cost_calculator,
                detail_calculator=cost_calculator,
                repeats=args.repeats,
            )
        )

        print(
            format_detail_preservation_cost_calculation_benchmark(
                case=case,
                benchmark=detail_preservation_benchmark,
            ),
        )

        max_regions = resolve_max_regions(
            baseline_region_count=len(
                prepared.regions,
            ),
            target_fraction=args.target_fraction,
        )

        adjacency_benchmark = benchmark_incremental_adjacency_updates_for_regions(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=cost_calculator,
            minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            repeats=args.repeats,
        )

        print(
            format_incremental_adjacency_update_benchmark(
                case=case,
                benchmark=adjacency_benchmark,
            ),
        )

        incremental_benchmark = benchmark_incremental_candidate_maintenance_for_regions(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=cost_calculator,
            minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            repeats=args.repeats,
        )

        print(
            format_incremental_candidate_maintenance_benchmark(
                case=case,
                benchmark=incremental_benchmark,
            ),
        )

        full_recalculation_benchmark = (
            benchmark_full_candidate_recalculation_for_regions(
                regions=prepared.regions,
                color_distance=color_distance,
                cost_calculator=cost_calculator,
                minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
                max_regions=max_regions,
                maximum_merge_cost=maximum_merge_cost,
                repeats=args.repeats,
            )
        )

        print(
            format_full_candidate_recalculation_benchmark(
                case=case,
                benchmark=full_recalculation_benchmark,
            ),
        )


if __name__ == "__main__":
    main()
