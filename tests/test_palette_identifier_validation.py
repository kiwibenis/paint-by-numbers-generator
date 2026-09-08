# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.exceptions import PaletteNotFoundError
from pbn.infrastructure.palette_file_name import (
    PaletteIdentity,
    is_valid_identity,
)
from pbn.infrastructure.palette_manager import PaletteManager


def test_known_palette_is_loaded() -> None:
    palette = PaletteManager().get(
        "reference8",
        1,
    )

    assert palette.id == "reference8"


@pytest.mark.parametrize(
    "palette_id",
    [
        "reference8",
        "myPalette",
        "mypalette",
        "palette120",
    ],
)
def test_alphanumeric_palette_identifiers_are_valid(
    palette_id: str,
) -> None:
    assert is_valid_identity(
        PaletteIdentity(
            palette_id=palette_id,
            version=1,
        ),
    )


@pytest.mark.parametrize(
    "palette_id",
    [
        "",
        "..",
        "../../etc/passwd",
        "..\\..\\windows",
        "reference8/../../secret",
        "/etc/passwd",
        "C:\\Windows\\system",
        "reference 8",
        "reference8.json",
        "reference8\x00",
        "reference-8",
        "my-palette",
        "palette-120",
        "reference_8",
        "my_palette",
        "palette_120",
        "a" * 65,
    ],
)
def test_identifiers_outside_the_accepted_character_set_are_rejected(
    palette_id: str,
) -> None:
    with pytest.raises(PaletteNotFoundError):
        PaletteManager().get(
            palette_id,
            1,
        )


def test_absolute_identifier_does_not_escape_the_directory(
    tmp_path: Path,
) -> None:
    """
    Path concatenation is not a containment control.

    An absolute component replaces the base directory entirely, so the
    identifier must be rejected before the path is built.
    """
    outside = tmp_path / "outside-v1.json"
    outside.write_text("{}")

    with pytest.raises(PaletteNotFoundError):
        PaletteManager().get(
            str(tmp_path / "outside"),
            1,
        )


@pytest.mark.parametrize(
    "version",
    [
        0,
        -1,
        10_000,
    ],
)
def test_versions_outside_the_accepted_range_are_rejected(
    version: int,
) -> None:
    with pytest.raises(PaletteNotFoundError):
        PaletteManager().get(
            "reference8",
            version,
        )


def test_rejection_does_not_reveal_whether_a_file_exists() -> None:
    """
    A caller must not learn existence from the error it receives.
    """
    missing = _message_for(
        "doesnotexist",
        1,
    )
    traversal = _message_for(
        "../../etc/passwd",
        1,
    )

    assert missing == traversal


def _message_for(
    palette_id: str,
    version: int,
) -> str:
    try:
        PaletteManager().get(
            palette_id,
            version,
        )
    except PaletteNotFoundError as error:
        return str(error)

    raise AssertionError(
        "Expected the palette to be rejected.",
    )
