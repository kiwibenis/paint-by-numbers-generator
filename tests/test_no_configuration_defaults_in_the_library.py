# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
No entry point under `src/pbn/` decides a configuration value for its caller.

ADR-0030 says the project has no program-internal configuration defaults. It
held for the configuration surface: the CLI and `build_config` require every
value, and no production path reaches a fallback. It did not hold for the
library surface, where seven entry points carried defaults of their own and
three of them disagreed with every shipped profile:

    RegionMergeCostCalculator          0.40 / 0.20 / 0.20 / 0.20
    config/example.toml                0.40 / 0.25 / 0.15 / 0.20

    PdfExporter.write                  font_size_pt 9, line_width_pt 0.4
    config/example.toml                font_size_pt 3, line_width_pt 0.1

    RegionGenerator.generate           minimum_circle_diameter_px 2
    resolved from the profile          7, 13 or 21, by image size

`RegionMergeCandidateRanker` was the worst of them: omitting its calculator
did not select different weights, it selected the base calculator, which has
no enclosure or compactness protection at all. That is a different algorithm,
reached by leaving an argument out.

The names checked are the configuration's own field names, read from
`GeneratorConfig`, so a configuration value added later is covered without
being listed here.
"""

from __future__ import annotations

import ast
import dataclasses
import typing
from pathlib import Path

import pytest

from pbn.config.models import GeneratorConfig
from tools.benchmark_region_complexity import REPOSITORY_ROOT

PACKAGE_DIRECTORY = REPOSITORY_ROOT / "src" / "pbn"

ADDITIONAL_POLICY_PARAMETERS = frozenset(
    {
        "minimum_circle_diameter_px",
        "cost_calculator",
    },
)
"""
Two values the configuration owns without naming them.

`minimum_circle_diameter_px` is resolved from `minimum_region_size_mm` and
the image size, and `cost_calculator` carries the whole merge-cost policy
including which algorithm applies it.
"""


def configuration_field_names(
    cls: type,
) -> frozenset[str]:
    """
    Return every field name in the configuration, nested ones included.
    """
    found: set[str] = set()

    hints = typing.get_type_hints(
        cls,
    )

    for field in dataclasses.fields(
        cls,
    ):
        found.add(
            field.name,
        )

        annotation = hints[field.name]

        if isinstance(
            annotation,
            type,
        ) and dataclasses.is_dataclass(
            annotation,
        ):
            found |= configuration_field_names(
                annotation,
            )

    return frozenset(
        found,
    )


POLICY_PARAMETERS = (
    configuration_field_names(
        GeneratorConfig,
    )
    | ADDITIONAL_POLICY_PARAMETERS
)

PACKAGE_MODULES = tuple(
    sorted(
        PACKAGE_DIRECTORY.rglob(
            "*.py",
        ),
    ),
)


def defaulted_policy_parameters(
    path: Path,
) -> tuple[tuple[int, str, str], ...]:
    """
    Return `(line, function, parameter)` for each policy default declared.

    Dataclass fields are skipped. The configuration models are themselves
    dataclasses whose fields carry these names, and a field is a value, not
    a decision made for a caller.
    """
    tree = ast.parse(
        path.read_text(
            encoding="utf-8",
        ),
    )

    dataclass_bodies = {
        child
        for node in ast.walk(
            tree,
        )
        if isinstance(node, ast.ClassDef)
        and any(
            "dataclass"
            in ast.unparse(
                decorator,
            )
            for decorator in node.decorator_list
        )
        for child in ast.walk(
            node,
        )
    }

    found: list[tuple[int, str, str]] = []

    for node in ast.walk(
        tree,
    ):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node in dataclass_bodies and node.name != "__init__":
            continue

        arguments = node.args

        defaulted = list(
            zip(
                arguments.args[len(arguments.args) - len(arguments.defaults) :],
                arguments.defaults,
            ),
        ) + [
            (argument, default)
            for argument, default in zip(
                arguments.kwonlyargs,
                arguments.kw_defaults,
            )
            if default is not None
        ]

        for argument, _ in defaulted:
            if argument.arg in POLICY_PARAMETERS:
                found.append(
                    (
                        node.lineno,
                        node.name,
                        argument.arg,
                    ),
                )

    return tuple(
        found,
    )


@pytest.mark.parametrize(
    "path",
    PACKAGE_MODULES,
    ids=lambda path: str(
        path.relative_to(
            PACKAGE_DIRECTORY,
        ),
    ),
)
def test_the_module_decides_no_configuration_value_for_its_caller(
    path: Path,
) -> None:
    declared = defaulted_policy_parameters(
        path,
    )

    assert declared == (), (
        f"{path.relative_to(PACKAGE_DIRECTORY)} supplies a default for a "
        f"value the configuration owns: {declared}"
    )


def test_the_configuration_field_names_were_found() -> None:
    """
    Without this, an empty name set would leave every check above passing
    over nothing.
    """
    assert "color_weight" in POLICY_PARAMETERS
    assert "font_size_pt" in POLICY_PARAMETERS
    assert "minimum_region_size_mm" in POLICY_PARAMETERS
    assert "outline_simplification_tolerance_px" in POLICY_PARAMETERS

    assert len(POLICY_PARAMETERS) > 40


def test_the_package_modules_were_found() -> None:
    """
    And without this, an empty module list would do the same.
    """
    names = {path.name for path in PACKAGE_MODULES}

    assert "merge_cost_calculator.py" in names
    assert "pdf_exporter.py" in names
    assert len(PACKAGE_MODULES) > 50


def test_a_reintroduced_default_is_reported(
    tmp_path: Path,
) -> None:
    """
    Why the check says something: it separates a required parameter from one
    the module answers itself, rather than accepting both.
    """
    offending = tmp_path / "offending_module.py"

    offending.write_text(
        "class Calculator:\n"
        "    def __init__(\n"
        "        self,\n"
        "        *,\n"
        "        color_weight: float = 0.40,\n"
        "    ) -> None:\n"
        "        self._color_weight = color_weight\n",
        encoding="utf-8",
    )

    assert defaulted_policy_parameters(
        offending,
    ) == (
        (
            2,
            "__init__",
            "color_weight",
        ),
    )


def test_a_configuration_dataclass_field_is_not_reported(
    tmp_path: Path,
) -> None:
    """
    The configuration models declare these names as fields, and a field with
    a value is not a decision taken on a caller's behalf.
    """
    model = tmp_path / "model_module.py"

    model.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        "class Example:\n"
        "    color_weight: float = 0.40\n",
        encoding="utf-8",
    )

    assert (
        defaulted_policy_parameters(
            model,
        )
        == ()
    )
