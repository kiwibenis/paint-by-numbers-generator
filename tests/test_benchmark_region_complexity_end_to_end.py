# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pbn.cli.main import build_parser as build_generator_parser
from pbn.infrastructure.config_loader import load_config
from tools import benchmark_region_complexity_end_to_end as benchmark
from tools.benchmark_region_complexity import REPOSITORY_ROOT

BENCHMARK_PARAMETER_OPTIONS = (
    "--config_file",
    "--input",
    "--output",
    "--palette",
    "--palette-version",
    "--region-complexity-reduction-enabled",
    "--max-regions",
)
"""
The only options the benchmark is allowed to put on the command line.

Each is a property of the experiment rather than of the shipped policy: the
profile to measure, the two paths, the palette that makes region complexity
observable, the reduction state under test and the target derived from each
case's own baseline.
"""

RESTATED_POLICY_OPTIONS = (
    (
        "--maximum-merge-cost",
        "0.3",
    ),
    (
        "--merge-cost-color-weight",
        "0.4",
    ),
    (
        "--merge-cost-affected-area-weight",
        "0.25",
    ),
    (
        "--merge-cost-border-weight",
        "0.15",
    ),
    (
        "--merge-cost-geometry-weight",
        "0.2",
    ),
    (
        "--merge-cost-enclosure-strength",
        "0.5",
    ),
    (
        "--merge-cost-compactness-strength",
        "0.15",
    ),
    (
        "--minimum-region-size-mm",
        "2.0",
    ),
    (
        "--color-distance",
        "delta_e_2000",
    ),
)
"""
The nine options the benchmark used to pass from constants of its own.

Kept by name so a reintroduction is caught as the specific regression it is
rather than as a list that no longer matches anything.
"""


def test_build_command_runs_complete_disabled_cli_pipeline() -> None:
    command = benchmark.build_command(
        "simple",
        reduction_enabled=False,
        max_regions=40,
    )

    assert command == [
        sys.executable,
        "-m",
        "pbn",
        "generate",
        "--config_file",
        str(benchmark.CONFIG_PATH),
        "--input",
        str(REPOSITORY_ROOT / "examples" / "input" / "simple.png"),
        "--output",
        str(
            benchmark.BENCHMARK_OUTPUT_DIRECTORY
            / ("benchmark-region-complexity-" "simple-disabled.pdf")
        ),
        "--palette",
        "faberCastellPolychromos120",
        "--palette-version",
        "1",
        "--region-complexity-reduction-enabled",
        "false",
        "--max-regions",
        "40",
    ]


def test_the_command_carries_only_benchmark_parameters() -> None:
    """
    Generation policy reaches the generator through the profile, never
    through a value restated in the benchmark.

    The tool once passed `--minimum-region-size-mm` from a constant of its
    own while the profile shipped a different value, so the published
    end-to-end numbers described a paintability policy the project does not
    have. A restated value cannot be kept in step by review, only by not
    existing.
    """
    for reduction_enabled in (
        False,
        True,
    ):
        command = benchmark.build_command(
            "simple",
            reduction_enabled=reduction_enabled,
            max_regions=40,
        )

        assert (
            tuple(argument for argument in command if argument.startswith("--"))
            == BENCHMARK_PARAMETER_OPTIONS
        )


@pytest.mark.parametrize(
    (
        "option",
        "value",
    ),
    RESTATED_POLICY_OPTIONS,
)
def test_the_generator_would_have_accepted_the_policy_option(
    option: str,
    value: str,
) -> None:
    """
    Why the test above says something.

    Without this, it would pass just as well if the generator had lost these
    options entirely, which is a different fact about a different defect.
    They exist and are accepted; the benchmark declines to use them.
    """
    _, unrecognized = build_generator_parser().parse_known_args(
        [
            "generate",
            option,
            value,
        ],
    )

    assert unrecognized == []


def test_the_profile_supplies_the_policy_the_command_no_longer_passes() -> None:
    """
    The benchmark relies on the profile being complete, and the project has
    no program-internal defaults, so an incomplete profile would fail per
    run rather than per suite.
    """
    config = load_config(
        benchmark.CONFIG_PATH,
    )

    assert config.minimum_region_size_mm > 0.0
    assert config.region_complexity.maximum_merge_cost > 0.0
    assert config.color_distance


def test_build_command_changes_only_reduction_state_and_output() -> None:
    disabled = benchmark.build_command(
        "simple",
        reduction_enabled=False,
        max_regions=40,
    )

    enabled = benchmark.build_command(
        "simple",
        reduction_enabled=True,
        max_regions=40,
    )

    disabled_without_output = list(
        disabled,
    )
    enabled_without_output = list(
        enabled,
    )

    output_index = (
        disabled_without_output.index(
            "--output",
        )
        + 1
    )

    disabled_without_output[output_index] = "<output>"
    enabled_without_output[output_index] = "<output>"

    reduction_index = (
        disabled_without_output.index(
            "--region-complexity-reduction-enabled",
        )
        + 1
    )

    assert (
        disabled_without_output[:reduction_index]
        == enabled_without_output[:reduction_index]
    )

    disabled_without_output[reduction_index] = "<reduction-state>"
    enabled_without_output[reduction_index] = "<reduction-state>"

    assert disabled_without_output == enabled_without_output


def test_measure_generation_runs_complete_cli_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[
        tuple[
            list[str],
            bool,
            Path,
        ]
    ] = []

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
        reduction_enabled=True,
        max_regions=40,
    )

    assert duration == pytest.approx(
        2.5,
    )

    assert commands == [
        (
            benchmark.build_command(
                "simple",
                reduction_enabled=True,
                max_regions=40,
            ),
            True,
            REPOSITORY_ROOT,
        ),
    ]


def test_run_case_alternates_disabled_and_enabled_order(
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

    disabled_durations = iter(
        (
            10.0,
            12.0,
            11.0,
        ),
    )

    enabled_durations = iter(
        (
            14.0,
            15.0,
            13.0,
        ),
    )

    def fake_measure_generation(
        case: str,
        *,
        reduction_enabled: bool,
        max_regions: int,
    ) -> float:
        assert case == "simple"
        assert max_regions == 40

        calls.append(
            reduction_enabled,
        )

        if reduction_enabled:
            return next(
                enabled_durations,
            )

        return next(
            disabled_durations,
        )

    monkeypatch.setattr(
        benchmark,
        "measure_generation",
        fake_measure_generation,
    )

    result = benchmark.run_case(
        "simple",
        baseline_region_count=80,
        max_regions=40,
        runs=3,
    )

    assert output_directory.is_dir()

    assert calls == [
        False,
        True,
        True,
        False,
        False,
        True,
    ]

    assert result.disabled_durations_seconds == (
        10.0,
        12.0,
        11.0,
    )

    assert result.enabled_durations_seconds == (
        14.0,
        15.0,
        13.0,
    )


def test_run_case_rejects_non_positive_run_count() -> None:
    with pytest.raises(
        ValueError,
        match="runs must be greater than zero",
    ):
        benchmark.run_case(
            "simple",
            baseline_region_count=80,
            max_regions=40,
            runs=0,
        )


def test_result_reports_median_end_to_end_overhead() -> None:
    result = benchmark.RegionComplexityEndToEndBenchmarkResult(
        case="simple",
        baseline_region_count=80,
        max_regions=40,
        disabled_durations_seconds=(
            10.0,
            12.0,
            11.0,
        ),
        enabled_durations_seconds=(
            14.0,
            15.0,
            13.0,
        ),
    )

    assert result.run_count == 3

    assert result.median_disabled_seconds == pytest.approx(
        11.0,
    )

    assert result.median_enabled_seconds == pytest.approx(
        14.0,
    )

    assert result.median_overhead_seconds == pytest.approx(
        3.0,
    )

    assert result.median_overhead_fraction == pytest.approx(
        3.0 / 11.0,
    )

    assert result.median_enabled_to_disabled_ratio == pytest.approx(
        14.0 / 11.0,
    )


def test_format_result_reports_end_to_end_overhead() -> None:
    result = benchmark.RegionComplexityEndToEndBenchmarkResult(
        case="simple",
        baseline_region_count=80,
        max_regions=40,
        disabled_durations_seconds=(10.0,),
        enabled_durations_seconds=(12.0,),
    )

    assert benchmark.format_result(
        result,
    ) == (
        "simple: "
        "baseline_regions=80, "
        "max_regions=40, "
        "runs=1, "
        "disabled=10.000s, "
        "enabled=12.000s, "
        "overhead=2.000s, "
        "overhead_percent=20.00%, "
        "enabled_to_disabled=1.200x"
    )


def test_parser_accepts_cases_runs_and_target_fraction() -> None:
    args = benchmark.build_parser().parse_args(
        [
            "--cases",
            "simple",
            "complex",
            "--runs",
            "5",
            "--target-fraction",
            "0.5",
        ],
    )

    assert args.cases == [
        "simple",
        "complex",
    ]

    assert args.runs == 5
    assert args.target_fraction == pytest.approx(
        0.5,
    )
