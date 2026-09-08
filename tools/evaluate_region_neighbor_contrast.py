# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate all-neighbor color structure for accepted complexity merges.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path

from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    Region,
    RegionMergeStep,
)
from pbn.regions import RegionAdjacency
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    CandidateDiagnostic,
    format_result,
    palette_path,
    prepare_case,
    resolve_color_distance,
)
from tools.evaluate_region_detail_preservation import (
    DetailPreservingRegionMergeCostCalculator,
    build_accepted_merge_diagnostics,
    execute_detail_reduction,
)
from tools.profile_merge_cost_weights import (
    profile_merge_cost_weights,
)


@dataclass(frozen=True, slots=True)
class NeighborContrastDiagnostic:
    """
    All-neighbor color and boundary metrics for one accepted merge.
    """

    diagnostic: CandidateDiagnostic

    neighbor_count: int
    total_shared_border_length: int

    neighbor_boundary_coverage: float
    target_neighbor_border_fraction: float
    dominant_neighbor_border_fraction: float

    min_neighbor_color_difference: float
    max_neighbor_color_difference: float
    mean_neighbor_color_difference: float

    boundary_weighted_neighbor_color_difference: float
    boundary_weighted_neighbor_color_penalty: float


def build_neighbor_contrast_diagnostics(
    *,
    regions: tuple[Region, ...],
    merge_steps: tuple[RegionMergeStep, ...],
    color_distance: ColorDistance,
) -> tuple[NeighborContrastDiagnostic, ...]:
    """
    Evaluate all neighbors using the region state at each accepted merge.
    """
    accepted_diagnostics = build_accepted_merge_diagnostics(
        regions=regions,
        merge_steps=merge_steps,
    )

    active_regions = {region.id: region for region in regions}

    adjacency = RegionAdjacency()

    (
        shared_borders,
        has_overlapping_pixels,
    ) = adjacency.shared_borders_with_overlap_status(
        _ordered_regions(
            active_regions,
        ),
    )

    diagnostics: list[NeighborContrastDiagnostic] = []

    for accepted_diagnostic, merge_step in zip(
        accepted_diagnostics,
        merge_steps,
        strict=True,
    ):
        candidate = merge_step.candidate

        source = active_regions[candidate.source_id]
        target = active_regions[candidate.target_id]

        source_borders = shared_borders[source.id]

        diagnostics.append(
            _build_neighbor_contrast_diagnostic(
                diagnostic=accepted_diagnostic,
                source=source,
                target_id=target.id,
                source_borders=source_borders,
                active_regions=active_regions,
                color_distance=color_distance,
            ),
        )

        active_regions.pop(
            source.id,
        )

        active_regions[target.id] = Region(
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
                _ordered_regions(
                    active_regions,
                ),
            )
        else:
            adjacency.update_after_merge(
                shared_borders,
                source_id=source.id,
                target_id=target.id,
            )

    return tuple(
        diagnostics,
    )


def _build_neighbor_contrast_diagnostic(
    *,
    diagnostic: CandidateDiagnostic,
    source: Region,
    target_id: int,
    source_borders: dict[int, int],
    active_regions: dict[int, Region],
    color_distance: ColorDistance,
) -> NeighborContrastDiagnostic:
    """
    Build all-neighbor metrics for the current source region.
    """
    if target_id not in source_borders:
        raise ValueError(
            "accepted merge target must be adjacent to source",
        )

    neighbor_measurements = tuple(
        (
            neighbor_id,
            border_length,
            color_distance.distance(
                source.color.lab,
                active_regions[neighbor_id].color.lab,
            ),
        )
        for neighbor_id, border_length in sorted(
            source_borders.items(),
        )
    )

    total_shared_border_length = sum(
        border_length for _, border_length, _ in neighbor_measurements
    )

    if total_shared_border_length <= 0:
        raise ValueError(
            "accepted merge source must have a shared border",
        )

    color_differences = tuple(
        color_difference for _, _, color_difference in neighbor_measurements
    )

    target_shared_border_length = source_borders[target_id]

    dominant_shared_border_length = max(
        border_length for _, border_length, _ in neighbor_measurements
    )

    weighted_color_difference = sum(
        (border_length * color_difference)
        for _, border_length, color_difference in neighbor_measurements
    )

    weighted_color_penalty = sum(
        (
            border_length
            * _normalized_color_penalty(
                color_difference,
            )
        )
        for _, border_length, color_difference in neighbor_measurements
    )

    return NeighborContrastDiagnostic(
        diagnostic=diagnostic,
        neighbor_count=len(
            neighbor_measurements,
        ),
        total_shared_border_length=(total_shared_border_length),
        neighbor_boundary_coverage=(
            total_shared_border_length / diagnostic.metrics.source_perimeter
        ),
        target_neighbor_border_fraction=(
            target_shared_border_length / total_shared_border_length
        ),
        dominant_neighbor_border_fraction=(
            dominant_shared_border_length / total_shared_border_length
        ),
        min_neighbor_color_difference=min(
            color_differences,
        ),
        max_neighbor_color_difference=max(
            color_differences,
        ),
        mean_neighbor_color_difference=(
            sum(
                color_differences,
            )
            / len(
                color_differences,
            )
        ),
        boundary_weighted_neighbor_color_difference=(
            weighted_color_difference / total_shared_border_length
        ),
        boundary_weighted_neighbor_color_penalty=(
            weighted_color_penalty / total_shared_border_length
        ),
    )


def _normalized_color_penalty(
    color_difference: float,
) -> float:
    """
    Normalize color difference using the evaluated production mapping.
    """
    return color_difference / (color_difference + 10.0)


def format_neighbor_contrast_diagnostic(
    diagnostic: NeighborContrastDiagnostic,
    *,
    step_number: int,
) -> str:
    """
    Format correlated source-shape and all-neighbor metrics.
    """
    accepted = diagnostic.diagnostic
    candidate = accepted.candidate
    metrics = accepted.metrics

    return (
        f"    step={step_number}, "
        f"source_id={candidate.source_id}, "
        f"target_id={candidate.target_id}, "
        "source_color_number="
        f"{accepted.source_color_number}, "
        "source_color_name="
        f"{accepted.source_color_name}, "
        "target_color_number="
        f"{accepted.target_color_number}, "
        "target_color_name="
        f"{accepted.target_color_name}, "
        f"source_bounds={accepted.source_bounds}, "
        f"cost={accepted.cost.value:.6f}, "
        "source_non_compactness="
        f"{metrics.source_non_compactness:.6f}, "
        f"neighbor_count={diagnostic.neighbor_count}, "
        "neighbor_boundary_coverage="
        f"{diagnostic.neighbor_boundary_coverage:.6f}, "
        "target_neighbor_border_fraction="
        f"{diagnostic.target_neighbor_border_fraction:.6f}, "
        "dominant_neighbor_border_fraction="
        f"{diagnostic.dominant_neighbor_border_fraction:.6f}, "
        "target_color_difference="
        f"{metrics.color_difference:.6f}, "
        "min_neighbor_color_difference="
        f"{diagnostic.min_neighbor_color_difference:.6f}, "
        "max_neighbor_color_difference="
        f"{diagnostic.max_neighbor_color_difference:.6f}, "
        "mean_neighbor_color_difference="
        f"{diagnostic.mean_neighbor_color_difference:.6f}, "
        "boundary_weighted_neighbor_color_difference="
        f"{diagnostic.boundary_weighted_neighbor_color_difference:.6f}, "
        "boundary_weighted_neighbor_color_penalty="
        f"{diagnostic.boundary_weighted_neighbor_color_penalty:.6f}"
    )


def _ordered_regions(
    regions: dict[int, Region],
) -> tuple[Region, ...]:
    """
    Return active regions in deterministic id order.
    """
    return tuple(
        regions[region_id]
        for region_id in sorted(
            regions,
        )
    )


def build_parser() -> ArgumentParser:
    """
    Build the all-neighbor contrast evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate all-neighbor color structure for "
            "actual accepted region-complexity merges."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
        help=(
            "Generation configuration used to prepare " "the mandatory-merge baseline."
        ),
    )

    parser.add_argument(
        "--cases",
        nargs="+",
        choices=EVALUATION_CASES,
        default=EVALUATION_CASES,
        help="Representative image cases to evaluate.",
    )

    parser.add_argument(
        "--palette",
        default=None,
        help=("Palette id override. " "Uses the configuration value when omitted."),
    )

    parser.add_argument(
        "--palette-version",
        type=int,
        default=None,
        help=(
            "Palette version override. " "Uses the configuration value when omitted."
        ),
    )

    parser.add_argument(
        "--color-distance",
        default=None,
        help=("Color-distance override. " "Uses the configuration value when omitted."),
    )

    parser.add_argument(
        "--strength",
        type=float,
        required=True,
        help=("Experimental enclosure-based " "detail-preservation strength."),
    )

    parser.add_argument(
        "--target-fraction",
        type=float,
        required=True,
        help=(
            "Fraction of the mandatory-merge region count "
            "used to derive max_regions."
        ),
    )

    parser.add_argument(
        "--maximum-merge-costs",
        nargs="+",
        type=float,
        required=True,
        help=(
            "Merge-cost boundaries whose accepted merge "
            "sequences shall be evaluated."
        ),
    )

    return parser


def _validate_arguments(
    parser: ArgumentParser,
    args: Namespace,
) -> None:
    """
    Validate developer-tool arguments.
    """
    if not 0.0 <= args.strength <= 1.0:
        parser.error(
            "--strength must be between zero and one",
        )

    if not 0.0 < args.target_fraction <= 1.0:
        parser.error(
            "--target-fraction must be greater than zero " "and at most one",
        )

    if any(
        not 0.0 <= maximum_merge_cost <= 1.0
        for maximum_merge_cost in args.maximum_merge_costs
    ):
        parser.error(
            "--maximum-merge-costs values must be " "between zero and one",
        )


def main() -> None:
    """
    Evaluate all-neighbor structure for accepted merge sequences.
    """
    parser = build_parser()
    args = parser.parse_args()

    _validate_arguments(
        parser,
        args,
    )

    config = load_config(
        args.config,
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
            f"palette_version={selected_palette_version}, "
            f"color_distance={selected_color_distance}, "
            f"strength={args.strength}, "
            f"target_fraction={args.target_fraction}, "
            "maximum_merge_costs="
            f"{tuple(args.maximum_merge_costs)}"
        ),
    )

    calculator = DetailPreservingRegionMergeCostCalculator(
        strength=args.strength,
        **profile_merge_cost_weights(
            config,
        ),
    )

    for case in args.cases:
        prepared = prepare_case(
            case=case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

        print(
            (f"{case}: " f"baseline_regions={len(prepared.regions)}"),
        )

        for maximum_merge_cost in args.maximum_merge_costs:
            execution = execute_detail_reduction(
                case=case,
                regions=prepared.regions,
                color_distance=color_distance,
                minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
                target_fraction=args.target_fraction,
                maximum_merge_cost=maximum_merge_cost,
                cost_calculator=calculator,
            )

            print(
                ("  reduction=" f"{format_result(execution.result).strip()}"),
            )

            diagnostics = build_neighbor_contrast_diagnostics(
                regions=prepared.regions,
                merge_steps=execution.merge_steps,
                color_distance=color_distance,
            )

            print(
                ("    neighbor_contrast_diagnostics=" f"{len(diagnostics)}"),
            )

            for step_number, diagnostic in enumerate(
                diagnostics,
                start=1,
            ):
                print(
                    format_neighbor_contrast_diagnostic(
                        diagnostic,
                        step_number=step_number,
                    ),
                )


if __name__ == "__main__":
    main()
