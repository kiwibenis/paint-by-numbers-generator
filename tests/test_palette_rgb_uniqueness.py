# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Two colours with one RGB value are one colour to the quantizer.

A palette entry that shares its RGB value with another entry can never be
selected: the nearest-colour search is a tie and the earlier entry wins every
time, so the second number can never appear on a generated template while
still being printed in the legend. A painter buying that tube would never use
it, and the palette offers fewer usable colours than it claims.

Three pairs in the Amsterdam palettes were in exactly that state. They were
corrected before publication, and `docs/reference-data/`
`amsterdamStandardRoyalTalents.md` records how the corrected values were
derived. This module keeps the property from coming back.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest

from pbn.color import ImageQuantizer
from pbn.color.delta_e_2000 import DeltaE2000
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import InputImage

PALETTE_DIRECTORY = Path("palettes")

Rgb = tuple[int, int, int]

PREVIOUSLY_COLLIDING = {
    105: (255, 255, 255),
    104: (251, 250, 250),
    275: (255, 237, 0),
    272: (255, 232, 0),
    398: (189, 53, 52),
    399: (128, 42, 48),
}
"""
The three pairs that shared a value, and the values they carry now.

`398 Naphthol Red Light` against `399 Naphthol Red Deep` is the light and the
deep variant of one paint. `272 Transparent Yellow Medium` against
`275 Primary Yellow` uses different pigments, `PY128` against `PY3` and
`PY74`. `104 Zinc White` and `105 Titanium White` differ mainly in opacity.
None of the three was a duplicate the manufacturer intends.
"""


def palette_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            PALETTE_DIRECTORY.glob(
                "*.json",
            ),
        ),
    )


def duplicate_rgb_values(
    colors: list[dict[str, object]],
) -> dict[Rgb, tuple[int, ...]]:
    by_rgb: dict[Rgb, list[int]] = defaultdict(
        list,
    )

    for color in colors:
        channels = color["rgb"]

        assert isinstance(
            channels,
            dict,
        )

        by_rgb[
            (
                channels["red"],
                channels["green"],
                channels["blue"],
            )
        ].append(
            color["number"],  # type: ignore[arg-type]
        )

    return {
        rgb: tuple(
            sorted(
                numbers,
            ),
        )
        for rgb, numbers in by_rgb.items()
        if len(numbers) > 1
    }


def colors_of(
    palette_file: Path,
) -> list[dict[str, object]]:
    document = json.loads(
        palette_file.read_text(
            encoding="utf-8",
        ),
    )

    colors = document["colors"]

    assert isinstance(
        colors,
        list,
    )

    return colors


def test_the_repository_ships_palettes() -> None:
    """
    Without this, an empty directory would satisfy the check below.
    """
    assert palette_files()


@pytest.mark.parametrize(
    "palette_file",
    palette_files(),
    ids=lambda path: path.name,
)
def test_no_shipped_palette_contains_a_duplicate_rgb_value(
    palette_file: Path,
) -> None:
    assert (
        duplicate_rgb_values(
            colors_of(
                palette_file,
            ),
        )
        == {}
    )


def test_the_detector_finds_a_duplicate_when_there_is_one() -> None:
    """
    Without this, a detector that always returned nothing would satisfy every
    case above.
    """
    assert duplicate_rgb_values(
        [
            {
                "number": 1,
                "rgb": {"red": 1, "green": 2, "blue": 3},
            },
            {
                "number": 2,
                "rgb": {"red": 9, "green": 9, "blue": 9},
            },
            {
                "number": 3,
                "rgb": {"red": 1, "green": 2, "blue": 3},
            },
        ],
    ) == {
        (1, 2, 3): (1, 3),
    }


def test_each_previously_colliding_color_is_reachable() -> None:
    """
    The property the file check cannot show.

    Distinct values in the document are necessary but not sufficient: what
    matters is that the quantizer can actually return each number. Asserted
    against the real quantizer and the real palette.
    """
    palette = load_palette(
        PALETTE_DIRECTORY / "amsterdamStandardRoyalTalents90-v1.json",
    )

    quantized = ImageQuantizer(
        color_distance=DeltaE2000(),
    ).quantize(
        InputImage(
            width=len(PREVIOUSLY_COLLIDING),
            height=1,
            pixels=b"".join(
                bytes(
                    rgb,
                )
                for rgb in PREVIOUSLY_COLLIDING.values()
            ),
        ),
        palette,
    )

    assert [
        quantized.color_at(
            x,
            0,
        ).number
        for x in range(
            len(PREVIOUSLY_COLLIDING),
        )
    ] == list(
        PREVIOUSLY_COLLIDING,
    )
