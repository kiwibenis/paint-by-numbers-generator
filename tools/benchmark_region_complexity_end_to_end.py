# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
End-to-end optional region-complexity reduction benchmark.

This developer-only module compares complete CLI generation with optional
region complexity reduction disabled and enabled while keeping all other
generation policy values identical.

Generation policy is taken from `config/example.toml` and is not restated
here. The command line carries only the benchmark parameters: the palette,
the reduction state under test, the derived region target and the paths.
Everything else reaches the generator through `--config_file`, so a
recalibrated profile is measured as recalibrated rather than overridden by a
stale copy of its values. The tool once passed a `minimum_region_size_mm` of
its own that the profile no longer shipped, and the published numbers then
described a paintability policy the project does not have.

The palette is the one deliberate divergence. The profile ships
`reference8`, which is too small to exercise region complexity, so the
palette is a benchmark parameter rather than policy under test.
"""

from __future__ import annotations

import subprocess
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from statistics import median
from time import perf_counter

from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    palette_path,
    prepare_case,
    resolve_color_distance,
    resolve_max_regions,
)

BENCHMARK_OUTPUT_DIRECTORY = REPOSITORY_ROOT / "tools" / "output"

CONFIG_PATH = REPOSITORY_ROOT / "config" / "example.toml"

PALETTE_ID = "faberCastellPolychromos120"
PALETTE_VERSION = 1


@dataclass(frozen=True, slots=True)
class RegionComplexityEndToEndBenchmarkResult:
    """
    End-to-end timings for disabled and enabled optional reduction.
    """

    case: str
    baseline_region_count: int
    max_regions: int
    disabled_durations_seconds: tuple[float, ...]
    enabled_durations_seconds: tuple[float, ...]

    @property
    def run_count(self) -> int:
        """
        Return the number of paired benchmark runs.
        """
        return len(
            self.disabled_durations_seconds,
        )

    @property
    def median_disabled_seconds(self) -> float:
        """
        Return median generation time with optional reduction disabled.
        """
        return median(
            self.disabled_durations_seconds,
        )

    @property
    def median_enabled_seconds(self) -> float:
        """
        Return median generation time with optional reduction enabled.
        """
        return median(
            self.enabled_durations_seconds,
        )

    @property
    def median_overhead_seconds(self) -> float:
        """
        Return enabled minus disabled median generation time.
        """
        return self.median_enabled_seconds - self.median_disabled_seconds

    @property
    def median_overhead_fraction(self) -> float:
        """
        Return relative enabled end-to-end overhead.
        """
        disabled_seconds = self.median_disabled_seconds

        if disabled_seconds == 0.0:
            return float("inf")

        return self.median_overhead_seconds / disabled_seconds

    @property
    def median_enabled_to_disabled_ratio(self) -> float:
        """
        Return enabled duration divided by disabled duration.
        """
        disabled_seconds = self.median_disabled_seconds

        if disabled_seconds == 0.0:
            return float("inf")

        return self.median_enabled_seconds / disabled_seconds


def build_command(
    case: str,
    *,
    reduction_enabled: bool,
    max_regions: int,
) -> list[str]:
    """
    Build one complete CLI generation command.
    """
    input_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"

    reduction_state = "enabled" if reduction_enabled else "disabled"

    output_path = BENCHMARK_OUTPUT_DIRECTORY / (
        "benchmark-region-complexity-" f"{case}-{reduction_state}.pdf"
    )

    return [
        sys.executable,
        "-m",
        "pbn",
        "generate",
        "--config_file",
        str(CONFIG_PATH),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--palette",
        PALETTE_ID,
        "--palette-version",
        str(PALETTE_VERSION),
        "--region-complexity-reduction-enabled",
        ("true" if reduction_enabled else "false"),
        "--max-regions",
        str(max_regions),
    ]


def measure_generation(
    case: str,
    *,
    reduction_enabled: bool,
    max_regions: int,
) -> float:
    """
    Measure one complete CLI generation run.
    """
    command = build_command(
        case,
        reduction_enabled=reduction_enabled,
        max_regions=max_regions,
    )

    started_at = perf_counter()

    subprocess.run(
        command,
        check=True,
        cwd=REPOSITORY_ROOT,
    )

    finished_at = perf_counter()

    return finished_at - started_at


def run_case(
    case: str,
    *,
    baseline_region_count: int,
    max_regions: int,
    runs: int,
) -> RegionComplexityEndToEndBenchmarkResult:
    """
    Benchmark paired disabled and enabled complete generation runs.
    """
    if runs <= 0:
        raise ValueError(
            "runs must be greater than zero",
        )

    if baseline_region_count <= 0:
        raise ValueError(
            "baseline_region_count must be greater than zero",
        )

    if max_regions <= 0:
        raise ValueError(
            "max_regions must be greater than zero",
        )

    BENCHMARK_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    disabled_durations: list[float] = []
    enabled_durations: list[float] = []

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

        for reduction_enabled in execution_order:
            duration = measure_generation(
                case,
                reduction_enabled=reduction_enabled,
                max_regions=max_regions,
            )

            if reduction_enabled:
                enabled_durations.append(
                    duration,
                )
            else:
                disabled_durations.append(
                    duration,
                )

    return RegionComplexityEndToEndBenchmarkResult(
        case=case,
        baseline_region_count=baseline_region_count,
        max_regions=max_regions,
        disabled_durations_seconds=tuple(
            disabled_durations,
        ),
        enabled_durations_seconds=tuple(
            enabled_durations,
        ),
    )


def format_result(
    result: RegionComplexityEndToEndBenchmarkResult,
) -> str:
    """
    Format one paired end-to-end benchmark result.
    """
    return (
        f"{result.case}: "
        "baseline_regions="
        f"{result.baseline_region_count}, "
        f"max_regions={result.max_regions}, "
        f"runs={result.run_count}, "
        "disabled="
        f"{result.median_disabled_seconds:.3f}s, "
        "enabled="
        f"{result.median_enabled_seconds:.3f}s, "
        "overhead="
        f"{result.median_overhead_seconds:.3f}s, "
        "overhead_percent="
        f"{result.median_overhead_fraction * 100.0:.2f}%, "
        "enabled_to_disabled="
        f"{result.median_enabled_to_disabled_ratio:.3f}x"
    )


def build_parser() -> ArgumentParser:
    """
    Build the end-to-end complexity benchmark parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark complete generation with optional "
            "region complexity reduction disabled and enabled."
        ),
    )

    parser.add_argument(
        "--cases",
        nargs="+",
        choices=EVALUATION_CASES,
        default=EVALUATION_CASES,
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help=("Number of paired complete generation runs " "per representative case."),
    )

    parser.add_argument(
        "--target-fraction",
        type=float,
        default=0.5,
        help=("Fraction of the mandatory baseline used to " "derive max_regions."),
    )

    return parser


def main() -> None:
    """
    Run paired end-to-end optional-complexity benchmarks.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.runs <= 0:
        parser.error(
            "--runs must be greater than zero",
        )

    if not 0.0 < args.target_fraction <= 1.0:
        parser.error(
            "--target-fraction must be greater than zero and at most one",
        )

    config = load_config(
        CONFIG_PATH,
    )

    palette = load_palette(
        palette_path(
            palette_id=PALETTE_ID,
            palette_version=PALETTE_VERSION,
        ),
    )

    color_distance = resolve_color_distance(
        config.color_distance,
    )

    print(
        (
            f"profile={CONFIG_PATH.name}, "
            f"palette={PALETTE_ID}, "
            f"palette_version={PALETTE_VERSION}, "
            f"color_distance={config.color_distance}, "
            "minimum_region_size_mm="
            f"{config.minimum_region_size_mm:g}, "
            "maximum_merge_cost="
            f"{config.region_complexity.maximum_merge_cost:g}, "
            "target_fraction="
            f"{args.target_fraction:g}, "
            f"runs={args.runs}"
        ),
    )

    for case in args.cases:
        prepared = prepare_case(
            case=case,
            config=config,
            palette=palette,
            color_distance=color_distance,
        )

        baseline_region_count = len(
            prepared.regions,
        )

        max_regions = resolve_max_regions(
            baseline_region_count=(baseline_region_count),
            target_fraction=args.target_fraction,
        )

        result = run_case(
            case,
            baseline_region_count=(baseline_region_count),
            max_regions=max_regions,
            runs=args.runs,
        )

        print(
            format_result(
                result,
            ),
        )


if __name__ == "__main__":
    main()
