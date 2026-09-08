# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pbn import exceptions
from pbn.exceptions import PbnError

_PATH_LIKE = re.compile(
    r"[/\\]|\.[a-z]{2,4}\b|[A-Za-z]:",
)


def _error_classes() -> tuple[type[PbnError], ...]:
    return tuple(
        sorted(
            (
                value
                for value in vars(exceptions).values()
                if isinstance(value, type) and issubclass(value, PbnError)
            ),
            key=lambda error: error.__name__,
        ),
    )


def test_every_error_class_is_discovered() -> None:
    """
    A guard for the guards below, which are worthless if empty.
    """
    assert len(_error_classes()) >= 14


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_every_error_declares_its_public_message(
    error: type[PbnError],
) -> None:
    """
    Inheriting the base message means the decision was never made.
    """
    if error is PbnError:
        return

    assert "public_message" in vars(error)


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_every_error_declares_its_attribution(
    error: type[PbnError],
) -> None:
    if error is PbnError:
        return

    assert "caused_by_request" in vars(error)


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_no_public_message_looks_like_a_path(
    error: type[PbnError],
) -> None:
    assert not _PATH_LIKE.search(
        error.public_message,
    )


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_no_public_message_carries_a_placeholder(
    error: type[PbnError],
) -> None:
    """
    A message that cannot be interpolated cannot leak a value.
    """
    assert "{" not in error.public_message
    assert "%" not in error.public_message


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_the_diagnostic_message_is_what_was_raised(
    error: type[PbnError],
) -> None:
    instance = error(
        "Detail naming /var/lib/pbn/input.png.",
    )

    assert instance.diagnostic_message == ("Detail naming /var/lib/pbn/input.png.")


@pytest.mark.parametrize(
    "error",
    _error_classes(),
    ids=lambda error: error.__name__,
)
def test_the_public_message_does_not_repeat_the_diagnostic_one(
    error: type[PbnError],
) -> None:
    instance = error(
        "Detail naming /var/lib/pbn/input.png.",
    )

    assert "/var/lib/pbn" not in instance.public_message


def test_no_source_file_raises_the_base_error() -> None:
    """
    Raising the base class would inherit the decision instead of making it.
    """
    offenders = [
        path
        for path in sorted(
            Path("src").rglob("*.py"),
        )
        if "raise PbnError("
        in path.read_text(
            encoding="utf-8",
        )
    ]

    assert offenders == []
