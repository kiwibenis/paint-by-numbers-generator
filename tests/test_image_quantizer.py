# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from unittest.mock import patch

from pbn.color import DeltaE2000, ImageQuantizer
from pbn.color.nearest_palette_color import NearestPaletteColorFinder
from pbn.color.rgb_to_lab import RgbToLabConverter
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
    QuantizedImage,
)


def test_quantize_single_black_pixel() -> None:
    image = InputImage.from_rows(
        (
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
            ),
        )
    )

    black = PaletteColor(
        number=1,
        name="Black",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(black,),
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    result = quantizer.quantize(
        image,
        palette,
    )

    assert isinstance(result, QuantizedImage)

    assert result.width == 1
    assert result.height == 1

    assert tuple(result.rows()) == ((black,),)


def test_quantize_two_by_two_image() -> None:
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    white = RGB(
        red=255,
        green=255,
        blue=255,
    )

    image = InputImage.from_rows(
        (
            (
                black,
                white,
            ),
            (
                white,
                black,
            ),
        )
    )

    black_palette_color = PaletteColor(
        number=1,
        name="Black",
        rgb=black,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    white_palette_color = PaletteColor(
        number=2,
        name="White",
        rgb=white,
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            black_palette_color,
            white_palette_color,
        ),
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    result = quantizer.quantize(
        image,
        palette,
    )

    assert isinstance(result, QuantizedImage)

    assert result.width == 2
    assert result.height == 2

    assert tuple(result.rows()) == (
        (
            black_palette_color,
            white_palette_color,
        ),
        (
            white_palette_color,
            black_palette_color,
        ),
    )


def test_collect_unique_colors_preserves_first_seen_order() -> None:
    first = RGB(
        red=10,
        green=20,
        blue=30,
    )

    second = RGB(
        red=40,
        green=50,
        blue=60,
    )

    third = RGB(
        red=70,
        green=80,
        blue=90,
    )

    image = InputImage.from_rows(
        (
            (
                first,
                second,
                first,
            ),
            (
                third,
                second,
                RGB(
                    red=10,
                    green=20,
                    blue=30,
                ),
            ),
        )
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    result = quantizer.collect_unique_colors(
        image,
    )

    assert result == (
        first,
        second,
        third,
    )


def test_quantize_colors_preserves_chunk_order() -> None:
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    white = RGB(
        red=255,
        green=255,
        blue=255,
    )

    black_palette_color = PaletteColor(
        number=1,
        name="Black",
        rgb=black,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    white_palette_color = PaletteColor(
        number=2,
        name="White",
        rgb=white,
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            black_palette_color,
            white_palette_color,
        ),
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    result = quantizer.quantize_colors(
        (
            white,
            black,
        ),
        palette,
    )

    assert result == (
        (
            white,
            white_palette_color,
        ),
        (
            black,
            black_palette_color,
        ),
    )


def test_reconstruct_quantized_image_uses_color_matches() -> None:
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    white = RGB(
        red=255,
        green=255,
        blue=255,
    )

    image = InputImage.from_rows(
        (
            (
                black,
                white,
            ),
            (
                white,
                black,
            ),
        )
    )

    black_palette_color = PaletteColor(
        number=1,
        name="Black",
        rgb=black,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    white_palette_color = PaletteColor(
        number=2,
        name="White",
        rgb=white,
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    result = quantizer.reconstruct_quantized_image(
        image,
        (
            (
                black,
                black_palette_color,
            ),
            (
                white,
                white_palette_color,
            ),
        ),
    )

    assert result == QuantizedImage.from_rows(
        (
            (
                black_palette_color,
                white_palette_color,
            ),
            (
                white_palette_color,
                black_palette_color,
            ),
        )
    )


def test_quantize_reuses_result_for_repeated_rgb_values() -> None:
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    white = RGB(
        red=255,
        green=255,
        blue=255,
    )

    image = InputImage.from_rows(
        (
            (
                black,
                white,
            ),
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
                RGB(
                    red=255,
                    green=255,
                    blue=255,
                ),
            ),
        )
    )

    black_palette_color = PaletteColor(
        number=1,
        name="Black",
        rgb=black,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    white_palette_color = PaletteColor(
        number=2,
        name="White",
        rgb=white,
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            black_palette_color,
            white_palette_color,
        ),
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    with (
        patch.object(
            RgbToLabConverter,
            "convert",
            autospec=True,
            wraps=RgbToLabConverter.convert,
        ) as convert,
        patch.object(
            NearestPaletteColorFinder,
            "find",
            autospec=True,
            wraps=NearestPaletteColorFinder.find,
        ) as find,
    ):
        result = quantizer.quantize(
            image,
            palette,
        )

    assert tuple(result.rows()) == (
        (
            black_palette_color,
            white_palette_color,
        ),
        (
            black_palette_color,
            white_palette_color,
        ),
    )

    assert convert.call_count == 2
    assert find.call_count == 2


def test_quantize_cache_is_scoped_to_single_call() -> None:
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    image = InputImage.from_rows(((black,),))

    first_color = PaletteColor(
        number=1,
        name="First",
        rgb=black,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    second_color = PaletteColor(
        number=2,
        name="Second",
        rgb=black,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    first_palette = Palette(
        id="first",
        manufacturer="Test",
        display_name="First",
        version=1,
        colors=(first_color,),
    )

    second_palette = Palette(
        id="second",
        manufacturer="Test",
        display_name="Second",
        version=1,
        colors=(second_color,),
    )

    quantizer = ImageQuantizer(
        color_distance=DeltaE2000(),
    )

    first_result = quantizer.quantize(
        image,
        first_palette,
    )

    second_result = quantizer.quantize(
        image,
        second_palette,
    )

    assert tuple(first_result.rows()) == ((first_color,),)

    assert tuple(second_result.rows()) == ((second_color,),)
