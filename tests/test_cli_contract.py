# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The command line interface is the integration contract of ADR-0026.

A front end in another language depends on the exit code and the shape
of the object on standard output. Both are interface: changing either
breaks a caller in a way no other test here would notice.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pbn import exceptions
from pbn.cli.contract import (
    EXIT_CONFIGURATION,
    EXIT_OPERATION,
    EXIT_REQUEST,
    EXIT_SUCCESS,
    exit_code_for,
)
from pbn.exceptions import PbnError

_BROKEN_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def _error_classes() -> tuple[type[PbnError], ...]:
    return tuple(
        value
        for value in vars(exceptions).values()
        if isinstance(value, type) and issubclass(value, PbnError)
    )


def test_the_exit_codes_are_distinct() -> None:
    """
    A caller distinguishes these, so they may not collide.
    """
    codes = {
        EXIT_SUCCESS,
        EXIT_REQUEST,
        EXIT_CONFIGURATION,
        EXIT_OPERATION,
    }

    assert len(codes) == 4


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_every_error_maps_to_a_defined_exit_code(
    error: type[PbnError],
) -> None:
    """
    Derived from the attribution of ADR-0019, so a new error type needs
    no change to the mapping.
    """
    code = exit_code_for(
        error("diagnostic"),
    )

    assert code in (
        EXIT_REQUEST,
        EXIT_CONFIGURATION,
        EXIT_OPERATION,
    )


def test_a_request_failure_maps_to_the_request_code() -> None:
    assert (
        exit_code_for(
            exceptions.CorruptedImageError("x"),
        )
        == EXIT_REQUEST
    )


def test_a_configuration_failure_is_separated_from_operation() -> None:
    """
    It names a different action than any other operational failure.
    """
    assert (
        exit_code_for(
            exceptions.ConfigurationError("x"),
        )
        == EXIT_CONFIGURATION
    )
    assert (
        exit_code_for(
            exceptions.PdfExportError("x"),
        )
        == EXIT_OPERATION
    )


def _run(
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pbn",
            "generate",
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )


def test_a_successful_run_reports_the_output(
    tmp_path: Path,
    small_input_image: Path,
) -> None:
    output = tmp_path / "out.pdf"
    completed = _run(
        "--input",
        str(small_input_image),
        "--output",
        str(output),
        "--config_file",
        "config/example.toml",
        "--json",
    )

    assert completed.returncode == EXIT_SUCCESS

    payload = json.loads(completed.stdout)

    assert payload == {
        "status": "succeeded",
        "output": str(output),
    }
    assert output.exists()


def test_a_failing_run_reports_the_error(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "broken.png"
    broken.write_bytes(_BROKEN_PNG)

    completed = _run(
        "--input",
        str(broken),
        "--output",
        str(tmp_path / "out.pdf"),
        "--config_file",
        "config/example.toml",
        "--json",
    )

    assert completed.returncode == EXIT_REQUEST

    payload = json.loads(completed.stdout)

    assert payload["status"] == "failed"
    assert payload["error"]["type"] == "CorruptedImageError"
    assert payload["error"]["caused_by_request"] is True
    assert payload["error"]["message"]


def test_a_failure_puts_no_path_on_standard_output(
    tmp_path: Path,
) -> None:
    """
    A front end that prints standard output cannot leak a path by doing
    so. The diagnostic message, which names the path, goes to standard
    error.
    """
    broken = tmp_path / "broken.png"
    broken.write_bytes(_BROKEN_PNG)

    completed = _run(
        "--input",
        str(broken),
        "--output",
        str(tmp_path / "out.pdf"),
        "--config_file",
        "config/example.toml",
        "--json",
    )

    assert str(tmp_path) not in completed.stdout
    assert str(tmp_path) in completed.stderr


def test_a_missing_configuration_is_its_own_code(
    tmp_path: Path,
    small_input_image: Path,
) -> None:
    completed = _run(
        "--input",
        str(small_input_image),
        "--output",
        str(tmp_path / "out.pdf"),
        "--config_file",
        str(tmp_path / "absent.toml"),
        "--json",
    )

    assert completed.returncode == EXIT_CONFIGURATION
    assert (
        json.loads(
            completed.stdout,
        )[
            "error"
        ]["type"]
        == "ConfigurationError"
    )


def test_standard_output_stays_empty_without_the_flag(
    tmp_path: Path,
    small_input_image: Path,
) -> None:
    """
    The machine-readable mode has to be asked for. Progress belongs on
    standard error either way.
    """
    completed = _run(
        "--input",
        str(small_input_image),
        "--output",
        str(tmp_path / "out.pdf"),
        "--config_file",
        "config/example.toml",
    )

    assert completed.returncode == EXIT_SUCCESS
    assert completed.stdout == ""
    assert completed.stderr


def test_standard_output_carries_exactly_one_object(
    tmp_path: Path,
    small_input_image: Path,
) -> None:
    """
    Progress must not end up on the stream the outcome is read from.
    """
    completed = _run(
        "--input",
        str(small_input_image),
        "--output",
        str(tmp_path / "out.pdf"),
        "--config_file",
        "config/example.toml",
        "--json",
    )

    assert (
        len(
            [line for line in completed.stdout.splitlines() if line.strip()],
        )
        == 1
    )
