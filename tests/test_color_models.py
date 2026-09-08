# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
)


def test_rgb() -> None:
    rgb = RGB(
        red=255,
        green=128,
        blue=64,
    )

    assert rgb.red == 255
    assert rgb.green == 128
    assert rgb.blue == 64

    assert rgb.as_tuple() == (
        255,
        128,
        64,
    )


def test_lab() -> None:
    lab = Lab(
        l=52.1,
        a=10.4,
        b=-5.2,
    )

    assert lab.l == 52.1
    assert lab.a == 10.4
    assert lab.b == -5.2

    assert lab.as_tuple() == (
        52.1,
        10.4,
        -5.2,
    )


def test_palette_color() -> None:
    color = PaletteColor(
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
    )

    assert color.number == 101
    assert color.name == "White"

    assert color.rgb.red == 255
    assert color.rgb.green == 255
    assert color.rgb.blue == 255

    assert color.lab.l == 100.0
    assert color.lab.a == 0.0
    assert color.lab.b == 0.0
