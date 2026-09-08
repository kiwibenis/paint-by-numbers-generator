# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate source-region compactness for region-complexity candidates.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    CandidateDiagnostic,
    build_candidate_diagnostics,
    format_result,
    palette_path,
    prepare_case,
    resolve_color_distance,
)
from tools.evaluate_region_detail_preservation import (
    DetailPreservationEvaluation,
    DetailPreservingRegionMergeCostCalculator,
    build_accepted_merge_diagnostics,
    evaluate_detail_preservation,
    execute_detail_reduction,
)
from tools.profile_merge_cost_weights import (
    profile_merge_cost_weights,
)


def format_initial_source_shape_evaluation(
    evaluation: DetailPreservationEvaluation,
    *,
    rank: int,
) -> str:
    """
    Format source geometry for one initially ranked candidate.
    """
    diagnostic = evaluation.diagnostic
    candidate = diagnostic.candidate
    metrics = diagnostic.metrics

    return (
        f"    rank={rank}, "
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
        f"source_area={metrics.source_area}, "
        f"source_perimeter={metrics.source_perimeter}, "
        "source_geometry_complexity="
        f"{metrics.source_geometry_complexity:.6f}, "
        "source_compactness="
        f"{metrics.source_compactness:.6f}, "
        "source_non_compactness="
        f"{metrics.source_non_compactness:.6f}, "
        "source_shared_border_ratio="
        f"{metrics.source_shared_border_ratio:.6f}, "
        "color_difference="
        f"{metrics.color_difference:.6f}"
    )


def format_source_shape_diagnostic(
    diagnostic: CandidateDiagnostic,
    *,
    step_number: int,
) -> str:
    """
    Format source geometry for one actually accepted merge.
    """
    candidate = diagnostic.candidate
    metrics = diagnostic.metrics

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
        f"cost={diagnostic.cost.value:.6f}, "
        f"source_area={metrics.source_area}, "
        f"source_perimeter={metrics.source_perimeter}, "
        "source_geometry_complexity="
        f"{metrics.source_geometry_complexity:.6f}, "
        "source_compactness="
        f"{metrics.source_compactness:.6f}, "
        "source_non_compactness="
        f"{metrics.source_non_compactness:.6f}"
    )


def build_parser() -> ArgumentParser:
    """
    Build the source-compactness evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate source-region compactness for initial "
            "candidates and actual accepted complexity merges."
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

    parser.add_argument(
        "--initial-limit",
        type=int,
        default=20,
        help=(
            "Number of initially ranked candidates whose "
            "source compactness shall be printed."
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

    if args.initial_limit <= 0:
        parser.error(
            "--initial-limit must be greater than zero",
        )


def main() -> None:
    """
    Evaluate source geometry across initial and accepted candidates.
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
            f"{tuple(args.maximum_merge_costs)}, "
            f"initial_limit={args.initial_limit}"
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

        initial_diagnostics = build_candidate_diagnostics(
            regions=prepared.regions,
            color_distance=color_distance,
            cost_calculator=calculator,
        )

        initial_evaluations = evaluate_detail_preservation(
            diagnostics=initial_diagnostics,
            strength=args.strength,
        )

        print(
            (
                f"{case}: "
                f"baseline_regions={len(prepared.regions)}, "
                f"initial_candidates={len(initial_evaluations)}"
            ),
        )

        print(
            (
                "  initial_source_shape_diagnostics="
                f"{min(args.initial_limit, len(initial_evaluations))}"
            ),
        )

        for rank, evaluation in enumerate(
            initial_evaluations[: args.initial_limit],
            start=1,
        ):
            print(
                format_initial_source_shape_evaluation(
                    evaluation,
                    rank=rank,
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

            diagnostics = build_accepted_merge_diagnostics(
                regions=prepared.regions,
                merge_steps=execution.merge_steps,
            )

            print(
                ("    source_shape_diagnostics=" f"{len(diagnostics)}"),
            )

            for step_number, diagnostic in enumerate(
                diagnostics,
                start=1,
            ):
                print(
                    format_source_shape_diagnostic(
                        diagnostic,
                        step_number=step_number,
                    ),
                )


if __name__ == "__main__":
    main()
