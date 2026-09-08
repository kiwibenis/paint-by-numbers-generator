# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.models import RGB, InputImage, Lab, PaletteColor, QuantizedImage


def _rgb(value: int) -> RGB:
    return RGB(
        red=value % 256,
        green=(value + 1) % 256,
        blue=(value + 2) % 256,
    )


def _palette_color(number: int) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"C{number}",
        rgb=_rgb(number),
        lab=Lab(
            l=float(number),
            a=0.0,
            b=0.0,
        ),
    )


_ROWS = (
    (_rgb(10), _rgb(20), _rgb(30)),
    (_rgb(40), _rgb(50), _rgb(60)),
)


def test_input_image_round_trips_through_rows() -> None:
    image = InputImage.from_rows(_ROWS)

    assert tuple(image.rows()) == _ROWS
    assert image.width == 3
    assert image.height == 2


def test_input_image_stores_three_bytes_per_pixel() -> None:
    image = InputImage.from_rows(_ROWS)

    assert isinstance(image.pixels, bytes)
    assert len(image.pixels) == 3 * 2 * 3


def test_input_image_accessors_match_the_rows() -> None:
    image = InputImage.from_rows(_ROWS)

    for y, row in enumerate(_ROWS):
        assert image.rows_at(y) == row

        for x, color in enumerate(row):
            assert image.rgb_at(x, y) == color


def test_input_image_rejects_data_that_does_not_match_its_size() -> None:
    with pytest.raises(ValueError):
        InputImage(
            width=2,
            height=2,
            pixels=b"\x00\x01\x02",
        )


def test_input_image_rejects_ragged_rows() -> None:
    with pytest.raises(ValueError):
        InputImage.from_rows(
            (
                (_rgb(1), _rgb(2)),
                (_rgb(3),),
            ),
        )


def test_empty_input_image_is_allowed() -> None:
    image = InputImage.from_rows(())

    assert image.width == 0
    assert image.height == 0
    assert image.pixels == b""


_QUANTIZED_ROWS = (
    (_palette_color(1), _palette_color(2), _palette_color(1)),
    (_palette_color(2), _palette_color(2), _palette_color(1)),
)


def test_quantized_image_round_trips_through_rows() -> None:
    image = QuantizedImage.from_rows(_QUANTIZED_ROWS)

    assert tuple(image.rows()) == _QUANTIZED_ROWS


def test_quantized_image_stores_one_index_per_pixel() -> None:
    image = QuantizedImage.from_rows(_QUANTIZED_ROWS)

    assert isinstance(image.indices, bytes)
    assert len(image.indices) == 6


def test_quantized_image_keeps_each_color_once() -> None:
    image = QuantizedImage.from_rows(_QUANTIZED_ROWS)

    assert len(image.palette) == 2


def test_quantized_image_accessors_match_the_rows() -> None:
    image = QuantizedImage.from_rows(_QUANTIZED_ROWS)

    for y, row in enumerate(_QUANTIZED_ROWS):
        assert image.rows_at(y) == row

        for x, color in enumerate(row):
            assert image.color_at(x, y) == color
            assert image.palette[image.index_at(x, y)] == color


def test_quantized_image_rejects_data_that_does_not_match_its_size() -> None:
    with pytest.raises(ValueError):
        QuantizedImage(
            width=2,
            height=2,
            palette=(_palette_color(1),),
            indices=b"\x00",
        )


def test_quantized_image_rejects_an_oversized_palette() -> None:
    """
    One byte per pixel cannot address more than 256 palette entries.
    """
    with pytest.raises(ValueError):
        QuantizedImage(
            width=1,
            height=1,
            palette=tuple(_palette_color(number) for number in range(257)),
            indices=b"\x00",
        )


def test_quantized_image_accepts_the_largest_supported_palette() -> None:
    image = QuantizedImage(
        width=1,
        height=1,
        palette=tuple(_palette_color(number) for number in range(256)),
        indices=b"\xff",
    )

    assert image.color_at(0, 0).number == 255
