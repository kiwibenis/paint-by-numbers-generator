# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate optional region complexity reduction across targets and cost limits.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from struct import pack
from time import perf_counter

from pbn.application.generator_config_resolver import (
    GeneratorConfigResolver,
)
from pbn.color import DeltaE76, DeltaE2000
from pbn.color.color_distance import ColorDistance
from pbn.config import GeneratorConfig
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    ImageSize,
    Palette,
    Region,
    RegionMergeCandidate,
    RegionMergeCost,
    RegionMergeMetrics,
)
from pbn.pipeline.region_generator import RegionGenerator
from pbn.regions.complexity_reducer import (
    RegionComplexityReducer,
)
from pbn.regions.merge_candidate_builder import (
    RegionMergeCandidateBuilder,
)
from pbn.regions.merge_cost_calculator import (
    RegionMergeCostCalculator,
)
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)
from tools.profile_merge_cost_weights import (
    profile_merge_cost_weights,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

PREVIEW_OUTPUT_DIRECTORY = REPOSITORY_ROOT / "tools" / "output" / "region-complexity"

EVALUATION_CASES = (
    "simple",
    "medium",
    "complex",
)

SUPPORTED_COLOR_DISTANCES = (
    "delta_e_76",
    "delta_e_2000",
)

WEIGHTING_STRATEGIES = (
    "production",
    "color_focused",
)

DEFAULT_TARGET_FRACTIONS = (
    0.75,
    0.50,
    0.25,
)

DEFAULT_MAXIMUM_MERGE_COSTS = (
    0.10,
    0.20,
    0.30,
    0.40,
    0.50,
)


@dataclass(frozen=True, slots=True)
class ComplexityReductionResult:
    """
    Result of one optional complexity-reduction evaluation.
    """

    case: str
    baseline_region_count: int
    target_fraction: float
    max_regions: int
    maximum_merge_cost: float
    final_region_count: int
    reduction_seconds: float

    @property
    def target_reached(self) -> bool:
        """
        Return whether the requested region target was reached.
        """
        return self.final_region_count <= self.max_regions

    @property
    def reduction_fraction(self) -> float:
        """
        Return the fraction of baseline regions removed.
        """
        return (
            self.baseline_region_count - self.final_region_count
        ) / self.baseline_region_count

    @property
    def stop_reason(self) -> str:
        """
        Return the observable reason category for stopping.
        """
        if self.target_reached:
            return "target_reached"

        return "quality_boundary_or_no_candidate"


@dataclass(frozen=True, slots=True)
class ComplexityReductionExecution:
    """
    One reduction result together with the resulting regions.
    """

    result: ComplexityReductionResult
    regions: tuple[Region, ...]


@dataclass(frozen=True, slots=True)
class PreparedCase:
    """
    Mandatory-merge output used as the baseline for one case.
    """

    case: str
    image_size: ImageSize
    minimum_circle_diameter_px: int
    regions: tuple[Region, ...]


@dataclass(frozen=True, slots=True)
class CaseComplexityEvaluation:
    """
    Complexity-reduction evaluation for one representative image.
    """

    case: str
    minimum_circle_diameter_px: int
    baseline_region_count: int
    results: tuple[
        ComplexityReductionResult,
        ...,
    ]


@dataclass(frozen=True, slots=True)
class CandidateDiagnostic:
    """
    Developer diagnostics for one initial directed merge candidate.
    """

    candidate: RegionMergeCandidate
    source_color_number: int
    source_color_name: str
    target_color_number: int
    target_color_name: str
    source_bounds: tuple[int, int, int, int]
    target_bounds: tuple[int, int, int, int]
    metrics: RegionMergeMetrics
    cost: RegionMergeCost


def resolve_max_regions(
    *,
    baseline_region_count: int,
    target_fraction: float,
) -> int:
    """
    Resolve a relative evaluation target into an absolute region count.
    """
    if baseline_region_count <= 0:
        raise ValueError(
            "baseline_region_count must be greater than zero",
        )

    if not 0.0 < target_fraction <= 1.0:
        raise ValueError(
            "target_fraction must be greater than zero " "and at most one",
        )

    return max(
        1,
        ceil(baseline_region_count * target_fraction),
    )


def resolve_merge_cost_calculator(
    weighting_strategy: str,
    config: GeneratorConfig,
) -> RegionMergeCostCalculator:
    """
    Resolve the merge-cost calculator for one weighting strategy.

    `production` used to resolve to `None`, which reached the Core class as
    its own weighting of `0.40 / 0.20 / 0.20 / 0.20` while every shipped
    profile says `0.40 / 0.25 / 0.15 / 0.20`. The strategy named after
    production measured a weighting the project does not ship.
    """
    if weighting_strategy == "production":
        return RegionMergeCostCalculator(
            **profile_merge_cost_weights(
                config,
            ),
        )

    if weighting_strategy == "color_focused":
        return RegionMergeCostCalculator(
            color_weight=0.60,
            affected_area_weight=0.15,
            border_weight=0.15,
            geometry_weight=0.10,
        )

    raise ValueError(
        "Unsupported weighting strategy: " f"{weighting_strategy}",
    )


def execute_reduction(
    *,
    case: str,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    minimum_circle_diameter_px: int,
    target_fraction: float,
    maximum_merge_cost: float,
    cost_calculator: RegionMergeCostCalculator,
) -> ComplexityReductionExecution:
    """
    Execute one reduction and retain its resulting regions.
    """
    if not 0.0 <= maximum_merge_cost <= 1.0:
        raise ValueError(
            "maximum_merge_cost must be between zero and one",
        )

    baseline_region_count = len(regions)

    max_regions = resolve_max_regions(
        baseline_region_count=baseline_region_count,
        target_fraction=target_fraction,
    )

    started_at = perf_counter()

    reduced_regions = RegionComplexityReducer(
        color_distance=color_distance,
        cost_calculator=cost_calculator,
    ).reduce(
        regions,
        minimum_circle_diameter_px=(minimum_circle_diameter_px),
        max_regions=max_regions,
        maximum_merge_cost=maximum_merge_cost,
    )

    finished_at = perf_counter()

    return ComplexityReductionExecution(
        result=ComplexityReductionResult(
            case=case,
            baseline_region_count=baseline_region_count,
            target_fraction=target_fraction,
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            final_region_count=len(reduced_regions),
            reduction_seconds=(finished_at - started_at),
        ),
        regions=reduced_regions,
    )


def evaluate_reduction(
    *,
    case: str,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    minimum_circle_diameter_px: int,
    target_fraction: float,
    maximum_merge_cost: float,
    cost_calculator: RegionMergeCostCalculator,
) -> ComplexityReductionResult:
    """
    Evaluate one region target and merge-cost boundary.
    """
    return execute_reduction(
        case=case,
        regions=regions,
        color_distance=color_distance,
        minimum_circle_diameter_px=(minimum_circle_diameter_px),
        target_fraction=target_fraction,
        maximum_merge_cost=maximum_merge_cost,
        cost_calculator=cost_calculator,
    ).result


def evaluate_matrix(
    *,
    case: str,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    minimum_circle_diameter_px: int,
    target_fractions: tuple[float, ...],
    maximum_merge_costs: tuple[float, ...],
    cost_calculator: RegionMergeCostCalculator,
) -> tuple[
    ComplexityReductionResult,
    ...,
]:
    """
    Evaluate every requested target and merge-cost combination.
    """
    if not target_fractions:
        raise ValueError(
            "target_fractions must not be empty",
        )

    if not maximum_merge_costs:
        raise ValueError(
            "maximum_merge_costs must not be empty",
        )

    return tuple(
        evaluate_reduction(
            case=case,
            regions=regions,
            color_distance=color_distance,
            minimum_circle_diameter_px=(minimum_circle_diameter_px),
            target_fraction=target_fraction,
            maximum_merge_cost=maximum_merge_cost,
            cost_calculator=cost_calculator,
        )
        for target_fraction in target_fractions
        for maximum_merge_cost in maximum_merge_costs
    )


def prepare_case(
    *,
    case: str,
    config: GeneratorConfig,
    palette: Palette,
    color_distance: ColorDistance,
) -> PreparedCase:
    """
    Generate the mandatory-merge baseline for one representative image.
    """
    image_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"

    image = load_image(
        image_path,
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
        case=case,
        image_size=image_size,
        minimum_circle_diameter_px=(minimum_circle_diameter_px),
        regions=regions,
    )


def evaluate_prepared_case(
    *,
    prepared: PreparedCase,
    color_distance: ColorDistance,
    target_fractions: tuple[float, ...],
    maximum_merge_costs: tuple[float, ...],
    cost_calculator: RegionMergeCostCalculator,
) -> CaseComplexityEvaluation:
    """
    Evaluate optional reduction for an already prepared baseline.
    """
    return CaseComplexityEvaluation(
        case=prepared.case,
        minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
        baseline_region_count=len(
            prepared.regions,
        ),
        results=evaluate_matrix(
            case=prepared.case,
            regions=prepared.regions,
            color_distance=color_distance,
            minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
            target_fractions=target_fractions,
            maximum_merge_costs=maximum_merge_costs,
            cost_calculator=cost_calculator,
        ),
    )


def evaluate_case(
    *,
    case: str,
    config: GeneratorConfig,
    palette: Palette,
    color_distance: ColorDistance,
    target_fractions: tuple[float, ...],
    maximum_merge_costs: tuple[float, ...],
    cost_calculator: RegionMergeCostCalculator,
) -> CaseComplexityEvaluation:
    """
    Evaluate optional reduction after mandatory region merging.
    """
    prepared = prepare_case(
        case=case,
        config=config,
        palette=palette,
        color_distance=color_distance,
    )

    return evaluate_prepared_case(
        prepared=prepared,
        color_distance=color_distance,
        target_fractions=target_fractions,
        maximum_merge_costs=maximum_merge_costs,
        cost_calculator=cost_calculator,
    )


def build_candidate_diagnostics(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
) -> tuple[CandidateDiagnostic, ...]:
    """
    Build deterministic diagnostics for all initial merge candidates.
    """
    calculator = cost_calculator

    regions_by_id = {region.id: region for region in regions}

    raw_evaluations = RegionMergeCandidateBuilder(
        color_distance=color_distance,
    ).build(
        regions,
    )

    diagnostics = tuple(
        CandidateDiagnostic(
            candidate=candidate,
            source_color_number=(regions_by_id[candidate.source_id].color.number),
            source_color_name=(regions_by_id[candidate.source_id].color.name),
            target_color_number=(regions_by_id[candidate.target_id].color.number),
            target_color_name=(regions_by_id[candidate.target_id].color.name),
            source_bounds=_region_bounds(
                regions_by_id[candidate.source_id],
            ),
            target_bounds=_region_bounds(
                regions_by_id[candidate.target_id],
            ),
            metrics=metrics,
            cost=calculator.calculate(
                metrics,
            ),
        )
        for candidate, metrics in raw_evaluations
    )

    return tuple(
        sorted(
            diagnostics,
            key=lambda diagnostic: (
                diagnostic.cost.value,
                diagnostic.candidate.source_id,
                diagnostic.candidate.target_id,
            ),
        ),
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


def format_candidate_diagnostic(
    diagnostic: CandidateDiagnostic,
    *,
    rank: int,
) -> str:
    """
    Format one initial merge candidate and all existing cost inputs.
    """
    metrics = diagnostic.metrics
    cost = diagnostic.cost

    return (
        f"  rank={rank}, "
        f"source_id={diagnostic.candidate.source_id}, "
        f"target_id={diagnostic.candidate.target_id}, "
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
        f"merged_area={metrics.merged_area}, "
        "affected_area_ratio="
        f"{metrics.affected_area_ratio:.6f}, "
        "shared_border_length="
        f"{metrics.shared_border_length}, "
        "source_perimeter="
        f"{metrics.source_perimeter}, "
        "target_perimeter="
        f"{metrics.target_perimeter}, "
        "merged_perimeter="
        f"{metrics.merged_perimeter}, "
        "source_shared_border_ratio="
        f"{metrics.source_shared_border_ratio:.6f}, "
        "target_shared_border_ratio="
        f"{metrics.target_shared_border_ratio:.6f}, "
        "source_geometry_complexity="
        f"{metrics.source_geometry_complexity:.6f}, "
        "target_geometry_complexity="
        f"{metrics.target_geometry_complexity:.6f}, "
        "merged_geometry_complexity="
        f"{metrics.merged_geometry_complexity:.6f}, "
        f"geometry_change={metrics.geometry_change:.6f}, "
        f"color_penalty={cost.color_penalty:.6f}, "
        "affected_area_penalty="
        f"{cost.affected_area_penalty:.6f}, "
        f"border_penalty={cost.border_penalty:.6f}, "
        f"geometry_penalty={cost.geometry_penalty:.6f}"
    )


def print_candidate_diagnostics(
    *,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
    cost_calculator: RegionMergeCostCalculator,
    limit: int,
) -> None:
    """
    Print the lowest-cost initial merge candidates.
    """
    diagnostics = build_candidate_diagnostics(
        regions=regions,
        color_distance=color_distance,
        cost_calculator=cost_calculator,
    )

    selected = diagnostics[:limit]

    print(
        ("  initial_candidate_diagnostics=" f"{len(selected)}/{len(diagnostics)}"),
    )

    for rank, diagnostic in enumerate(
        selected,
        start=1,
    ):
        print(
            format_candidate_diagnostic(
                diagnostic,
                rank=rank,
            ),
        )


def build_region_preview_bmp(
    *,
    regions: tuple[Region, ...],
    image_size: ImageSize,
) -> bytes:
    """
    Render region palette colors into an uncompressed 24-bit BMP.
    """
    width = image_size.width
    height = image_size.height

    bytes_per_pixel = 3
    unpadded_row_size = width * bytes_per_pixel
    row_size = (unpadded_row_size + 3) & ~3

    pixel_data_size = row_size * height

    pixel_data = bytearray(
        pixel_data_size,
    )

    for region in regions:
        color = region.color.rgb

        for x, y in region.coordinates():
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError(
                    "Region pixel is outside the preview image.",
                )

            offset = y * row_size + x * bytes_per_pixel

            pixel_data[offset] = color.blue
            pixel_data[offset + 1] = color.green
            pixel_data[offset + 2] = color.red

    pixel_offset = 54

    file_size = pixel_offset + pixel_data_size

    file_header = b"BM" + pack(
        "<IHHI",
        file_size,
        0,
        0,
        pixel_offset,
    )

    information_header = pack(
        "<IiiHHIIiiII",
        40,
        width,
        -height,
        1,
        24,
        0,
        pixel_data_size,
        2835,
        2835,
        0,
        0,
    )

    return file_header + information_header + bytes(pixel_data)


def preview_output_path(
    *,
    output_directory: Path,
    case: str,
    result: ComplexityReductionResult | None,
    weighting_strategy: str = "production",
) -> Path:
    """
    Return the deterministic output path for one region preview.
    """
    if weighting_strategy not in WEIGHTING_STRATEGIES:
        raise ValueError(
            "Unsupported weighting strategy: " f"{weighting_strategy}",
        )

    if result is None:
        return output_directory / ("region-complexity-" f"{case}-baseline.bmp")

    cost_token = f"{result.maximum_merge_cost:.3f}".replace(
        ".",
        "p",
    )

    weighting_suffix = ""

    if weighting_strategy != "production":
        weighting_token = weighting_strategy.replace(
            "_",
            "-",
        )
        weighting_suffix = "-weights-" f"{weighting_token}"

    return output_directory / (
        "region-complexity-"
        f"{case}-"
        f"max-{result.max_regions}-"
        f"cost-{cost_token}"
        f"{weighting_suffix}.bmp"
    )


def write_region_preview(
    *,
    output_path: Path,
    regions: tuple[Region, ...],
    image_size: ImageSize,
) -> None:
    """
    Write one deterministic region-color preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_region_preview_bmp(
            regions=regions,
            image_size=image_size,
        ),
    )


def format_result(
    result: ComplexityReductionResult,
) -> str:
    """
    Format one complexity-reduction result.
    """
    return (
        f"  target_fraction={result.target_fraction:.3f}, "
        f"max_regions={result.max_regions}, "
        "maximum_merge_cost="
        f"{result.maximum_merge_cost:.3f}, "
        f"final_regions={result.final_region_count}, "
        "reduction="
        f"{result.reduction_fraction:.2%}, "
        f"stop={result.stop_reason}, "
        f"reducer={result.reduction_seconds:.3f}s"
    )


def format_case(
    evaluation: CaseComplexityEvaluation,
) -> str:
    """
    Format one representative-image complexity evaluation.
    """
    lines = [
        (
            f"{evaluation.case}: "
            f"baseline_regions="
            f"{evaluation.baseline_region_count}, "
            "minimum_circle_diameter_px="
            f"{evaluation.minimum_circle_diameter_px}"
        ),
    ]

    lines.extend(format_result(result) for result in evaluation.results)

    return "\n".join(
        lines,
    )


def resolve_color_distance(
    name: str,
) -> ColorDistance:
    """
    Resolve the configured color-distance implementation.
    """
    if name == "delta_e_76":
        return DeltaE76()

    if name == "delta_e_2000":
        return DeltaE2000()

    raise ValueError(
        f"Unsupported color distance: {name}",
    )


def palette_path(
    *,
    palette_id: str,
    palette_version: int,
) -> Path:
    """
    Return the repository path for a versioned palette.
    """
    return REPOSITORY_ROOT / "palettes" / f"{palette_id}-v{palette_version}.json"


def build_parser() -> ArgumentParser:
    """
    Build the region-complexity evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate optional region complexity reduction "
            "across region targets and merge-cost limits."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
        help=(
            "Generation configuration used for physical "
            "minimum-region-size semantics."
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
        choices=SUPPORTED_COLOR_DISTANCES,
        default=None,
        help=("Color-distance override. " "Uses the configuration value when omitted."),
    )

    parser.add_argument(
        "--weighting-strategy",
        choices=WEIGHTING_STRATEGIES,
        default="production",
        help=("Merge-cost weighting strategy used for " "developer evaluation."),
    )

    parser.add_argument(
        "--target-fractions",
        nargs="+",
        type=float,
        default=DEFAULT_TARGET_FRACTIONS,
        help=(
            "Fractions of the mandatory-merge region count "
            "used to derive max_regions targets."
        ),
    )

    parser.add_argument(
        "--maximum-merge-costs",
        nargs="+",
        type=float,
        default=DEFAULT_MAXIMUM_MERGE_COSTS,
        help=("Merge-cost boundaries to evaluate."),
    )

    parser.add_argument(
        "--candidate-diagnostics-limit",
        type=int,
        default=0,
        help=(
            "Print this many lowest-cost initial directed "
            "merge candidates with raw metrics. "
            "Zero disables diagnostics."
        ),
    )

    parser.add_argument(
        "--write-previews",
        action="store_true",
        help=(
            "Write palette-colored BMP previews for the "
            "mandatory baseline and every evaluated result."
        ),
    )

    parser.add_argument(
        "--preview-output-directory",
        type=Path,
        default=PREVIEW_OUTPUT_DIRECTORY,
        help=("Directory used for optional region-color " "preview images."),
    )

    return parser


def _print_case_with_previews(
    *,
    prepared: PreparedCase,
    color_distance: ColorDistance,
    target_fractions: tuple[float, ...],
    maximum_merge_costs: tuple[float, ...],
    output_directory: Path,
    weighting_strategy: str,
    cost_calculator: RegionMergeCostCalculator,
) -> None:
    """
    Evaluate one case while writing region-color previews.
    """
    print(
        (
            f"{prepared.case}: "
            f"baseline_regions={len(prepared.regions)}, "
            "minimum_circle_diameter_px="
            f"{prepared.minimum_circle_diameter_px}"
        ),
    )

    baseline_path = preview_output_path(
        output_directory=output_directory,
        case=prepared.case,
        result=None,
        weighting_strategy=weighting_strategy,
    )

    write_region_preview(
        output_path=baseline_path,
        regions=prepared.regions,
        image_size=prepared.image_size,
    )

    print(
        f"  baseline_preview={baseline_path}",
    )

    for target_fraction in target_fractions:
        for maximum_merge_cost in maximum_merge_costs:
            execution = execute_reduction(
                case=prepared.case,
                regions=prepared.regions,
                color_distance=color_distance,
                minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
                target_fraction=target_fraction,
                maximum_merge_cost=maximum_merge_cost,
                cost_calculator=cost_calculator,
            )

            print(
                format_result(
                    execution.result,
                ),
            )

            output_path = preview_output_path(
                output_directory=output_directory,
                case=prepared.case,
                result=execution.result,
                weighting_strategy=weighting_strategy,
            )

            write_region_preview(
                output_path=output_path,
                regions=execution.regions,
                image_size=prepared.image_size,
            )

            print(
                f"    preview={output_path}",
            )


def main() -> None:
    """
    Evaluate region complexity reduction on representative images.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.candidate_diagnostics_limit < 0:
        parser.error(
            "--candidate-diagnostics-limit must be " "greater than or equal to zero",
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

    cost_calculator = resolve_merge_cost_calculator(
        args.weighting_strategy,
        config,
    )

    target_fractions = tuple(
        args.target_fractions,
    )
    maximum_merge_costs = tuple(
        args.maximum_merge_costs,
    )

    print(
        (
            f"palette={selected_palette}, "
            f"palette_version={selected_palette_version}, "
            f"color_distance={selected_color_distance}, "
            "weighting_strategy="
            f"{args.weighting_strategy}, "
            f"minimum_region_size_mm="
            f"{config.minimum_region_size_mm}, "
            "target_fractions="
            f"{target_fractions}, "
            "maximum_merge_costs="
            f"{maximum_merge_costs}"
        ),
    )

    for case in args.cases:
        prepared = prepare_case(
            case=case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

        if args.write_previews:
            _print_case_with_previews(
                prepared=prepared,
                color_distance=color_distance,
                target_fractions=target_fractions,
                maximum_merge_costs=maximum_merge_costs,
                output_directory=(args.preview_output_directory),
                weighting_strategy=args.weighting_strategy,
                cost_calculator=cost_calculator,
            )
        else:
            evaluation = evaluate_prepared_case(
                prepared=prepared,
                color_distance=color_distance,
                target_fractions=target_fractions,
                maximum_merge_costs=maximum_merge_costs,
                cost_calculator=cost_calculator,
            )

            print(
                format_case(
                    evaluation,
                ),
            )

        if args.candidate_diagnostics_limit > 0:
            print_candidate_diagnostics(
                regions=prepared.regions,
                color_distance=color_distance,
                cost_calculator=cost_calculator,
                limit=args.candidate_diagnostics_limit,
            )


if __name__ == "__main__":
    main()
