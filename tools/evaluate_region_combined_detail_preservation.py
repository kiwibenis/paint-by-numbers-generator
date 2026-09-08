# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate combined enclosure and compactness detail preservation.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, replace
from pathlib import Path

from pbn.application import GeneratorConfigValidator
from pbn.application.generator_config_resolver import (
    GeneratorConfigResolver,
)
from pbn.color.color_distance import ColorDistance
from pbn.config import GeneratorConfig
from pbn.exceptions import ConfigurationError
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    ImageSize,
    Palette,
    RegionMergeCost,
    RegionMergeMetrics,
)
from pbn.pipeline.region_generator import RegionGenerator
from pbn.regions.merge_cost_calculator import (
    RegionMergeCostCalculator,
)
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    PREVIEW_OUTPUT_DIRECTORY,
    REPOSITORY_ROOT,
    ComplexityReductionResult,
    PreparedCase,
    format_result,
    palette_path,
    prepare_case,
    resolve_color_distance,
    write_region_preview,
)
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)
from tools.evaluate_region_detail_preservation import (
    adjusted_detail_preservation_cost,
    build_accepted_merge_diagnostics,
    detail_preservation_penalty_from_components,
    execute_detail_reduction,
    format_accepted_merge_diagnostic,
)


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    """
    One built-in or explicitly supplied evaluation input.
    """

    case: str
    image_path: Path | None = None


@dataclass(frozen=True, slots=True)
class BaseWeightSet:
    """
    One experimental base merge-cost weighting.
    """

    color_weight: float
    affected_area_weight: float
    border_weight: float
    geometry_weight: float

    @property
    def values(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Return weights in merge-cost component order.
        """
        return (
            self.color_weight,
            self.affected_area_weight,
            self.border_weight,
            self.geometry_weight,
        )

    @property
    def token(
        self,
    ) -> str:
        """
        Return a deterministic file-name token.
        """
        return "-".join(
            _number_token(
                value,
            )
            for value in self.values
        )

    def build_calculator(
        self,
    ) -> RegionMergeCostCalculator:
        """
        Build and validate a base merge-cost calculator.
        """
        return RegionMergeCostCalculator(
            color_weight=self.color_weight,
            affected_area_weight=self.affected_area_weight,
            border_weight=self.border_weight,
            geometry_weight=self.geometry_weight,
        )


DEFAULT_BASE_WEIGHT_SET = BaseWeightSet(
    color_weight=0.40,
    affected_area_weight=0.25,
    border_weight=0.15,
    geometry_weight=0.20,
)
"""
The weights the shipped profiles configure.

These were 0.40, 0.20, 0.20, 0.20 while `config/example.toml` and
`config/untrusted.toml` configured 0.40, 0.25, 0.15, 0.20, and the
constant is what the help text calls the production weights. The
recorded cross-image calibration of `maximum_merge_cost` was therefore
produced against a weighting the project does not ship.
"""


class CombinedDetailPreservingRegionMergeCostCalculator(
    RegionMergeCostCalculator,
):
    """
    Apply enclosure protection followed by compactness protection.

    The base weighting is supplied as one `BaseWeightSet` rather than as a
    calculator plus a separate set of weights, so the inherited weights and
    the weights the base cost is computed from cannot disagree.
    """

    def __init__(
        self,
        *,
        enclosure_strength: float,
        compactness_strength: float,
        base_weights: BaseWeightSet,
    ) -> None:
        super().__init__(
            color_weight=base_weights.color_weight,
            affected_area_weight=base_weights.affected_area_weight,
            border_weight=base_weights.border_weight,
            geometry_weight=base_weights.geometry_weight,
        )

        _validate_strength(
            enclosure_strength,
        )
        _validate_strength(
            compactness_strength,
        )

        self._enclosure_strength = enclosure_strength
        self._compactness_strength = compactness_strength

        self.base_calculator = base_weights.build_calculator()

    def calculate(
        self,
        metrics: RegionMergeMetrics,
    ) -> RegionMergeCost:
        """
        Calculate sequential enclosure and compactness protection.
        """
        base_cost = self.base_calculator.calculate(
            metrics,
        )

        enclosure_penalty = detail_preservation_penalty_from_components(
            source_shared_border_ratio=(metrics.source_shared_border_ratio),
            color_penalty=base_cost.color_penalty,
            affected_area_ratio=(metrics.affected_area_ratio),
        )

        enclosure_adjusted_cost = adjusted_detail_preservation_cost(
            base_cost=base_cost.value,
            protection_penalty=enclosure_penalty,
            strength=self._enclosure_strength,
        )

        compactness_penalty = compactness_detail_preservation_penalty(
            metrics=metrics,
            color_penalty=base_cost.color_penalty,
        )

        adjusted_cost = adjusted_detail_preservation_cost(
            base_cost=enclosure_adjusted_cost,
            protection_penalty=compactness_penalty,
            strength=self._compactness_strength,
        )

        return RegionMergeCost(
            color_penalty=base_cost.color_penalty,
            affected_area_penalty=(base_cost.affected_area_penalty),
            border_penalty=base_cost.border_penalty,
            geometry_penalty=base_cost.geometry_penalty,
            value=adjusted_cost,
        )


def _validate_strength(
    strength: float,
) -> None:
    """
    Validate one experimental protection strength.
    """
    if not 0.0 <= strength <= 1.0:
        raise ValueError(
            "strength must be between zero and one",
        )


def compactness_detail_preservation_penalty(
    *,
    metrics: RegionMergeMetrics,
    color_penalty: float,
) -> float:
    """
    Calculate compactness-based protection for a source region.
    """
    return (
        metrics.source_non_compactness
        * color_penalty
        * (1.0 - metrics.affected_area_ratio)
    )


def resolve_base_weight_sets(
    raw_weight_sets: list[list[float]] | None,
) -> tuple[BaseWeightSet, ...]:
    """
    Resolve requested base weightings and validate each calculator.
    """
    if raw_weight_sets is None:
        return (DEFAULT_BASE_WEIGHT_SET,)

    weight_sets = tuple(
        BaseWeightSet(
            color_weight=values[0],
            affected_area_weight=values[1],
            border_weight=values[2],
            geometry_weight=values[3],
        )
        for values in raw_weight_sets
    )

    for weight_set in weight_sets:
        weight_set.build_calculator()

    return weight_sets


def combined_preview_output_path(
    *,
    output_directory: Path,
    case: str,
    result: ComplexityReductionResult,
    enclosure_strength: float,
    compactness_strength: float,
    base_weights: BaseWeightSet = DEFAULT_BASE_WEIGHT_SET,
) -> Path:
    """
    Return a deterministic preview path for a combined experiment.
    """
    enclosure_token = _number_token(
        enclosure_strength,
    )
    compactness_token = _number_token(
        compactness_strength,
    )
    cost_token = _number_token(
        result.maximum_merge_cost,
    )

    weights_token = (
        ""
        if base_weights == DEFAULT_BASE_WEIGHT_SET
        else (f"weights-{base_weights.token}-")
    )

    return output_directory / (
        "region-combined-detail-"
        f"{case}-"
        f"{weights_token}"
        f"enclosure-{enclosure_token}-"
        f"compactness-{compactness_token}-"
        f"max-{result.max_regions}-"
        f"cost-{cost_token}.bmp"
    )


def _number_token(
    value: float,
) -> str:
    """
    Format a normalized number for deterministic file names.
    """
    return f"{value:.3f}".replace(
        ".",
        "p",
    )


def resolve_evaluation_inputs(
    *,
    cases: tuple[str, ...] | None,
    input_images: tuple[Path, ...],
) -> tuple[EvaluationInput, ...]:
    """
    Resolve built-in and explicitly supplied evaluation inputs.
    """
    selected_cases = (
        EVALUATION_CASES if cases is None and not input_images else cases or ()
    )

    evaluation_inputs = tuple(
        EvaluationInput(
            case=case,
        )
        for case in selected_cases
    ) + tuple(
        EvaluationInput(
            case=image_path.stem,
            image_path=image_path,
        )
        for image_path in input_images
    )

    seen_cases: set[str] = set()

    for evaluation_input in evaluation_inputs:
        if evaluation_input.case in seen_cases:
            raise ValueError(
                "Duplicate evaluation case name: " f"{evaluation_input.case}",
            )

        seen_cases.add(
            evaluation_input.case,
        )

    return evaluation_inputs


def _validate_evaluation_inputs(
    parser: ArgumentParser,
    evaluation_inputs: tuple[EvaluationInput, ...],
) -> None:
    """
    Validate resolved evaluation inputs.
    """
    if not evaluation_inputs:
        parser.error(
            "At least one evaluation input must be supplied.",
        )

    for evaluation_input in evaluation_inputs:
        image_path = evaluation_input.image_path

        if image_path is None:
            continue

        if not image_path.is_file():
            parser.error(
                f"Input image does not exist: {image_path}",
            )


def _prepare_evaluation_input(
    *,
    evaluation_input: EvaluationInput,
    config: GeneratorConfig,
    palette: Palette,
    color_distance: ColorDistance,
) -> PreparedCase:
    """
    Generate the mandatory baseline for one evaluation input.
    """
    if evaluation_input.image_path is None:
        return prepare_case(
            case=evaluation_input.case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

    image = load_image(
        evaluation_input.image_path,
        DEVELOPER_IMAGE_INPUT_LIMITS,
    )

    image_size = ImageSize(
        width=image.width,
        height=image.height,
    )

    minimum_circle_diameter_px = (
        GeneratorConfigResolver().calculate_minimum_circle_diameter(
            config=config,
            image_size=image_size,
        )
    )

    regions = RegionGenerator(
        color_distance=color_distance,
    ).generate(
        image=image,
        palette=palette,
        minimum_circle_diameter_px=(minimum_circle_diameter_px),
    )

    return PreparedCase(
        case=evaluation_input.case,
        image_size=image_size,
        minimum_circle_diameter_px=(minimum_circle_diameter_px),
        regions=regions,
    )


def build_parser() -> ArgumentParser:
    """
    Build the combined detail-preservation evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate combined enclosure and source-compactness "
            "protection for optional region reduction."
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
        default=None,
    )

    parser.add_argument(
        "--input-images",
        nargs="+",
        type=Path,
        default=(),
        help=(
            "Additional local image files to evaluate. "
            "When supplied without --cases, only these "
            "images are evaluated."
        ),
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
        default=None,
    )

    parser.add_argument(
        "--minimum-region-size-mm",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--base-weights",
        action="append",
        nargs=4,
        type=float,
        default=None,
        metavar="WEIGHT",
        help=(
            "Experimental base weights in color, affected-area, "
            "border and geometry order. Repeat to compare "
            "multiple weight sets. Uses production weights "
            "when omitted."
        ),
    )

    parser.add_argument(
        "--enclosure-strength",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--compactness-strengths",
        nargs="+",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--target-fraction",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--maximum-merge-costs",
        nargs="+",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--write-previews",
        action="store_true",
    )

    parser.add_argument(
        "--preview-output-directory",
        type=Path,
        default=PREVIEW_OUTPUT_DIRECTORY,
    )

    return parser


def _validate_arguments(
    parser: ArgumentParser,
    args: Namespace,
) -> None:
    """
    Validate developer-tool arguments.
    """
    if not 0.0 <= args.enclosure_strength <= 1.0:
        parser.error(
            "--enclosure-strength must be between zero and one",
        )

    if any(not 0.0 <= strength <= 1.0 for strength in args.compactness_strengths):
        parser.error(
            "--compactness-strengths values must be " "between zero and one",
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
    Evaluate the combined protection through the actual reducer.
    """
    parser = build_parser()
    args = parser.parse_args()

    _validate_arguments(
        parser,
        args,
    )

    try:
        evaluation_inputs = resolve_evaluation_inputs(
            cases=(tuple(args.cases) if args.cases is not None else None),
            input_images=tuple(
                args.input_images,
            ),
        )

        base_weight_sets = resolve_base_weight_sets(
            args.base_weights,
        )
    except ValueError as exc:
        parser.error(
            str(exc),
        )

    _validate_evaluation_inputs(
        parser,
        evaluation_inputs,
    )

    config = load_config(
        args.config,
    )

    evaluation_config = (
        replace(
            config,
            minimum_region_size_mm=args.minimum_region_size_mm,
        )
        if args.minimum_region_size_mm is not None
        else config
    )

    try:
        GeneratorConfigValidator().validate(
            evaluation_config,
        )
    except ConfigurationError as exc:
        parser.error(
            str(exc),
        )

    selected_palette = (
        args.palette if args.palette is not None else evaluation_config.palette
    )

    selected_palette_version = (
        args.palette_version
        if args.palette_version is not None
        else evaluation_config.palette_version
    )

    selected_color_distance = (
        args.color_distance
        if args.color_distance is not None
        else evaluation_config.color_distance
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
            "minimum_region_size_mm="
            f"{evaluation_config.minimum_region_size_mm:g}, "
            "base_weight_sets="
            f"{tuple(item.values for item in base_weight_sets)}, "
            f"enclosure_strength={args.enclosure_strength}, "
            "compactness_strengths="
            f"{tuple(args.compactness_strengths)}, "
            f"target_fraction={args.target_fraction}, "
            "maximum_merge_costs="
            f"{tuple(args.maximum_merge_costs)}, "
            "evaluation_cases="
            f"{tuple(item.case for item in evaluation_inputs)}"
        ),
    )

    for evaluation_input in evaluation_inputs:
        prepared = _prepare_evaluation_input(
            evaluation_input=evaluation_input,
            config=evaluation_config,
            palette=palette,
            color_distance=color_distance,
        )

        print(
            (f"{prepared.case}: " f"baseline_regions={len(prepared.regions)}"),
        )

        for base_weights in base_weight_sets:
            print(
                ("  base_weights=" f"{base_weights.values}"),
            )

            for compactness_strength in args.compactness_strengths:
                print(
                    ("    compactness_strength=" f"{compactness_strength:.3f}"),
                )

                calculator = CombinedDetailPreservingRegionMergeCostCalculator(
                    enclosure_strength=(args.enclosure_strength),
                    compactness_strength=(compactness_strength),
                    base_weights=base_weights,
                )

                for maximum_merge_cost in args.maximum_merge_costs:
                    execution = execute_detail_reduction(
                        case=prepared.case,
                        regions=prepared.regions,
                        color_distance=color_distance,
                        minimum_circle_diameter_px=(
                            prepared.minimum_circle_diameter_px
                        ),
                        target_fraction=args.target_fraction,
                        maximum_merge_cost=maximum_merge_cost,
                        cost_calculator=calculator,
                    )

                    print(
                        (
                            "      reduction="
                            f"{format_result(execution.result).strip()}"
                        ),
                    )

                    diagnostics = build_accepted_merge_diagnostics(
                        regions=prepared.regions,
                        merge_steps=execution.merge_steps,
                    )

                    for step_number, diagnostic in enumerate(
                        diagnostics,
                        start=1,
                    ):
                        print(
                            format_accepted_merge_diagnostic(
                                diagnostic,
                                step_number=step_number,
                            ),
                        )

                    if not args.write_previews:
                        continue

                    output_path = combined_preview_output_path(
                        output_directory=(args.preview_output_directory),
                        case=prepared.case,
                        result=execution.result,
                        enclosure_strength=(args.enclosure_strength),
                        compactness_strength=(compactness_strength),
                        base_weights=base_weights,
                    )

                    write_region_preview(
                        output_path=output_path,
                        regions=execution.regions,
                        image_size=prepared.image_size,
                    )

                    print(
                        f"        preview={output_path}",
                    )


if __name__ == "__main__":
    main()
