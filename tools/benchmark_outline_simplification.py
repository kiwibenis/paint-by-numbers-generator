# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Polygon outline simplification benchmarks.

Generation policy is taken from `config/example.toml` and is not restated
here. Only the palette and the simplification state under test are
overridden on the loaded profile, so a recalibrated profile is measured as
recalibrated rather than overridden by a stale copy of its values.

The palette is the deliberate divergence. The profile ships `reference8`,
which is too small for a representative outline set.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from time import perf_counter

from pbn.application.generator_application import GeneratorApplication
from pbn.config.models import GeneratorConfig
from pbn.core.image_input_rules import ImageInputLimits
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.overlap_detector_factory import (
    build_overlap_detector,
)
from pbn.infrastructure.palette_manager import PaletteManager
from pbn.models import InputImage, Palette
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_CASES = (
    "simple_smaller",
    "simple",
    "medium_smaller",
    "medium",
    "complex_smaller",
    "complex",
)

PALETTE_ID = "faberCastellPolychromos60"
PALETTE_VERSION = 1


def case_image_path(
    case: str,
) -> Path:
    return REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"


@dataclass(frozen=True, slots=True)
class PreloadedImageLoader:
    """
    Hands the generator an image that was decoded before measurement.

    The benchmark compares two configurations of one generation, and
    decoding the input is identical in both. Leaving it inside the
    measured region would add the same constant to each arm and shrink
    the reported difference, which is the only number this tool exists
    to produce.

    The limits argument is accepted and ignored. The image already
    passed `DEVELOPER_IMAGE_INPUT_LIMITS` in `load_case`, and a loader
    that reapplied limits it was handed would be validating a decode it
    did not perform.
    """

    image: InputImage

    def load(
        self,
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage:
        return self.image


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """
    Benchmark results for one outline simplification case.
    """

    case: str
    disabled_durations_seconds: tuple[float, ...]
    enabled_durations_seconds: tuple[float, ...]
    disabled_outline_points: int
    enabled_outline_points: int

    @property
    def median_disabled_seconds(self) -> float:
        """
        Return the median duration without outline simplification.
        """
        return median(
            self.disabled_durations_seconds,
        )

    @property
    def median_enabled_seconds(self) -> float:
        """
        Return the median duration with outline simplification.
        """
        return median(
            self.enabled_durations_seconds,
        )

    @property
    def speedup(self) -> float:
        """
        Return the generation speedup with outline simplification.
        """
        enabled_seconds = self.median_enabled_seconds

        if enabled_seconds == 0.0:
            return float("inf")

        return self.median_disabled_seconds / enabled_seconds

    @property
    def outline_point_reduction(self) -> int:
        """
        Return the outline point reduction.
        """
        return self.disabled_outline_points - self.enabled_outline_points

    @property
    def outline_point_reduction_percent(self) -> float:
        """
        Return the outline point reduction as a percentage.
        """
        if self.disabled_outline_points == 0:
            return 0.0

        return self.outline_point_reduction / self.disabled_outline_points * 100.0


def load_case(
    case: str,
) -> tuple[
    InputImage,
    Palette,
    GeneratorConfig,
]:
    """
    Load one benchmark case through the existing infrastructure.
    """
    loaded_config = load_config(
        REPOSITORY_ROOT / "config" / "example.toml",
    )

    config = replace(
        loaded_config,
        palette=PALETTE_ID,
        palette_version=PALETTE_VERSION,
    )

    image = load_image(
        case_image_path(
            case,
        ),
        DEVELOPER_IMAGE_INPUT_LIMITS,
    )

    palette = PaletteManager().get(
        PALETTE_ID,
        PALETTE_VERSION,
    )

    return (
        image,
        palette,
        config,
    )


def measure_generation(
    case: str,
    image: InputImage,
    palette: Palette,
    config: GeneratorConfig,
    *,
    simplification_enabled: bool,
) -> tuple[float, int]:
    """
    Measure generation and count the outline points it produced.
    """
    benchmark_config = replace(
        config,
        outline_simplification_enabled=simplification_enabled,
    )

    application = GeneratorApplication(
        image_loader=PreloadedImageLoader(
            image=image,
        ),
        overlap_detector=build_overlap_detector(),
    )

    started_at = perf_counter()

    document = application.generate(
        case_image_path(
            case,
        ),
        palette,
        benchmark_config,
    )

    finished_at = perf_counter()

    # Measure outline complexity directly. Serialized byte size would add
    # exporter-specific effects that are unrelated to simplification itself.
    return (
        finished_at - started_at,
        sum(
            len(outline.points) + sum(len(ring) for ring in outline.hole_rings)
            for outline in document.outlines
        ),
    )


def run_case(
    case: str,
    image: InputImage,
    palette: Palette,
    config: GeneratorConfig,
    *,
    runs: int,
) -> BenchmarkResult:
    """
    Benchmark generation with and without outline simplification.
    """
    if runs <= 0:
        raise ValueError(
            "runs must be greater than zero",
        )

    disabled_durations: list[float] = []
    enabled_durations: list[float] = []

    disabled_outline_points = 0
    enabled_outline_points = 0

    for run_index in range(runs):
        execution_order = (
            (
                False,
                True,
            )
            if run_index % 2 == 0
            else (
                True,
                False,
            )
        )

        for simplification_enabled in execution_order:
            duration, outline_points = measure_generation(
                case,
                image,
                palette,
                config,
                simplification_enabled=simplification_enabled,
            )

            if simplification_enabled:
                enabled_durations.append(
                    duration,
                )
                enabled_outline_points = outline_points
            else:
                disabled_durations.append(
                    duration,
                )
                disabled_outline_points = outline_points

    return BenchmarkResult(
        case=case,
        disabled_durations_seconds=tuple(
            disabled_durations,
        ),
        enabled_durations_seconds=tuple(
            enabled_durations,
        ),
        disabled_outline_points=disabled_outline_points,
        enabled_outline_points=enabled_outline_points,
    )


def format_result(
    result: BenchmarkResult,
) -> str:
    """
    Format one outline simplification benchmark result.
    """
    return (
        f"{result.case}: "
        "disabled="
        f"{result.median_disabled_seconds:.3f}s, "
        "enabled="
        f"{result.median_enabled_seconds:.3f}s, "
        f"speedup={result.speedup:.2f}x, "
        "points_disabled="
        f"{result.disabled_outline_points}, "
        "points_enabled="
        f"{result.enabled_outline_points}, "
        "point_reduction="
        f"{result.outline_point_reduction} "
        f"({result.outline_point_reduction_percent:.2f}%)"
    )


def build_parser() -> ArgumentParser:
    """
    Build the benchmark command-line parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark generation with and without " "polygon outline simplification."
        ),
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help=("Number of paired measured runs " "per benchmark case."),
    )

    parser.add_argument(
        "--case",
        choices=BENCHMARK_CASES,
        help=("Run only the selected benchmark case."),
    )

    return parser


def main() -> None:
    """
    Run the requested outline simplification benchmarks.
    """
    args = build_parser().parse_args()

    cases = (args.case,) if args.case is not None else BENCHMARK_CASES

    for case in cases:
        image, palette, config = load_case(
            case,
        )

        result = run_case(
            case,
            image,
            palette,
            config,
            runs=args.runs,
        )

        print(
            format_result(
                result,
            ),
        )


if __name__ == "__main__":
    main()
