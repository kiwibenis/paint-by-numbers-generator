# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Every developer tool command the documentation prints can be run as printed.

Two of them could not. `tools/benchmark_region_complexity_end_to_end.py` and
`tools/benchmark_region_complexity_geometry_validation.py` import a sibling
module under `tools/`, and a script invocation puts `tools/` on the import
path rather than the repository root, so both ended with

    ModuleNotFoundError: No module named 'tools'

Eighteen of the twenty-six modules under `tools/` import a sibling that way,
so the next tool to be documented is more likely than not to need the module
form as well. Checked by running each documented invocation rather than by
reading it.

`--help` is appended so the invocation is exercised without running a
benchmark: argparse handles it while parsing, after the module-level imports
that are the failure under test have already run.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest

from tools.benchmark_region_complexity import REPOSITORY_ROOT

DOCUMENTED_COMMAND = re.compile(
    r"python (?:-m (tools\.\w+)|(tools/\w+\.py))",
)

HELP_TIMEOUT_SECONDS = 120.0


def documented_invocations() -> tuple[tuple[str, ...], ...]:
    """
    Return every documented tool invocation, without its arguments.

    The arguments are left out on purpose. What failed was the invocation
    form, and running a documented argument list would run the benchmark it
    belongs to.
    """
    sources = [
        REPOSITORY_ROOT / "README.md",
        *sorted(
            (REPOSITORY_ROOT / "docs").rglob(
                "*.md",
            ),
        ),
    ]

    found: list[tuple[str, ...]] = []

    for source in sources:
        for module, script in DOCUMENTED_COMMAND.findall(
            source.read_text(
                encoding="utf-8",
            ),
        ):
            invocation = (
                (
                    "-m",
                    module,
                )
                if module
                else (script,)
            )

            if invocation not in found:
                found.append(
                    invocation,
                )

    return tuple(
        found,
    )


def run_help(
    invocation: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    """
    Run one invocation with `--help` from the repository root.
    """
    return subprocess.run(
        [
            sys.executable,
            *invocation,
            "--help",
        ],
        capture_output=True,
        check=False,
        cwd=REPOSITORY_ROOT,
        text=True,
        timeout=HELP_TIMEOUT_SECONDS,
    )


@pytest.mark.parametrize(
    "invocation",
    documented_invocations(),
    ids=lambda invocation: " ".join(
        invocation,
    ),
)
def test_the_documented_invocation_runs(
    invocation: tuple[str, ...],
) -> None:
    completed = run_help(
        invocation,
    )

    assert completed.returncode == 0, completed.stderr


def test_the_referenced_module_exists() -> None:
    """
    A path that is documented but absent fails the run above with the same
    exit code as one that is present but unimportable, and the two are
    different defects.
    """
    for invocation in documented_invocations():
        if len(invocation) == 1:
            path = REPOSITORY_ROOT / invocation[0]
        else:
            path = REPOSITORY_ROOT / (invocation[1].replace(".", "/") + ".py")

        assert path.is_file(), invocation


def test_both_invocation_forms_are_found() -> None:
    """
    Without this, a pattern that stopped matching one of the two forms would
    leave the check above passing over whatever it still found.

    The documentation uses both: the module form where a tool imports a
    sibling, the script form otherwise.
    """
    invocations = documented_invocations()

    assert any(len(invocation) == 1 for invocation in invocations)
    assert any(len(invocation) == 2 for invocation in invocations)


def test_a_command_that_does_not_run_is_reported() -> None:
    """
    Why the check above says something: it distinguishes a working
    invocation from a failing one rather than reporting success for both.
    """
    completed = run_help(
        (
            "-m",
            "tools.not_a_module_that_exists",
        ),
    )

    assert completed.returncode != 0
