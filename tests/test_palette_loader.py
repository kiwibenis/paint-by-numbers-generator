# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from pbn.exceptions import InvalidPaletteError
from pbn.infrastructure import (
    PaletteLoader,
    load_palette,
)


def test_reject_palette_id_mismatch(tmp_path: Path) -> None:
    palette_file = tmp_path / "faberCastellPolychromos60-v1.json"

    palette_file.write_text(
        """
{
    "metadata": {
        "id": "reference8",
        "manufacturer": "Faber-Castell",
        "display_name": "Polychromos 60",
        "version": 1
    },
    "colors": []
}
""",
        encoding="utf-8",
    )

    loader = PaletteLoader()

    with pytest.raises(InvalidPaletteError):
        loader.load(
            palette_file,
        )


def test_reject_palette_version_mismatch(tmp_path: Path) -> None:
    palette_file = tmp_path / "faberCastellPolychromos60-v1.json"

    palette_file.write_text(
        """
{
    "metadata": {
        "id": "faberCastellPolychromos60",
        "manufacturer": "Faber-Castell",
        "display_name": "Polychromos 60",
        "version": 2
    },
    "colors": []
}
""",
        encoding="utf-8",
    )

    loader = PaletteLoader()

    with pytest.raises(InvalidPaletteError):
        loader.load(
            palette_file,
        )


def test_load_faber_castell_polychromos60_palette() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos60-v1.json"),
    )

    assert palette.id == "faberCastellPolychromos60"
    assert palette.manufacturer == "Faber-Castell"
    assert palette.display_name == "Polychromos 60"
    assert palette.version == 1

    assert len(palette.colors) == 60

    color = palette.colors[0]

    assert color.number == 101
    assert color.name == "White"

    assert color.rgb.red == 245
    assert color.rgb.green == 247
    assert color.rgb.blue == 251


def test_load_faber_castell_polychromos60_contains_60_unique_colors() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos60-v1.json"),
    )

    numbers = tuple(color.number for color in palette.colors)

    assert len(numbers) == 60
    assert len(set(numbers)) == 60

    assert numbers[0] == 101
    assert numbers[-1] == 283

    coral = next(color for color in palette.colors if color.number == 131)

    assert coral.name == "Coral"
    assert coral.rgb.red == 221
    assert coral.rgb.green == 123
    assert coral.rgb.blue == 137

    cold_grey_iv = next(color for color in palette.colors if color.number == 233)

    assert cold_grey_iv.name == "Cold Grey IV"
    assert cold_grey_iv.rgb.red == 142
    assert cold_grey_iv.rgb.green == 148
    assert cold_grey_iv.rgb.blue == 152


def test_load_faber_castell_polychromos120_palette() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos120-v1.json"),
    )

    assert palette.id == "faberCastellPolychromos120"
    assert palette.manufacturer == "Faber-Castell"
    assert palette.display_name == "Polychromos 120"
    assert palette.version == 1

    assert len(palette.colors) == 120

    color = palette.colors[0]

    assert color.number == 101
    assert color.name == "White"

    assert color.rgb.red == 245
    assert color.rgb.green == 247
    assert color.rgb.blue == 251


def test_load_faber_castell_polychromos120_contains_120_unique_colors() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos120-v1.json"),
    )

    numbers = tuple(color.number for color in palette.colors)

    assert len(numbers) == 120
    assert len(set(numbers)) == 120

    assert numbers[0] == 101
    assert numbers[-1] == 283

    ivory = next(color for color in palette.colors if color.number == 103)

    assert ivory.name == "Ivory"
    assert ivory.rgb.red == 242
    assert ivory.rgb.green == 244
    assert ivory.rgb.blue == 230

    light_chrome_yellow = next(color for color in palette.colors if color.number == 106)

    assert light_chrome_yellow.name == "Light Chrome Yellow"
    assert light_chrome_yellow.rgb.red == 253
    assert light_chrome_yellow.rgb.green == 248
    assert light_chrome_yellow.rgb.blue == 97

    burnt_umber = next(color for color in palette.colors if color.number == 280)

    assert burnt_umber.name == "Burnt Umber"
    assert burnt_umber.rgb.red == 117
    assert burnt_umber.rgb.green == 85
    assert burnt_umber.rgb.blue == 74


def test_faber_castell_polychromos120_preserves_60_colors() -> None:
    polychromos60 = load_palette(
        Path("palettes/faberCastellPolychromos60-v1.json"),
    )
    polychromos120 = load_palette(
        Path("palettes/faberCastellPolychromos120-v1.json"),
    )

    polychromos120_by_number = {color.number: color for color in polychromos120.colors}

    for color in polychromos60.colors:
        matching_color = polychromos120_by_number[color.number]

        assert matching_color.name == color.name
        assert matching_color.rgb == color.rgb


def test_amsterdam_separates_the_three_corrected_pairs() -> None:
    """
    Three pairs of colours shared one RGB value before publication.

    A pair with one value is one colour to the quantizer, so the second
    number could never appear on a template. Asserted on the shipped values
    rather than on the difference between them, because the numbers
    themselves are what
    `docs/reference-data/amsterdamStandardRoyalTalents.md` records and
    derives.
    """
    palette = load_palette(
        Path("palettes/amsterdamStandardRoyalTalents90-v1.json"),
    )

    by_number = {color.number: color for color in palette.colors}

    corrected = {
        105: (255, 255, 255),
        104: (251, 250, 250),
        275: (255, 237, 0),
        272: (255, 232, 0),
        398: (189, 53, 52),
        399: (128, 42, 48),
    }

    for number, rgb in corrected.items():
        color = by_number[number]

        assert (
            color.rgb.red,
            color.rgb.green,
            color.rgb.blue,
        ) == rgb, number


def test_amsterdam_uses_the_chart_name_for_267() -> None:
    """
    The English column of the published chart reads `Azo yellow`. An earlier
    revision carried `Azo Yellow Lemon`, and that qualifier appears only in
    the Dutch and German columns.

    Asserted for every size, because a name that differs between two files of
    one palette family would be the same class of defect as the duplicate
    values.
    """
    for size in (24, 36, 48, 90):
        palette = load_palette(
            Path(f"palettes/amsterdamStandardRoyalTalents{size}-v1.json"),
        )

        assert (
            next(color.name for color in palette.colors if color.number == 267)
            == "Azo Yellow"
        ), size


@pytest.mark.parametrize(
    ("palette_id", "display_name", "expected_color_count"),
    (
        (
            "amsterdamStandardRoyalTalents24",
            "Amsterdam Standard Series 24",
            24,
        ),
        (
            "amsterdamStandardRoyalTalents36",
            "Amsterdam Standard Series 36",
            36,
        ),
        (
            "amsterdamStandardRoyalTalents48",
            "Amsterdam Standard Series 48",
            48,
        ),
        (
            "amsterdamStandardRoyalTalents90",
            "Amsterdam Standard Series 90",
            90,
        ),
    ),
)
def test_load_amsterdam_standard_series_palette(
    palette_id: str,
    display_name: str,
    expected_color_count: int,
) -> None:
    palette = load_palette(
        Path(f"palettes/{palette_id}-v1.json"),
    )

    assert palette.id == palette_id
    assert palette.manufacturer == "Royal Talens"
    assert palette.display_name == display_name
    assert palette.version == 1

    numbers = tuple(color.number for color in palette.colors)

    assert len(numbers) == expected_color_count
    assert len(set(numbers)) == expected_color_count

    titanium_white = next(color for color in palette.colors if color.number == 105)

    assert titanium_white.name == "Titanium White"
    assert titanium_white.rgb.red == 255
    assert titanium_white.rgb.green == 255
    assert titanium_white.rgb.blue == 255


def test_amsterdam_standard_series_palettes_preserve_shared_colors() -> None:
    palette_ids = (
        "amsterdamStandardRoyalTalents24",
        "amsterdamStandardRoyalTalents36",
        "amsterdamStandardRoyalTalents48",
        "amsterdamStandardRoyalTalents90",
    )

    palettes = tuple(
        load_palette(
            Path(f"palettes/{palette_id}-v1.json"),
        )
        for palette_id in palette_ids
    )

    for smaller_palette, larger_palette in pairwise(palettes):
        larger_by_number = {color.number: color for color in larger_palette.colors}

        for color in smaller_palette.colors:
            matching_color = larger_by_number[color.number]

            assert matching_color.name == color.name
            assert matching_color.rgb == color.rgb
