# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
One number names one colour.

The number is the manufacturer's reference and, at the same time, the label
printed inside every region of that colour. `validate_palette_document`
checked that each one was a positive integer and never that two entries did
not share one, so a document could name two different paints with the same
number and nothing objected.

Measured before the rule existed, on a copy of `reference8-v1.json` whose
white and black were both given number one: the palette loaded, generation
finished with exit code zero, the template carried regions labelled `1`, and
the legend listed `White` and `Black` under that number. A painter reading a
`1` has no way to choose, and the two candidates are the furthest apart the
palette offers.

Checked at the document boundary rather than in the model, because that is
where a palette written by someone else enters the project. It is also the
only rule in that document no single entry can violate on its own, which is
why per-entry validation could not have found it.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from pbn.exceptions import PaletteNotFoundError
from pbn.infrastructure.palette_document import (
    PaletteDocumentError,
    validate_palette_document,
)
from pbn.infrastructure.palette_manager import PaletteManager

PALETTE_DIRECTORY = Path("palettes")

TEMPLATE = PALETTE_DIRECTORY / "reference8-v1.json"


def _document(
    numbers: tuple[int, ...],
) -> dict[str, Any]:
    """
    Return a valid document whose colours carry the given numbers.

    Everything else is held constant, so a rejection can only come from the
    numbers.
    """
    return {
        "metadata": {
            "id": "test",
            "manufacturer": "Test",
            "display_name": "Test Palette",
            "version": 1,
        },
        "colors": [
            {
                "number": number,
                "name": f"Colour {index}",
                "rgb": {
                    "red": index,
                    "green": index,
                    "blue": index,
                },
            }
            for index, number in enumerate(
                numbers,
            )
        ],
    }


@pytest.mark.parametrize(
    "numbers",
    (
        (1, 1),
        (1, 2, 1),
        (1, 2, 3, 4, 4),
        (7, 3, 9, 3, 5),
    ),
    ids=(
        "adjacent",
        "separated",
        "at-the-end",
        "in-the-middle",
    ),
)
def test_a_repeated_number_is_rejected(
    numbers: tuple[int, ...],
) -> None:
    with pytest.raises(
        PaletteDocumentError,
    ):
        validate_palette_document(
            _document(
                numbers,
            ),
        )


@pytest.mark.parametrize(
    "numbers",
    (
        (1,),
        (1, 2),
        (9, 4, 7, 1),
        (100, 200, 300),
    ),
    ids=(
        "one",
        "two",
        "unordered",
        "sparse",
    ),
)
def test_distinct_numbers_are_accepted(
    numbers: tuple[int, ...],
) -> None:
    """
    Why the rejection above says something: it separates a repeated number
    from any other property of these documents, rather than refusing both.
    """
    assert validate_palette_document(
        _document(
            numbers,
        ),
    )


def test_the_rejection_names_both_positions_and_the_number() -> None:
    """
    A palette author has to find the second entry, and a document may hold
    up to `MAXIMUM_COLOR_COUNT` of them.
    """
    with pytest.raises(
        PaletteDocumentError,
        match=r"colors\[3\]\.number repeats colors\[1\]\.number: 4\.",
    ):
        validate_palette_document(
            _document(
                (
                    9,
                    4,
                    7,
                    4,
                ),
            ),
        )


def test_a_palette_with_a_repeated_number_cannot_be_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The consequence the rule exists for, stated against the real loader.

    This document differs from the shipped one in a single field, and that
    is enough for the palette to stop being usable, which is the point: no
    document can be produced from it any more.
    """
    document = json.loads(
        TEMPLATE.read_text(
            encoding="utf-8",
        ),
    )

    document["metadata"]["id"] = "repeated"
    document["colors"][1]["number"] = document["colors"][0]["number"]

    directory = tmp_path / "palettes"

    directory.mkdir()

    (directory / "repeated-v1.json").write_text(
        json.dumps(
            document,
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(
        tmp_path,
    )

    manager = PaletteManager()

    assert manager.available() == ()

    with pytest.raises(
        PaletteNotFoundError,
    ):
        manager.get(
            "repeated",
            1,
        )


def test_the_same_palette_without_the_repetition_still_loads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Without this, a loader that refused the document for some other reason
    would satisfy the test above.
    """
    document = json.loads(
        TEMPLATE.read_text(
            encoding="utf-8",
        ),
    )

    document["metadata"]["id"] = "repeated"

    directory = tmp_path / "palettes"

    directory.mkdir()

    (directory / "repeated-v1.json").write_text(
        json.dumps(
            document,
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(
        tmp_path,
    )

    assert (
        PaletteManager()
        .get(
            "repeated",
            1,
        )
        .id
        == "repeated"
    )


def test_the_repository_ships_palettes() -> None:
    """
    A guard for the check below, which is worthless over an empty list.
    """
    assert (
        len(
            sorted(
                PALETTE_DIRECTORY.glob(
                    "*.json",
                ),
            ),
        )
        >= 5
    )


@pytest.mark.parametrize(
    "path",
    sorted(
        PALETTE_DIRECTORY.glob(
            "*.json",
        ),
    ),
    ids=lambda path: path.stem,
)
def test_no_shipped_palette_repeats_a_number(
    path: Path,
) -> None:
    """
    The rule is enforced on load, so this cannot fail while the shipped
    palettes load. It is kept because a failure here says which file and
    which number, where a loading failure says only that the file is
    invalid.
    """
    document = json.loads(
        path.read_text(
            encoding="utf-8",
        ),
    )

    numbers = [color["number"] for color in document["colors"]]

    assert len(
        set(
            numbers,
        ),
    ) == len(numbers)


def test_the_detector_finds_a_repetition_when_there_is_one() -> None:
    """
    The comparison above passes for a document with no colours at all, and
    for one this test file failed to read. Neither is the property.
    """
    document = json.loads(
        TEMPLATE.read_text(
            encoding="utf-8",
        ),
    )

    colors = deepcopy(
        document["colors"],
    )

    colors[1]["number"] = colors[0]["number"]

    numbers = [color["number"] for color in colors]

    assert len(
        set(
            numbers,
        ),
    ) < len(numbers)
