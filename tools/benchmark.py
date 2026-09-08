# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
End-to-end generation pipeline benchmarks.

Generation policy is taken from `config/example.toml` and is not restated
here. The command line carries only the benchmark parameters: the palette,
the parallel-quantization state under test and the paths. Everything else
reaches the generator through `--config_file`, so a recalibrated profile is
measured as recalibrated rather than overridden by a stale copy of its
values.

The palette is the one deliberate divergence. The profile ships
`reference8`, which is too small for a representative end-to-end run.
"""

from __future__ import annotations

import subprocess
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_OUTPUT_DIRECTORY = REPOSITORY_ROOT / "tools" / "output"

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


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """
    End-to-end timing results for one benchmark case.
    """

    case: str
    sequential_durations_seconds: tuple[float, ...]
    parallel_durations_seconds: tuple[float, ...]

    @property
    def median_sequential_seconds(self) -> float:
        """
        Return the median sequential generation duration.
        """
        return median(
            self.sequential_durations_seconds,
        )

    @property
    def median_parallel_seconds(self) -> float:
        """
        Return the median parallel generation duration.
        """
        return median(
            self.parallel_durations_seconds,
        )

    @property
    def speedup(self) -> float:
        """
        Return the end-to-end parallel speedup.
        """
        parallel_seconds = self.median_parallel_seconds

        if parallel_seconds == 0.0:
            return float("inf")

        return self.median_sequential_seconds / parallel_seconds


def build_command(
    case: str,
    *,
    parallel_enabled: bool,
) -> list[str]:
    """
    Build the complete CLI generation command for a benchmark case.
    """
    config_path = REPOSITORY_ROOT / "config" / "example.toml"
    input_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"
    output_path = BENCHMARK_OUTPUT_DIRECTORY / f"benchmark-{case}.pdf"

    return [
        sys.executable,
        "-m",
        "pbn",
        "generate",
        "--config_file",
        str(config_path),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--palette",
        PALETTE_ID,
        "--palette-version",
        str(PALETTE_VERSION),
        "--parallel-quantization-enabled",
        ("true" if parallel_enabled else "false"),
    ]


def measure_generation(
    case: str,
    *,
    parallel_enabled: bool,
) -> float:
    """
    Measure one complete generation run.
    """
    command = build_command(
        case,
        parallel_enabled=parallel_enabled,
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
    runs: int,
) -> BenchmarkResult:
    """
    Benchmark sequential and parallel generation for one case.
    """
    if runs <= 0:
        raise ValueError(
            "runs must be greater than zero",
        )

    BENCHMARK_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    sequential_durations: list[float] = []
    parallel_durations: list[float] = []

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

        for parallel_enabled in execution_order:
            duration = measure_generation(
                case,
                parallel_enabled=parallel_enabled,
            )

            if parallel_enabled:
                parallel_durations.append(
                    duration,
                )
            else:
                sequential_durations.append(
                    duration,
                )

    return BenchmarkResult(
        case=case,
        sequential_durations_seconds=tuple(
            sequential_durations,
        ),
        parallel_durations_seconds=tuple(
            parallel_durations,
        ),
    )


def format_result(
    result: BenchmarkResult,
) -> str:
    """
    Format one end-to-end benchmark result.
    """
    return (
        f"{result.case}: "
        "sequential="
        f"{result.median_sequential_seconds:.3f}s, "
        "parallel="
        f"{result.median_parallel_seconds:.3f}s, "
        f"speedup={result.speedup:.2f}x"
    )


def build_parser() -> ArgumentParser:
    """
    Build the benchmark command-line parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark sequential and parallel " "complete generation pipelines."
        ),
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help=("Number of paired measured runs " "per benchmark case."),
    )

    return parser


def main() -> None:
    """
    Run all end-to-end generation benchmarks.
    """
    args = build_parser().parse_args()

    for case in BENCHMARK_CASES:
        result = run_case(
            case,
            runs=args.runs,
        )

        print(
            format_result(
                result,
            ),
        )


if __name__ == "__main__":
    main()
