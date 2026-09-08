# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import (
    RGB,
    Lab,
    Palette,
    PaletteColor,
)


def test_palette() -> None:
    palette = Palette(
        id="polychromos60",
        manufacturer="Faber-Castell",
        display_name="Polychromos 60",
        version=1,
        colors=(
            PaletteColor(
                number=101,
                name="White",
                rgb=RGB(
                    red=255,
                    green=255,
                    blue=255,
                ),
                lab=Lab(
                    l=100.0,
                    a=0.0,
                    b=0.0,
                ),
            ),
        ),
    )

    assert palette.id == "polychromos60"
    assert palette.manufacturer == "Faber-Castell"
    assert palette.display_name == "Polychromos 60"
    assert palette.version == 1

    assert len(palette.colors) == 1

    assert palette.colors[0].number == 101
    assert palette.colors[0].name == "White"
    assert palette.colors[0].lab.l == 100.0
