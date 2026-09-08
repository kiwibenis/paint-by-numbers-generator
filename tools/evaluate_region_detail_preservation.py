# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate an experimental local detail-preservation merge-cost signal.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    Region,
    RegionMergeCost,
    RegionMergeMetrics,
    RegionMergeStep,
)
from pbn.regions.complexity_reducer import RegionComplexityReducer
from pbn.regions.merge_cost_calculator import (
    RegionMergeCostCalculator,
)
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    PREVIEW_OUTPUT_DIRECTORY,
    REPOSITORY_ROOT,
    CandidateDiagnostic,
    ComplexityReductionResult,
    build_candidate_diagnostics,
    format_result,
    palette_path,
    prepare_case,
    resolve_color_distance,
    resolve_max_regions,
    write_region_preview,
)
from tools.profile_merge_cost_weights import (
    profile_merge_cost_weights,
)

DEFAULT_TARGET_FRACTION = 0.25

DEFAULT_MAXIMUM_MERGE_COSTS = (
    0.48,
    0.50,
    0.52,
    0.54,
)


@dataclass(frozen=True, slots=True)
class DetailPreservationEvaluation:
    """
    Experimental detail-preservation evaluation for one merge candidate.
    """

    diagnostic: CandidateDiagnostic
    protection_penalty: float
    adjusted_cost: float


@dataclass(frozen=True, slots=True)
class DetailPreservationReductionExecution:
    """
    One full reducer execution with its actual accepted merge sequence.
    """

    result: ComplexityReductionResult
    regions: tuple[Region, ...]
    merge_steps: tuple[RegionMergeStep, ...]


class DetailPreservingRegionMergeCostCalculator(
    RegionMergeCostCalculator,
):
    """
    Apply an experimental detail-preservation adjustment to merge costs.
    """

    def __init__(
        self,
        *,
        strength: float,
        color_weight: float,
        affected_area_weight: float,
        border_weight: float,
        geometry_weight: float,
    ) -> None:
        super().__init__(
            color_weight=color_weight,
            affected_area_weight=affected_area_weight,
            border_weight=border_weight,
            geometry_weight=geometry_weight,
        )

        _validate_unit_interval(
            name="strength",
            value=strength,
        )

        self._strength = strength

    def calculate(
        self,
        metrics: RegionMergeMetrics,
    ) -> RegionMergeCost:
        """
        Calculate the production cost and apply experimental protection.
        """
        base_cost = super().calculate(
            metrics,
        )

        protection_penalty = detail_preservation_penalty_from_components(
            source_shared_border_ratio=(metrics.source_shared_border_ratio),
            color_penalty=base_cost.color_penalty,
            affected_area_ratio=(metrics.affected_area_ratio),
        )

        adjusted_cost = adjusted_detail_preservation_cost(
            base_cost=base_cost.value,
            protection_penalty=protection_penalty,
            strength=self._strength,
        )

        return RegionMergeCost(
            color_penalty=base_cost.color_penalty,
            affected_area_penalty=(base_cost.affected_area_penalty),
            border_penalty=base_cost.border_penalty,
            geometry_penalty=base_cost.geometry_penalty,
            value=adjusted_cost,
        )


def _validate_unit_interval(
    *,
    name: str,
    value: float,
) -> None:
    """
    Validate an experimental normalized parameter.
    """
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{name} must be between zero and one",
        )


def detail_preservation_penalty_from_components(
    *,
    source_shared_border_ratio: float,
    color_penalty: float,
    affected_area_ratio: float,
) -> float:
    """
    Calculate protection from normalized existing merge-cost signals.
    """
    return source_shared_border_ratio * color_penalty * (1.0 - affected_area_ratio)


def detail_preservation_penalty(
    diagnostic: CandidateDiagnostic,
) -> float:
    """
    Calculate the experimental local detail-preservation signal.
    """
    return detail_preservation_penalty_from_components(
        source_shared_border_ratio=(diagnostic.metrics.source_shared_border_ratio),
        color_penalty=diagnostic.cost.color_penalty,
        affected_area_ratio=(diagnostic.metrics.affected_area_ratio),
    )


def adjusted_detail_preservation_cost(
    *,
    base_cost: float,
    protection_penalty: float,
    strength: float,
) -> float:
    """
    Increase an existing merge cost by an experimental protection signal.
    """
    _validate_unit_interval(
        name="strength",
        value=strength,
    )
    _validate_unit_interval(
        name="base_cost",
        value=base_cost,
    )
    _validate_unit_interval(
        name="protection_penalty",
        value=protection_penalty,
    )

    return base_cost + strength * protection_penalty * (1.0 - base_cost)


def evaluate_detail_preservation(
    *,
    diagnostics: tuple[
        CandidateDiagnostic,
        ...,
    ],
    strength: float,
) -> tuple[
    DetailPreservationEvaluation,
    ...,
]:
    """
    Re-rank existing merge candidates with experimental detail protection.
    """
    evaluations = tuple(
        _evaluate_candidate(
            diagnostic=diagnostic,
            strength=strength,
        )
        for diagnostic in diagnostics
    )

    return tuple(
        sorted(
            evaluations,
            key=lambda evaluation: (
                evaluation.adjusted_cost,
                evaluation.diagnostic.candidate.source_id,
                evaluation.diagnostic.candidate.target_id,
            ),
        ),
    )


def _evaluate_candidate(
    *,
    diagnostic: CandidateDiagnostic,
    strength: float,
) -> DetailPreservationEvaluation:
    """
    Evaluate one initial candidate with experimental detail protection.
    """
    protection_penalty = detail_preservation_penalty(
        diagnostic,
    )

    return DetailPreservationEvaluation(
        diagnostic=diagnostic,
        protection_penalty=protection_penalty,
        adjusted_cost=(
            adjusted_detail_preservation_cost(
                base_cost=diagnostic.cost.value,
                protection_penalty=protection_penalty,
                strength=strength,
            )
        ),
    )


def execute_detail_reduction(
    *,
    case: str,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    minimum_circle_diameter_px: int,
    target_fraction: float,
    maximum_merge_cost: float,
    cost_calculator: RegionMergeCostCalculator,
) -> DetailPreservationReductionExecution:
    """
    Execute full reduction and retain the actual accepted merge sequence.
    """
    _validate_unit_interval(
        name="maximum_merge_cost",
        value=maximum_merge_cost,
    )

    baseline_region_count = len(
        regions,
    )

    max_regions = resolve_max_regions(
        baseline_region_count=baseline_region_count,
        target_fraction=target_fraction,
    )

    started_at = perf_counter()

    (
        reduced_regions,
        merge_steps,
    ) = RegionComplexityReducer(
        color_distance=color_distance,
        cost_calculator=cost_calculator,
    ).reduce_with_trace(
        regions,
        minimum_circle_diameter_px=(minimum_circle_diameter_px),
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    finished_at = perf_counter()

    return DetailPreservationReductionExecution(
        result=ComplexityReductionResult(
            case=case,
            baseline_region_count=baseline_region_count,
            target_fraction=target_fraction,
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            final_region_count=len(
                reduced_regions,
            ),
            reduction_seconds=(finished_at - started_at),
        ),
        regions=reduced_regions,
        merge_steps=merge_steps,
    )


def build_accepted_merge_diagnostics(
    *,
    regions: tuple[Region, ...],
    merge_steps: tuple[RegionMergeStep, ...],
) -> tuple[CandidateDiagnostic, ...]:
    """
    Reconstruct dynamic source and target state for accepted merge steps.
    """
    active_regions = {region.id: region for region in regions}

    diagnostics: list[CandidateDiagnostic] = []

    for merge_step in merge_steps:
        candidate = merge_step.candidate

        source = active_regions[candidate.source_id]
        target = active_regions[candidate.target_id]

        diagnostics.append(
            CandidateDiagnostic(
                candidate=candidate,
                source_color_number=source.color.number,
                source_color_name=source.color.name,
                target_color_number=target.color.number,
                target_color_name=target.color.name,
                source_bounds=_region_bounds(
                    source,
                ),
                target_bounds=_region_bounds(
                    target,
                ),
                metrics=merge_step.metrics,
                cost=merge_step.cost,
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

    return tuple(
        diagnostics,
    )


def _region_bounds(
    region: Region,
) -> tuple[int, int, int, int]:
    """
    Return the inclusive raster bounding box for developer diagnostics.
    """
    coordinates = tuple(
        region.coordinates(),
    )

    xs = tuple(x for x, _ in coordinates)
    ys = tuple(y for _, y in coordinates)

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    )


def format_accepted_merge_diagnostic(
    diagnostic: CandidateDiagnostic,
    *,
    step_number: int,
) -> str:
    """
    Format one accepted merge using its state at selection time.
    """
    candidate = diagnostic.candidate
    metrics = diagnostic.metrics
    cost = diagnostic.cost

    return (
        f"    step={step_number}, "
        f"source_id={candidate.source_id}, "
        f"target_id={candidate.target_id}, "
        "source_color_number="
        f"{diagnostic.source_color_number}, "
        "source_color_name="
        f"{diagnostic.source_color_name}, "
        "target_color_number="
        f"{diagnostic.target_color_number}, "
        "target_color_name="
        f"{diagnostic.target_color_name}, "
        f"source_bounds={diagnostic.source_bounds}, "
        f"target_bounds={diagnostic.target_bounds}, "
        f"cost={cost.value:.6f}, "
        "color_difference="
        f"{metrics.color_difference:.6f}, "
        f"source_area={metrics.source_area}, "
        f"target_area={metrics.target_area}, "
        "affected_area_ratio="
        f"{metrics.affected_area_ratio:.6f}, "
        f"source_perimeter={metrics.source_perimeter}, "
        "source_shared_border_ratio="
        f"{metrics.source_shared_border_ratio:.6f}, "
        f"color_penalty={cost.color_penalty:.6f}, "
        f"border_penalty={cost.border_penalty:.6f}, "
        f"geometry_penalty={cost.geometry_penalty:.6f}"
    )


def format_evaluation(
    evaluation: DetailPreservationEvaluation,
    *,
    rank: int,
) -> str:
    """
    Format one experimentally re-ranked merge candidate.
    """
    diagnostic = evaluation.diagnostic
    candidate = diagnostic.candidate
    metrics = diagnostic.metrics

    return (
        f"  rank={rank}, "
        f"source_id={candidate.source_id}, "
        f"target_id={candidate.target_id}, "
        "source_color_number="
        f"{diagnostic.source_color_number}, "
        "source_color_name="
        f"{diagnostic.source_color_name}, "
        "target_color_number="
        f"{diagnostic.target_color_number}, "
        "target_color_name="
        f"{diagnostic.target_color_name}, "
        f"source_bounds={diagnostic.source_bounds}, "
        f"target_bounds={diagnostic.target_bounds}, "
        f"base_cost={diagnostic.cost.value:.6f}, "
        "detail_preservation_penalty="
        f"{evaluation.protection_penalty:.6f}, "
        f"adjusted_cost={evaluation.adjusted_cost:.6f}, "
        "color_penalty="
        f"{diagnostic.cost.color_penalty:.6f}, "
        "affected_area_ratio="
        f"{metrics.affected_area_ratio:.6f}, "
        "source_shared_border_ratio="
        f"{metrics.source_shared_border_ratio:.6f}"
    )


def detail_preview_output_path(
    *,
    output_directory: Path,
    case: str,
    result: ComplexityReductionResult | None,
    strength: float,
) -> Path:
    """
    Return a deterministic output path for a detail-preservation preview.
    """
    if result is None:
        return output_directory / ("region-detail-preservation-" f"{case}-baseline.bmp")

    strength_token = f"{strength:.3f}".replace(
        ".",
        "p",
    )

    cost_token = f"{result.maximum_merge_cost:.3f}".replace(
        ".",
        "p",
    )

    return output_directory / (
        "region-detail-preservation-"
        f"{case}-"
        f"strength-{strength_token}-"
        f"max-{result.max_regions}-"
        f"cost-{cost_token}.bmp"
    )


def build_parser() -> ArgumentParser:
    """
    Build the detail-preservation evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate an experimental local " "detail-preservation merge-cost signal."
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
        "--strengths",
        nargs="+",
        type=float,
        required=True,
        help=("Experimental detail-preservation strengths " "between zero and one."),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help=(
            "Number of lowest adjusted-cost initial candidates "
            "to print for each strength."
        ),
    )

    parser.add_argument(
        "--target-fraction",
        type=float,
        default=DEFAULT_TARGET_FRACTION,
        help=(
            "Fraction of the mandatory-merge region count "
            "used to derive the reducer max_regions target."
        ),
    )

    parser.add_argument(
        "--maximum-merge-costs",
        nargs="+",
        type=float,
        default=DEFAULT_MAXIMUM_MERGE_COSTS,
        help=(
            "Adjusted merge-cost boundaries used for full "
            "experimental reducer evaluation."
        ),
    )

    parser.add_argument(
        "--accepted-merge-diagnostics",
        action="store_true",
        help=(
            "Print the actual accepted merge sequence "
            "for each full reducer execution."
        ),
    )

    parser.add_argument(
        "--write-previews",
        action="store_true",
        help=(
            "Write palette-colored BMP previews for the baseline "
            "and every experimental reduction."
        ),
    )

    parser.add_argument(
        "--preview-output-directory",
        type=Path,
        default=PREVIEW_OUTPUT_DIRECTORY,
        help=("Directory used for optional detail-preservation " "preview images."),
    )

    return parser


def _validate_arguments(
    parser: ArgumentParser,
    args: Namespace,
) -> None:
    """
    Validate developer-tool arguments.
    """
    limit = args.limit
    target_fraction = args.target_fraction
    strengths = args.strengths
    maximum_merge_costs = args.maximum_merge_costs

    if limit <= 0:
        parser.error(
            "--limit must be greater than zero",
        )

    if not 0.0 < target_fraction <= 1.0:
        parser.error(
            "--target-fraction must be greater than zero " "and at most one",
        )

    if any(not 0.0 <= strength <= 1.0 for strength in strengths):
        parser.error(
            "--strengths values must be between zero and one",
        )

    if any(
        not 0.0 <= maximum_merge_cost <= 1.0
        for maximum_merge_cost in maximum_merge_costs
    ):
        parser.error(
            "--maximum-merge-costs values must be " "between zero and one",
        )


def main() -> None:
    """
    Evaluate detail preservation through ranking and full reduction.
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
            f"strengths={tuple(args.strengths)}, "
            f"target_fraction={args.target_fraction}, "
            "maximum_merge_costs="
            f"{tuple(args.maximum_merge_costs)}"
        ),
    )

    for case in args.cases:
        prepared = prepare_case(
            case=case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

        diagnostics = build_candidate_diagnostics(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=RegionMergeCostCalculator(
                **profile_merge_cost_weights(
                    config,
                ),
            ),
        )

        print(
            (
                f"{case}: "
                f"baseline_regions={len(prepared.regions)}, "
                f"initial_candidates={len(diagnostics)}"
            ),
        )

        if args.write_previews:
            baseline_path = detail_preview_output_path(
                output_directory=args.preview_output_directory,
                case=case,
                result=None,
                strength=args.strengths[0],
            )

            write_region_preview(
                output_path=baseline_path,
                regions=prepared.regions,
                image_size=prepared.image_size,
            )

            print(
                f"  baseline_preview={baseline_path}",
            )

        for strength in args.strengths:
            evaluations = evaluate_detail_preservation(
                diagnostics=diagnostics,
                strength=strength,
            )

            print(
                f" strength={strength:.3f}",
            )

            for rank, evaluation in enumerate(
                evaluations[: args.limit],
                start=1,
            ):
                print(
                    format_evaluation(
                        evaluation,
                        rank=rank,
                    ),
                )

            calculator = DetailPreservingRegionMergeCostCalculator(
                strength=strength,
                **profile_merge_cost_weights(
                    config,
                ),
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

                if args.accepted_merge_diagnostics:
                    accepted_diagnostics = build_accepted_merge_diagnostics(
                        regions=prepared.regions,
                        merge_steps=execution.merge_steps,
                    )

                    print(
                        (
                            "    accepted_merge_diagnostics="
                            f"{len(accepted_diagnostics)}"
                        ),
                    )

                    for (
                        step_number,
                        accepted_diagnostic,
                    ) in enumerate(
                        accepted_diagnostics,
                        start=1,
                    ):
                        print(
                            format_accepted_merge_diagnostic(
                                accepted_diagnostic,
                                step_number=step_number,
                            ),
                        )

                if not args.write_previews:
                    continue

                output_path = detail_preview_output_path(
                    output_directory=(args.preview_output_directory),
                    case=case,
                    result=execution.result,
                    strength=strength,
                )

                write_region_preview(
                    output_path=output_path,
                    regions=execution.regions,
                    image_size=prepared.image_size,
                )

                print(
                    f"    preview={output_path}",
                )


if __name__ == "__main__":
    main()
