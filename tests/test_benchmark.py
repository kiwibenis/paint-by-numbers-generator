# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pbn.infrastructure.config_loader import load_config
from tools import benchmark


def test_benchmark_cases_cover_all_performance_images() -> None:
    assert benchmark.BENCHMARK_CASES == (
        "simple_smaller",
        "simple",
        "medium_smaller",
        "medium",
        "complex_smaller",
        "complex",
    )


def test_benchmark_uses_established_polychromos_palette() -> None:
    assert benchmark.PALETTE_ID == "faberCastellPolychromos60"
    assert benchmark.PALETTE_VERSION == 1


def test_build_command_runs_complete_sequential_cli_pipeline() -> None:
    command = benchmark.build_command(
        "simple",
        parallel_enabled=False,
    )

    assert command == [
        sys.executable,
        "-m",
        "pbn",
        "generate",
        "--config_file",
        str(benchmark.REPOSITORY_ROOT / "config" / "example.toml"),
        "--input",
        str(benchmark.REPOSITORY_ROOT / "examples" / "input" / "simple.png"),
        "--output",
        str(benchmark.BENCHMARK_OUTPUT_DIRECTORY / "benchmark-simple.pdf"),
        "--palette",
        "faberCastellPolychromos60",
        "--palette-version",
        "1",
        "--parallel-quantization-enabled",
        "false",
    ]


def test_the_command_carries_only_benchmark_parameters() -> None:
    """
    Generation policy reaches the generator through the profile, never
    through a value restated in the benchmark.

    The colour distance used to be passed from a constant here, and a test
    asserted that constant against itself, which detects an edit to the
    constant but never a disagreement with the shipped profile.
    """
    for parallel_enabled in (
        False,
        True,
    ):
        command = benchmark.build_command(
            "simple",
            parallel_enabled=parallel_enabled,
        )

        assert tuple(argument for argument in command if argument.startswith("--")) == (
            "--config_file",
            "--input",
            "--output",
            "--palette",
            "--palette-version",
            "--parallel-quantization-enabled",
        )


def test_the_profile_supplies_the_colour_distance() -> None:
    """
    What the removed constant used to say, asserted against the profile the
    benchmark actually runs.
    """
    assert (
        load_config(
            benchmark.REPOSITORY_ROOT / "config" / "example.toml",
        ).color_distance
        == "delta_e_2000"
    )


def test_build_command_runs_complete_parallel_cli_pipeline() -> None:
    command = benchmark.build_command(
        "simple",
        parallel_enabled=True,
    )

    assert command[-2:] == [
        "--parallel-quantization-enabled",
        "true",
    ]


def test_run_case_creates_benchmark_output_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "benchmark-output"

    monkeypatch.setattr(
        benchmark,
        "BENCHMARK_OUTPUT_DIRECTORY",
        output_directory,
    )

    def fake_measure_generation(
        case: str,
        *,
        parallel_enabled: bool,
    ) -> float:
        return 1.0

    monkeypatch.setattr(
        benchmark,
        "measure_generation",
        fake_measure_generation,
    )

    benchmark.run_case(
        "simple",
        runs=1,
    )

    assert output_directory.is_dir()


def test_measure_generation_runs_complete_cli_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[list[str], bool, Path]] = []

    def fake_run(
        command: list[str],
        *,
        check: bool,
        cwd: Path,
    ) -> None:
        commands.append(
            (
                command,
                check,
                cwd,
            ),
        )

    times = iter(
        (
            10.0,
            12.5,
        ),
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )
    monkeypatch.setattr(
        benchmark,
        "perf_counter",
        lambda: next(times),
    )

    duration = benchmark.measure_generation(
        "simple",
        parallel_enabled=True,
    )

    assert duration == pytest.approx(
        2.5,
    )

    assert commands == [
        (
            benchmark.build_command(
                "simple",
                parallel_enabled=True,
            ),
            True,
            benchmark.REPOSITORY_ROOT,
        ),
    ]


def test_run_case_measures_requested_number_of_paired_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "benchmark-output"

    monkeypatch.setattr(
        benchmark,
        "BENCHMARK_OUTPUT_DIRECTORY",
        output_directory,
    )

    calls: list[bool] = []

    sequential_durations = iter(
        (
            4.0,
            6.0,
        ),
    )
    parallel_durations = iter(
        (
            2.0,
            3.0,
        ),
    )

    def fake_measure_generation(
        case: str,
        *,
        parallel_enabled: bool,
    ) -> float:
        assert case == "simple"

        calls.append(
            parallel_enabled,
        )

        if parallel_enabled:
            return next(
                parallel_durations,
            )

        return next(
            sequential_durations,
        )

    monkeypatch.setattr(
        benchmark,
        "measure_generation",
        fake_measure_generation,
    )

    result = benchmark.run_case(
        "simple",
        runs=2,
    )

    assert calls == [
        False,
        True,
        True,
        False,
    ]

    assert result.case == "simple"
    assert result.sequential_durations_seconds == (
        4.0,
        6.0,
    )
    assert result.parallel_durations_seconds == (
        2.0,
        3.0,
    )


def test_run_case_rejects_non_positive_run_count() -> None:
    with pytest.raises(
        ValueError,
        match="runs must be greater than zero",
    ):
        benchmark.run_case(
            "simple",
            runs=0,
        )


def test_benchmark_result_reports_median_durations_and_speedup() -> None:
    result = benchmark.BenchmarkResult(
        case="simple",
        sequential_durations_seconds=(
            6.0,
            4.0,
            5.0,
        ),
        parallel_durations_seconds=(
            3.0,
            2.0,
            2.5,
        ),
    )

    assert result.median_sequential_seconds == pytest.approx(
        5.0,
    )
    assert result.median_parallel_seconds == pytest.approx(
        2.5,
    )
    assert result.speedup == pytest.approx(
        2.0,
    )


def test_format_result_reports_end_to_end_speedup() -> None:
    result = benchmark.BenchmarkResult(
        case="simple",
        sequential_durations_seconds=(5.0,),
        parallel_durations_seconds=(4.0,),
    )

    assert benchmark.format_result(
        result,
    ) == ("simple: " "sequential=5.000s, " "parallel=4.000s, " "speedup=1.25x")


def test_parser_accepts_run_count() -> None:
    args = benchmark.build_parser().parse_args(
        [
            "--runs",
            "5",
        ],
    )

    assert args.runs == 5
