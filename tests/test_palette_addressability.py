# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
One index byte bounds the palette, and that bound has three homes.

`MAXIMUM_PALETTE_SIZE` is the storage invariant: a quantized image keeps
one palette index per pixel, and a byte addresses 256 entries. The
document schema and the executor port both depend on it. They used to
repeat the number instead of deriving it, and nothing connected them.

The failure that motivated these tests: an image reaching more than 256
palette colors produced `ValueError: bytes must be in range(0, 256)`
after the whole quantization had run. The existing check on
`QuantizedImage` never fired, because the index array was built first.
"""

from __future__ import annotations

import pytest

from pbn.application.quantization_executor_port import (
    ensure_addressable_palette,
)
from pbn.color.delta_e_76 import DeltaE76
from pbn.color.quantizer import ImageQuantizer
from pbn.color.rgb_to_lab import RgbToLabConverter
from pbn.exceptions import QuantizationPaletteError
from pbn.infrastructure.palette_document import MAXIMUM_COLOR_COUNT
from pbn.models import (
    MAXIMUM_PALETTE_SIZE,
    RGB,
    InputImage,
    Palette,
    PaletteColor,
    QuantizedImage,
)

_CONVERT = RgbToLabConverter().convert


def _distinct_colors(
    count: int,
) -> tuple[RGB, ...]:
    return tuple(
        RGB(
            red=index % 32 * 8,
            green=index // 32 * 25 % 256,
            blue=index * 3 % 256,
        )
        for index in range(count)
    )


def _palette_of(
    colors: tuple[RGB, ...],
) -> Palette:
    return Palette(
        id="generated",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=tuple(
            PaletteColor(
                number=index + 1,
                name=f"C{index}",
                rgb=color,
                lab=_CONVERT(color),
            )
            for index, color in enumerate(colors)
        ),
    )


def _image_of(
    colors: tuple[RGB, ...],
    width: int = 20,
) -> InputImage:
    height = len(colors) // width

    return InputImage.from_rows(
        tuple(
            tuple(colors[y * width + x] for x in range(width)) for y in range(height)
        ),
    )


def test_the_document_bound_derives_from_the_storage_invariant() -> None:
    """
    Two constants with the same value and no link is the failure mode.
    """
    assert MAXIMUM_COLOR_COUNT == MAXIMUM_PALETTE_SIZE


def test_quantizing_beyond_the_bound_names_the_cause() -> None:
    """
    The real path, not the constructor.

    This produced a bare range error out of `bytes` before, after the
    whole quantization had been paid for.
    """
    colors = _distinct_colors(
        (MAXIMUM_PALETTE_SIZE + 44) // 20 * 20,
    )

    with pytest.raises(QuantizationPaletteError) as caught:
        ImageQuantizer(
            color_distance=DeltaE76(),
        ).quantize(
            _image_of(colors),
            _palette_of(colors),
        )

    assert str(MAXIMUM_PALETTE_SIZE) in caught.value.diagnostic_message
    assert caught.value.caused_by_request


def test_quantizing_at_the_bound_is_accepted() -> None:
    colors = _distinct_colors(
        MAXIMUM_PALETTE_SIZE,
    )

    quantized = ImageQuantizer(
        color_distance=DeltaE76(),
    ).quantize(
        _image_of(colors, width=16),
        _palette_of(colors),
    )

    assert len(quantized.palette) <= MAXIMUM_PALETTE_SIZE


def test_the_port_rejects_an_unaddressable_palette_before_the_work() -> None:
    with pytest.raises(QuantizationPaletteError):
        ensure_addressable_palette(
            _palette_of(
                _distinct_colors(
                    MAXIMUM_PALETTE_SIZE + 1,
                ),
            ),
        )


def test_the_port_accepts_a_palette_at_the_bound() -> None:
    ensure_addressable_palette(
        _palette_of(
            _distinct_colors(
                MAXIMUM_PALETTE_SIZE,
            ),
        ),
    )


def test_building_rows_beyond_the_bound_names_the_cause() -> None:
    """
    `from_rows` built the index array before checking, so it failed the
    same way the quantizer did.
    """
    colors = _distinct_colors(
        MAXIMUM_PALETTE_SIZE + 20,
    )
    palette_colors = tuple(
        PaletteColor(
            number=index + 1,
            name=f"C{index}",
            rgb=color,
            lab=_CONVERT(color),
        )
        for index, color in enumerate(colors)
    )

    rows = tuple(
        tuple(palette_colors[y * 20 + x] for x in range(20))
        for y in range(len(palette_colors) // 20)
    )

    with pytest.raises(ValueError) as caught:
        QuantizedImage.from_rows(rows)

    assert "palette entries" in str(caught.value)
