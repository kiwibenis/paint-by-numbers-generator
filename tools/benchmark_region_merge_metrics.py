# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate raw region merge metrics and experimental weighting strategies.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from statistics import mean

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
    RegionMergeMetrics,
)
from pbn.pipeline.region_generator import RegionGenerator
from pbn.regions import RegionMergeCandidateBuilder
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

EVALUATION_CASES = (
    "simple",
    "medium",
    "complex",
)

SUPPORTED_COLOR_DISTANCES = (
    "delta_e_76",
    "delta_e_2000",
)

LOW_COST_COHORT_FRACTION = 0.10
LOWEST_CANDIDATES_TO_DISPLAY = 5


@dataclass(frozen=True, slots=True)
class MetricDistribution:
    """
    Distribution summary for one raw or calculated metric.
    """

    name: str
    count: int
    minimum: float
    percentile_05: float
    percentile_25: float
    median: float
    percentile_75: float
    percentile_95: float
    maximum: float


@dataclass(frozen=True, slots=True)
class NormalizedMergeComponents:
    """
    Experimental dimensionless merge-cost components.
    """

    color_penalty: float
    affected_area_penalty: float
    border_penalty: float
    geometry_penalty: float


@dataclass(frozen=True, slots=True)
class WeightingStrategy:
    """
    Experimental weighting strategy used only for evaluation.
    """

    name: str
    color_scale: float
    color_weight: float
    affected_area_weight: float
    border_weight: float
    geometry_weight: float

    @property
    def total_weight(self) -> float:
        """
        Return the sum of all component weights.
        """
        return (
            self.color_weight
            + self.affected_area_weight
            + self.border_weight
            + self.geometry_weight
        )


@dataclass(frozen=True, slots=True)
class ScoredMergeCandidate:
    """
    Experimental score for one directed merge candidate.
    """

    candidate: RegionMergeCandidate
    metrics: RegionMergeMetrics
    components: NormalizedMergeComponents
    score: float


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    """
    Evaluation summary for one experimental weighting strategy.
    """

    strategy: WeightingStrategy
    cost_distribution: MetricDistribution
    low_cost_candidates: tuple[ScoredMergeCandidate, ...]
    mean_low_cost_color_difference: float
    mean_low_cost_affected_area_ratio: float
    mean_low_cost_source_shared_border_ratio: float
    mean_low_cost_geometry_penalty: float


@dataclass(frozen=True, slots=True)
class CaseEvaluation:
    """
    Merge-metric evaluation result for one representative image.
    """

    case: str
    region_count: int
    candidate_count: int
    distributions: tuple[MetricDistribution, ...]
    strategy_evaluations: tuple[StrategyEvaluation, ...]


WEIGHTING_STRATEGIES = (
    WeightingStrategy(
        name="balanced-c10",
        color_scale=10.0,
        color_weight=0.40,
        affected_area_weight=0.20,
        border_weight=0.20,
        geometry_weight=0.20,
    ),
    WeightingStrategy(
        name="balanced-c25",
        color_scale=25.0,
        color_weight=0.40,
        affected_area_weight=0.20,
        border_weight=0.20,
        geometry_weight=0.20,
    ),
    WeightingStrategy(
        name="color-focused-c10",
        color_scale=10.0,
        color_weight=0.60,
        affected_area_weight=0.15,
        border_weight=0.15,
        geometry_weight=0.10,
    ),
    WeightingStrategy(
        name="color-focused-c25",
        color_scale=25.0,
        color_weight=0.60,
        affected_area_weight=0.15,
        border_weight=0.15,
        geometry_weight=0.10,
    ),
    WeightingStrategy(
        name="geometry-focused-c10",
        color_scale=10.0,
        color_weight=0.40,
        affected_area_weight=0.15,
        border_weight=0.15,
        geometry_weight=0.30,
    ),
    WeightingStrategy(
        name="geometry-focused-c25",
        color_scale=25.0,
        color_weight=0.40,
        affected_area_weight=0.15,
        border_weight=0.15,
        geometry_weight=0.30,
    ),
)


def percentile(
    values: tuple[float, ...],
    fraction: float,
) -> float:
    """
    Return a linearly interpolated percentile.
    """
    if not values:
        raise ValueError(
            "values must not be empty",
        )

    if not 0.0 <= fraction <= 1.0:
        raise ValueError(
            "fraction must be between zero and one",
        )

    ordered = tuple(
        sorted(values),
    )

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * fraction

    lower_index = int(position)
    upper_index = min(
        lower_index + 1,
        len(ordered) - 1,
    )

    interpolation = position - lower_index

    return (
        ordered[lower_index]
        + (ordered[upper_index] - ordered[lower_index]) * interpolation
    )


def summarize_values(
    *,
    name: str,
    values: tuple[float, ...],
) -> MetricDistribution:
    """
    Summarize the scale and distribution of one metric.
    """
    if not values:
        raise ValueError(
            "values must not be empty",
        )

    return MetricDistribution(
        name=name,
        count=len(values),
        minimum=min(values),
        percentile_05=percentile(
            values,
            0.05,
        ),
        percentile_25=percentile(
            values,
            0.25,
        ),
        median=percentile(
            values,
            0.50,
        ),
        percentile_75=percentile(
            values,
            0.75,
        ),
        percentile_95=percentile(
            values,
            0.95,
        ),
        maximum=max(values),
    )


def summarize_merge_metrics(
    metrics: tuple[RegionMergeMetrics, ...],
) -> tuple[MetricDistribution, ...]:
    """
    Summarize all raw metrics relevant to merge-cost evaluation.
    """
    if not metrics:
        return ()

    return (
        summarize_values(
            name="color_difference",
            values=tuple(metric.color_difference for metric in metrics),
        ),
        summarize_values(
            name="source_area",
            values=tuple(float(metric.source_area) for metric in metrics),
        ),
        summarize_values(
            name="target_area",
            values=tuple(float(metric.target_area) for metric in metrics),
        ),
        summarize_values(
            name="merged_area",
            values=tuple(float(metric.merged_area) for metric in metrics),
        ),
        summarize_values(
            name="affected_area_ratio",
            values=tuple(metric.affected_area_ratio for metric in metrics),
        ),
        summarize_values(
            name="shared_border_length",
            values=tuple(float(metric.shared_border_length) for metric in metrics),
        ),
        summarize_values(
            name="source_shared_border_ratio",
            values=tuple(metric.source_shared_border_ratio for metric in metrics),
        ),
        summarize_values(
            name="target_shared_border_ratio",
            values=tuple(metric.target_shared_border_ratio for metric in metrics),
        ),
        summarize_values(
            name="source_geometry_complexity",
            values=tuple(metric.source_geometry_complexity for metric in metrics),
        ),
        summarize_values(
            name="target_geometry_complexity",
            values=tuple(metric.target_geometry_complexity for metric in metrics),
        ),
        summarize_values(
            name="merged_geometry_complexity",
            values=tuple(metric.merged_geometry_complexity for metric in metrics),
        ),
        summarize_values(
            name="geometry_change",
            values=tuple(metric.geometry_change for metric in metrics),
        ),
    )


def normalize_color_difference(
    color_difference: float,
    *,
    color_scale: float,
) -> float:
    """
    Normalize non-negative color difference to a value below one.
    """
    if color_difference < 0.0:
        raise ValueError(
            "color_difference must not be negative",
        )

    if color_scale <= 0.0:
        raise ValueError(
            "color_scale must be greater than zero",
        )

    return color_difference / (color_difference + color_scale)


def normalize_geometry_degradation(
    metrics: RegionMergeMetrics,
) -> float:
    """
    Normalize only positive target-geometry degradation.
    """
    positive_change = max(
        0.0,
        metrics.geometry_change,
    )

    if positive_change == 0.0:
        return 0.0

    return positive_change / (metrics.target_geometry_complexity + positive_change)


def normalize_merge_metrics(
    metrics: RegionMergeMetrics,
    *,
    color_scale: float,
) -> NormalizedMergeComponents:
    """
    Convert raw merge metrics into dimensionless evaluation components.
    """
    return NormalizedMergeComponents(
        color_penalty=normalize_color_difference(
            metrics.color_difference,
            color_scale=color_scale,
        ),
        affected_area_penalty=metrics.affected_area_ratio,
        border_penalty=(1.0 - metrics.source_shared_border_ratio),
        geometry_penalty=normalize_geometry_degradation(
            metrics,
        ),
    )


def score_components(
    components: NormalizedMergeComponents,
    *,
    strategy: WeightingStrategy,
) -> float:
    """
    Combine normalized components using an experimental strategy.
    """
    if strategy.total_weight <= 0.0:
        raise ValueError(
            "strategy total weight must be greater than zero",
        )

    weighted_sum = (
        components.color_penalty * strategy.color_weight
        + components.affected_area_penalty * strategy.affected_area_weight
        + components.border_penalty * strategy.border_weight
        + components.geometry_penalty * strategy.geometry_weight
    )

    return weighted_sum / strategy.total_weight


def score_candidate(
    candidate: RegionMergeCandidate,
    metrics: RegionMergeMetrics,
    *,
    strategy: WeightingStrategy,
) -> ScoredMergeCandidate:
    """
    Score one directed merge candidate for evaluation.
    """
    components = normalize_merge_metrics(
        metrics,
        color_scale=strategy.color_scale,
    )

    return ScoredMergeCandidate(
        candidate=candidate,
        metrics=metrics,
        components=components,
        score=score_components(
            components,
            strategy=strategy,
        ),
    )


def evaluate_weighting_strategy(
    evaluations: tuple[
        tuple[
            RegionMergeCandidate,
            RegionMergeMetrics,
        ],
        ...,
    ],
    *,
    strategy: WeightingStrategy,
) -> StrategyEvaluation:
    """
    Evaluate one weighting strategy across directed candidates.
    """
    if not evaluations:
        raise ValueError(
            "evaluations must not be empty",
        )

    scored_candidates = tuple(
        sorted(
            (
                score_candidate(
                    candidate,
                    metrics,
                    strategy=strategy,
                )
                for candidate, metrics in evaluations
            ),
            key=lambda scored: (
                scored.score,
                scored.candidate.source_id,
                scored.candidate.target_id,
            ),
        ),
    )

    cohort_count = max(
        1,
        ceil(len(scored_candidates) * LOW_COST_COHORT_FRACTION),
    )

    low_cost_candidates = scored_candidates[:cohort_count]

    return StrategyEvaluation(
        strategy=strategy,
        cost_distribution=summarize_values(
            name="cost",
            values=tuple(scored.score for scored in scored_candidates),
        ),
        low_cost_candidates=low_cost_candidates,
        mean_low_cost_color_difference=mean(
            scored.metrics.color_difference for scored in low_cost_candidates
        ),
        mean_low_cost_affected_area_ratio=mean(
            scored.metrics.affected_area_ratio for scored in low_cost_candidates
        ),
        mean_low_cost_source_shared_border_ratio=mean(
            scored.metrics.source_shared_border_ratio for scored in low_cost_candidates
        ),
        mean_low_cost_geometry_penalty=mean(
            scored.components.geometry_penalty for scored in low_cost_candidates
        ),
    )


def evaluate_weighting_strategies(
    evaluations: tuple[
        tuple[
            RegionMergeCandidate,
            RegionMergeMetrics,
        ],
        ...,
    ],
) -> tuple[StrategyEvaluation, ...]:
    """
    Evaluate all configured experimental weighting strategies.
    """
    if not evaluations:
        return ()

    return tuple(
        evaluate_weighting_strategy(
            evaluations,
            strategy=strategy,
        )
        for strategy in WEIGHTING_STRATEGIES
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


def evaluate_regions(
    *,
    case: str,
    regions: tuple[Region, ...],
    color_distance: ColorDistance,
) -> CaseEvaluation:
    """
    Evaluate initial directed merge candidates for merged regions.
    """
    evaluations = RegionMergeCandidateBuilder(
        color_distance=color_distance,
    ).build(
        regions,
    )

    metrics = tuple(metric for _, metric in evaluations)

    return CaseEvaluation(
        case=case,
        region_count=len(regions),
        candidate_count=len(evaluations),
        distributions=summarize_merge_metrics(
            metrics,
        ),
        strategy_evaluations=evaluate_weighting_strategies(
            evaluations,
        ),
    )


def evaluate_case(
    *,
    case: str,
    config: GeneratorConfig,
    palette: Palette,
    color_distance: ColorDistance,
) -> CaseEvaluation:
    """
    Evaluate one representative image after mandatory region merging.
    """
    image_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"

    image = load_image(
        image_path,
        DEVELOPER_IMAGE_INPUT_LIMITS,
    )

    minimum_circle_diameter_px = (
        GeneratorConfigResolver().calculate_minimum_circle_diameter(
            config=config,
            image_size=ImageSize(
                width=image.width,
                height=image.height,
            ),
        )
    )

    regions = RegionGenerator(
        color_distance=color_distance,
    ).generate(
        image=image,
        palette=palette,
        minimum_circle_diameter_px=minimum_circle_diameter_px,
    )

    return evaluate_regions(
        case=case,
        regions=regions,
        color_distance=color_distance,
    )


def format_distribution(
    distribution: MetricDistribution,
) -> str:
    """
    Format one metric distribution for console output.
    """
    return (
        f"{distribution.name}: "
        f"count={distribution.count}, "
        f"min={distribution.minimum:.6f}, "
        f"p05={distribution.percentile_05:.6f}, "
        f"p25={distribution.percentile_25:.6f}, "
        f"median={distribution.median:.6f}, "
        f"p75={distribution.percentile_75:.6f}, "
        f"p95={distribution.percentile_95:.6f}, "
        f"max={distribution.maximum:.6f}"
    )


def format_strategy_evaluation(
    evaluation: StrategyEvaluation,
) -> str:
    """
    Format one weighting-strategy evaluation.
    """
    strategy = evaluation.strategy

    lines = [
        (
            f"  {strategy.name}: "
            f"color_scale={strategy.color_scale:.3f}, "
            "weights=("
            f"color={strategy.color_weight:.3f}, "
            f"affected={strategy.affected_area_weight:.3f}, "
            f"border={strategy.border_weight:.3f}, "
            f"geometry={strategy.geometry_weight:.3f}"
            ")"
        ),
        (
            "    "
            + format_distribution(
                evaluation.cost_distribution,
            )
        ),
        (
            "    lowest_10pct: "
            f"count={len(evaluation.low_cost_candidates)}, "
            "mean_color_difference="
            f"{evaluation.mean_low_cost_color_difference:.6f}, "
            "mean_affected_area_ratio="
            f"{evaluation.mean_low_cost_affected_area_ratio:.6f}, "
            "mean_source_shared_border_ratio="
            f"{evaluation.mean_low_cost_source_shared_border_ratio:.6f}, "
            "mean_geometry_penalty="
            f"{evaluation.mean_low_cost_geometry_penalty:.6f}"
        ),
    ]

    lowest_candidates = evaluation.low_cost_candidates[:LOWEST_CANDIDATES_TO_DISPLAY]

    lines.append(
        "    cheapest_candidates="
        + ", ".join(
            (
                f"{scored.candidate.source_id}"
                f"->{scored.candidate.target_id}"
                f":{scored.score:.6f}"
            )
            for scored in lowest_candidates
        ),
    )

    return "\n".join(
        lines,
    )


def format_case(
    evaluation: CaseEvaluation,
) -> str:
    """
    Format one representative-image evaluation.
    """
    lines = [
        (
            f"{evaluation.case}: "
            f"regions={evaluation.region_count}, "
            f"directed_candidates={evaluation.candidate_count}"
        ),
    ]

    lines.extend(
        f"  {format_distribution(distribution)}"
        for distribution in evaluation.distributions
    )

    if evaluation.strategy_evaluations:
        lines.append(
            "  weighting_strategies:",
        )

        lines.extend(
            format_strategy_evaluation(
                strategy_evaluation,
            )
            for strategy_evaluation in evaluation.strategy_evaluations
        )

    return "\n".join(
        lines,
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
    Build the merge-metric evaluation command-line parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate raw directed region merge metrics "
            "and experimental weighting strategies."
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

    return parser


def main() -> None:
    """
    Evaluate merge metrics for representative images.
    """
    args = build_parser().parse_args()

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
            f"minimum_region_size_mm="
            f"{config.minimum_region_size_mm}"
        ),
    )

    for case in args.cases:
        evaluation = evaluate_case(
            case=case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

        print(
            format_case(
                evaluation,
            ),
        )


if __name__ == "__main__":
    main()
