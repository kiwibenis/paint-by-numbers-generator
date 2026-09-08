# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
No project-internal operational failure is introduced outside the hierarchy.

`docs/integration-contract.md` states that failures representing a request or
operation outcome in the supported generation workflow are `PbnError`
instances, and the CLI acts on that: it catches `PbnError` and nothing else,
derives the exit code from `caused_by_request` per ADR-0019, and writes the
machine-readable failure object of ADR-0026 from the public message.

Ten raise sites did not honour it. They raised `RuntimeError` for conditions
the project says cannot occur, in `region_generator`, `tracer`,
`topology_simplifier`, `nearest_palette_color` and the process quantization
executor. Reaching one produced, measured on the CLI:

    exit code 1                 not one of the four codes ADR-0026 defines
    empty standard output       where `--json` promises one failure object
    a Python traceback          naming installation paths, on standard error

which is three contract breaks at once, the last of them the disclosure
ADR-0019 exists to prevent. They are now `InvariantViolationError`, which is
attributed to the operation and reaches a caller as exit code 70.

`assert` is checked with them. It raises `AssertionError`, which the CLI does
not catch either, and it is removed entirely under `python -O`, so a check
written that way is not a check in a deployment that optimises.

`ValueError` and `TypeError` stay allowed. They validate programmer-facing
arguments in direct Python use, where the caller is a programmer holding a
traceback rather than a process reading an exit code. A branch that guards
against a state the project's own processing cannot produce is a different
thing and belongs in `InvariantViolationError`.

What this cannot see is an exception the package does not raise itself. A
symlink loop in the palette directory left `PaletteManager.get` as a
`RuntimeError` from `Path.resolve`, with no `raise` anywhere to find, and
reached a caller as a traceback and exit code 1 exactly like the ten below.
A standard-library call that raises outside `OSError` has to be caught where
it is made; this check does not substitute for reading what a call can raise.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tools.benchmark_region_complexity import REPOSITORY_ROOT

PACKAGE_DIRECTORY = REPOSITORY_ROOT / "src" / "pbn"

FORBIDDEN_EXCEPTIONS = frozenset(
    {
        "RuntimeError",
        "NotImplementedError",
        "AssertionError",
        "Exception",
        "BaseException",
    },
)
"""
Types that cannot represent project-internal operational failures.

None of them tells a caller whether the request or the operation failed, so
none of them can carry the attribution every interface derives from.
"""

PACKAGE_MODULES = tuple(
    sorted(
        PACKAGE_DIRECTORY.rglob(
            "*.py",
        ),
    ),
)


def raised_exception_name(
    node: ast.Raise,
) -> str | None:
    """
    Return the name of the exception a raise statement names, if any.

    A bare `raise` and a re-raise of a bound variable return `None`: both
    propagate something raised elsewhere rather than introducing a type.
    """
    if node.exc is None:
        return None

    if isinstance(node.exc, ast.Call):
        return getattr(
            node.exc.func,
            "id",
            None,
        )

    if isinstance(node.exc, ast.Name):
        return node.exc.id

    return None


def contract_breaking_statements(
    path: Path,
) -> tuple[tuple[int, str], ...]:
    """
    Return `(line, what)` for each statement that leaves the hierarchy.
    """
    tree = ast.parse(
        path.read_text(
            encoding="utf-8",
        ),
    )

    found: list[tuple[int, str]] = []

    for node in ast.walk(
        tree,
    ):
        if isinstance(node, ast.Assert):
            found.append(
                (
                    node.lineno,
                    "assert",
                ),
            )
            continue

        if not isinstance(node, ast.Raise):
            continue

        name = raised_exception_name(
            node,
        )

        if name in FORBIDDEN_EXCEPTIONS:
            found.append(
                (
                    node.lineno,
                    str(name),
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
def test_the_module_fails_inside_the_hierarchy(
    path: Path,
) -> None:
    breaking = contract_breaking_statements(
        path,
    )

    assert breaking == (), (
        f"{path.relative_to(PACKAGE_DIRECTORY)} fails outside the error "
        f"hierarchy, so the CLI cannot classify it: {breaking}"
    )


def test_the_package_modules_were_found() -> None:
    """
    Without this, an empty module list would leave every check above passing
    over nothing.
    """
    names = {path.name for path in PACKAGE_MODULES}

    assert "region_generator.py" in names
    assert "tracer.py" in names
    assert "topology_simplifier.py" in names

    assert len(PACKAGE_MODULES) > 50


@pytest.mark.parametrize(
    "statement",
    (
        'raise RuntimeError("cannot happen")',
        'raise NotImplementedError("later")',
        'assert value > 0, "cannot happen"',
    ),
    ids=(
        "runtime-error",
        "not-implemented",
        "assert",
    ),
)
def test_a_contract_breaking_statement_is_reported(
    statement: str,
    tmp_path: Path,
) -> None:
    """
    Why the check says something: it separates a project error from one the
    CLI cannot classify, rather than accepting both.
    """
    offending = tmp_path / "offending_module.py"

    offending.write_text(
        f"def check(value: int) -> None:\n    {statement}\n",
        encoding="utf-8",
    )

    assert (
        len(
            contract_breaking_statements(
                offending,
            ),
        )
        == 1
    )


def test_argument_validation_is_not_reported(
    tmp_path: Path,
) -> None:
    """
    `ValueError` at the direct Python boundary stays allowed, so the check has
    to leave it alone rather than pushing it into the project hierarchy too.
    """
    validating = tmp_path / "validating_module.py"

    validating.write_text(
        "def check(value: int) -> None:\n"
        "    if value < 0:\n"
        '        raise ValueError("value must not be negative")\n',
        encoding="utf-8",
    )

    assert (
        contract_breaking_statements(
            validating,
        )
        == ()
    )
