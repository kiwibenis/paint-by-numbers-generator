# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.color import RgbToXyzConverter
from pbn.models import RGB


def test_black() -> None:
    converter = RgbToXyzConverter()

    xyz = converter.convert(
        RGB(
            red=0,
            green=0,
            blue=0,
        )
    )

    assert xyz.x == pytest.approx(0.0)
    assert xyz.y == pytest.approx(0.0)
    assert xyz.z == pytest.approx(0.0)


def test_white() -> None:
    converter = RgbToXyzConverter()

    xyz = converter.convert(
        RGB(
            red=255,
            green=255,
            blue=255,
        )
    )

    assert xyz.x == pytest.approx(
        0.95047,
        abs=0.001,
    )
    assert xyz.y == pytest.approx(
        1.00000,
        abs=0.001,
    )
    assert xyz.z == pytest.approx(
        1.08883,
        abs=0.001,
    )


def test_red() -> None:
    converter = RgbToXyzConverter()

    xyz = converter.convert(
        RGB(
            red=255,
            green=0,
            blue=0,
        )
    )

    assert xyz.x == pytest.approx(
        0.41246,
        abs=0.001,
    )
    assert xyz.y == pytest.approx(
        0.21267,
        abs=0.001,
    )
    assert xyz.z == pytest.approx(
        0.01933,
        abs=0.001,
    )


def test_green() -> None:
    converter = RgbToXyzConverter()

    xyz = converter.convert(
        RGB(
            red=0,
            green=255,
            blue=0,
        )
    )

    assert xyz.x == pytest.approx(
        0.35758,
        abs=0.001,
    )
    assert xyz.y == pytest.approx(
        0.71515,
        abs=0.001,
    )
    assert xyz.z == pytest.approx(
        0.11919,
        abs=0.001,
    )


def test_blue() -> None:
    converter = RgbToXyzConverter()

    xyz = converter.convert(
        RGB(
            red=0,
            green=0,
            blue=255,
        )
    )

    assert xyz.x == pytest.approx(
        0.18044,
        abs=0.001,
    )
    assert xyz.y == pytest.approx(
        0.07218,
        abs=0.001,
    )
    assert xyz.z == pytest.approx(
        0.95030,
        abs=0.001,
    )


def test_mixed_color() -> None:
    converter = RgbToXyzConverter()

    xyz = converter.convert(
        RGB(
            red=12,
            green=128,
            blue=240,
        )
    )

    assert xyz.x == pytest.approx(
        0.23593,
        abs=0.001,
    )
    assert xyz.y == pytest.approx(
        0.21805,
        abs=0.001,
    )
    assert xyz.z == pytest.approx(
        0.85386,
        abs=0.001,
    )
