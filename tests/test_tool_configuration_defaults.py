# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
No developer tool supplies its own default for a generation policy value.

ADR-0030 says the project has no program-internal configuration defaults.
The tools under `tools/` are outside the generator, so the rule does not
reach them by itself, and two of them had drifted:
`benchmark_region_complexity_geometry_validation` and
`benchmark_region_complexity_downstream_performance` both defaulted
`--minimum-region-size-mm` to `1.0` while the shipped profile said `2.0`,
and both applied that default unconditionally to the profile they had just
loaded. The geometry evaluation documents its tool as being run without
arguments, so its published numbers were taken at half the shipped
paintability.

A tool may still override any of these per run. What it may not do is decide
the value on the caller's behalf, because a decision made in a constant is
invisible in the recorded command and cannot be kept in step with the
profile.

The option set is taken from the generator's own parser rather than from a
list here, so an option added to the generator is covered on the day it is
added.
"""

from __future__ import annotations

import ast
from argparse import ArgumentParser
from pathlib import Path

import pytest

from pbn.cli.main import build_parser as build_generator_parser
from tools.benchmark_region_complexity import REPOSITORY_ROOT

TOOLS_DIRECTORY = REPOSITORY_ROOT / "tools"

ACCEPTED_DEFAULTS = (
    "None",
    "<none given>",
)
"""
An option that carries no default, or `None`, leaves the value to the
profile. Anything else answers the question the profile is there to answer.
"""


def generator_option_strings(
    parser: ArgumentParser,
) -> frozenset[str]:
    """
    Return every long option the generator accepts, subcommands included.
    """
    found: set[str] = set()

    for action in parser._actions:
        found.update(
            option for option in action.option_strings if option.startswith("--")
        )

        choices = getattr(
            action,
            "choices",
            None,
        )

        if isinstance(choices, dict):
            for subparser in choices.values():
                if isinstance(subparser, ArgumentParser):
                    found |= generator_option_strings(
                        subparser,
                    )

    return frozenset(
        found,
    )


GENERATOR_OPTIONS = generator_option_strings(
    build_generator_parser(),
)


def declared_defaults(
    path: Path,
) -> tuple[tuple[int, str, str], ...]:
    """
    Return `(line, option, default)` for the generator options a tool declares.

    Read from the source rather than by building each parser, because a
    parser is built inside a function whose module-level import cost is not
    worth paying to read one keyword argument.
    """
    found: list[tuple[int, str, str]] = []

    for node in ast.walk(
        ast.parse(
            path.read_text(
                encoding="utf-8",
            ),
        ),
    ):
        if not isinstance(node, ast.Call):
            continue

        if (
            getattr(
                node.func,
                "attr",
                "",
            )
            != "add_argument"
        ):
            continue

        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue

        option = node.args[0].value

        if option not in GENERATOR_OPTIONS:
            continue

        default = next(
            (keyword.value for keyword in node.keywords if keyword.arg == "default"),
            None,
        )

        found.append(
            (
                node.lineno,
                option,
                (
                    "<none given>"
                    if default is None
                    else ast.unparse(
                        default,
                    )
                ),
            ),
        )

    return tuple(
        found,
    )


TOOL_MODULES = tuple(
    sorted(
        TOOLS_DIRECTORY.glob(
            "*.py",
        ),
    ),
)


@pytest.mark.parametrize(
    "path",
    TOOL_MODULES,
    ids=lambda path: path.name,
)
def test_the_tool_leaves_generation_policy_to_the_profile(
    path: Path,
) -> None:
    offenders = [
        (line, option, default)
        for line, option, default in declared_defaults(
            path,
        )
        if default not in ACCEPTED_DEFAULTS
    ]

    assert offenders == [], (
        f"{path.name} decides a generation value the profile owns: " f"{offenders}"
    )


def test_the_generator_options_were_found() -> None:
    """
    Without this, a parser walk that returned nothing would leave every
    check above passing over an empty option set.
    """
    assert "--minimum-region-size-mm" in GENERATOR_OPTIONS
    assert "--color-distance" in GENERATOR_OPTIONS
    assert "--maximum-merge-cost" in GENERATOR_OPTIONS


def test_the_tools_declare_such_options_at_all() -> None:
    """
    And without this, a scan that matched nothing would pass the same way.
    """
    declaring = [
        path.name
        for path in TOOL_MODULES
        if declared_defaults(
            path,
        )
    ]

    assert len(declaring) >= 10


def test_a_tool_supplied_default_is_reported(
    tmp_path: Path,
) -> None:
    """
    Why the check says something: it separates a profile-backed option from
    one the tool answers itself, rather than accepting both.
    """
    offending = tmp_path / "offending_tool.py"

    offending.write_text(
        "from argparse import ArgumentParser\n"
        "\n"
        "\n"
        "def build_parser() -> ArgumentParser:\n"
        "    parser = ArgumentParser()\n"
        '    parser.add_argument("--minimum-region-size-mm", default=1.0)\n'
        "    return parser\n",
        encoding="utf-8",
    )

    assert declared_defaults(
        offending,
    ) == (
        (
            6,
            "--minimum-region-size-mm",
            "1.0",
        ),
    )
