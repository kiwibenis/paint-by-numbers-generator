# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.color import DeltaE2000, ImageQuantizer
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
    QuantizedImage,
)
from pbn.regions import RegionDetector


def test_detect_single_two_by_two_region() -> None:
    image = InputImage.from_rows(
        (
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
            ),
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
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
    detector = RegionDetector()

    quantized_image = quantizer.quantize(
        image,
        palette,
    )

    regions = detector.detect(
        quantized_image,
    )

    assert len(regions) == 1

    region = regions[0]

    assert region.id == 1
    assert region.color == black

    assert set(region.coordinates()) == {
        (0, 0),
        (1, 0),
        (0, 1),
        (1, 1),
    }


def test_detect_uses_four_way_connectivity_and_scan_order() -> None:
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

    white = PaletteColor(
        number=2,
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

    image = QuantizedImage.from_rows(
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

    regions = RegionDetector().detect(image)

    assert tuple(
        (
            region.id,
            region.color,
            frozenset(region.coordinates()),
        )
        for region in regions
    ) == (
        (
            1,
            black,
            frozenset({(0, 0)}),
        ),
        (
            2,
            white,
            frozenset({(1, 0)}),
        ),
        (
            3,
            white,
            frozenset({(0, 1)}),
        ),
        (
            4,
            black,
            frozenset({(1, 1)}),
        ),
    )
