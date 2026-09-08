# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from unittest.mock import patch

import pytest

from pbn.color import DeltaE2000
from pbn.exceptions import InvariantViolationError, RegionPaintabilityError
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
    QuantizedImage,
    Region,
    VectorDocument,
)
from pbn.models.pixel_index import pack_pixels
from pbn.pipeline import PaintByNumbersGenerator, RegionGenerator
from pbn.regions import RegionMerger


def _solid_input_image(
    rgb: RGB,
    *,
    size: int,
) -> InputImage:
    row = tuple(rgb for _ in range(size))

    return InputImage.from_rows(tuple(row for _ in range(size)))


def _black_palette_color() -> PaletteColor:
    return PaletteColor(
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


def _white_palette_color() -> PaletteColor:
    return PaletteColor(
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


def _palette(
    *colors: PaletteColor,
) -> Palette:
    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=colors,
    )


def test_generate_returns_vector_document() -> None:
    black_rgb = RGB(
        red=0,
        green=0,
        blue=0,
    )

    image = _solid_input_image(
        black_rgb,
        size=3,
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            PaletteColor(
                number=1,
                name="Black",
                rgb=black_rgb,
                lab=Lab(
                    l=0.0,
                    a=0.0,
                    b=0.0,
                ),
            ),
        ),
    )

    generator = PaintByNumbersGenerator(
        outline_simplification_enabled=False,
        outline_simplification_tolerance_px=1.0,
        color_distance=DeltaE2000(),
    )

    document = generator.generate(
        image=image,
        palette=palette,
        minimum_circle_diameter_px=2,
    )

    assert isinstance(
        document,
        VectorDocument,
    )
    assert len(document.outlines) == 1
    assert len(document.labels) == 1
    assert document.palette_id == "test"
    assert document.palette_version == 1


def test_generate_uses_injected_quantizer() -> None:
    black_rgb = RGB(
        red=0,
        green=0,
        blue=0,
    )

    black = PaletteColor(
        number=1,
        name="Black",
        rgb=black_rgb,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    image = _solid_input_image(
        black_rgb,
        size=3,
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(black,),
    )

    captured: dict[str, object] = {}

    class FakeQuantizer:
        def quantize(
            self,
            image: InputImage,
            palette: Palette,
        ) -> QuantizedImage:
            captured["image"] = image
            captured["palette"] = palette

            row = tuple(black for _ in range(3))

            return QuantizedImage.from_rows(tuple(row for _ in range(3)))

    quantizer = FakeQuantizer()

    generator = PaintByNumbersGenerator(
        quantizer=quantizer,
        outline_simplification_enabled=False,
        outline_simplification_tolerance_px=1.0,
        color_distance=DeltaE2000(),
    )

    document = generator.generate(
        image=image,
        palette=palette,
        minimum_circle_diameter_px=2,
    )

    assert isinstance(
        document,
        VectorDocument,
    )
    assert captured["image"] is image
    assert captured["palette"] is palette


def test_generate_uses_injected_optional_complexity_reducer() -> None:
    black = _black_palette_color()
    image = _solid_input_image(
        black.rgb,
        size=3,
    )
    palette = _palette(
        black,
    )
    captured_regions: tuple[Region, ...] = ()
    captured: dict[str, object] = {}

    class FakeComplexityReducer:
        def reduce(
            self,
            regions: tuple[Region, ...],
            *,
            minimum_circle_diameter_px: int,
        ) -> tuple[Region, ...]:
            nonlocal captured_regions

            captured_regions = regions
            captured["minimum_circle_diameter_px"] = minimum_circle_diameter_px
            return regions

    generator = PaintByNumbersGenerator(
        complexity_reducer=FakeComplexityReducer(),
        outline_simplification_enabled=False,
        outline_simplification_tolerance_px=1.0,
        color_distance=DeltaE2000(),
    )

    document = generator.generate(
        image=image,
        palette=palette,
        minimum_circle_diameter_px=2,
    )

    assert isinstance(
        document,
        VectorDocument,
    )
    assert len(captured_regions) == 1
    assert captured["minimum_circle_diameter_px"] == 2


def test_generator_exists() -> None:
    generator = PaintByNumbersGenerator(
        outline_simplification_enabled=False,
        outline_simplification_tolerance_px=1.0,
        color_distance=DeltaE2000(),
    )

    assert generator is not None


def test_regions_single_black_region() -> None:
    black_rgb = RGB(
        red=0,
        green=0,
        blue=0,
    )

    image = _solid_input_image(
        black_rgb,
        size=3,
    )

    black = PaletteColor(
        number=1,
        name="Black",
        rgb=black_rgb,
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

    generator = RegionGenerator(
        color_distance=DeltaE2000(),
    )

    regions = generator.generate(
        image=image,
        palette=palette,
        minimum_circle_diameter_px=2,
    )

    assert len(regions) == 1

    region = regions[0]

    assert region.id == 1
    assert region.color == black
    assert set(region.coordinates()) == {(x, y) for x in range(3) for y in range(3)}


def test_region_generator_rejects_mergeable_undersized_mandatory_result() -> None:
    black = _black_palette_color()
    white = _white_palette_color()

    image = _solid_input_image(
        black.rgb,
        size=3,
    )

    palette = _palette(
        black,
        white,
    )

    large = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(4) for y in range(4)},
        ),
    )
    undersized = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (4, 1),
            },
        ),
    )

    reducer_called = False

    class FakeComplexityReducer:
        def reduce(
            self,
            regions: tuple[Region, ...],
            *,
            minimum_circle_diameter_px: int,
        ) -> tuple[Region, ...]:
            nonlocal reducer_called
            reducer_called = True
            return regions

    generator = RegionGenerator(
        color_distance=DeltaE2000(),
        complexity_reducer=FakeComplexityReducer(),
    )

    with (
        patch.object(
            RegionMerger,
            "merge",
            return_value=(
                large,
                undersized,
            ),
        ),
        pytest.raises(
            InvariantViolationError,
            match=(
                "Mandatory paintability merging left " "mergeable undersized regions"
            ),
        ),
    ):
        generator.generate(
            image=image,
            palette=palette,
            minimum_circle_diameter_px=2,
        )

    assert reducer_called is False


def test_region_generator_rejects_isolated_undersized_region() -> None:
    black = _black_palette_color()

    image = _solid_input_image(
        black.rgb,
        size=1,
    )

    palette = _palette(
        black,
    )

    with pytest.raises(
        RegionPaintabilityError,
        match=(
            "Mandatory paintability merging could not resolve "
            "isolated undersized regions"
        ),
    ):
        RegionGenerator(
            color_distance=DeltaE2000(),
        ).generate(
            image=image,
            palette=palette,
            minimum_circle_diameter_px=2,
        )


def test_region_generator_verifies_optional_complexity_result() -> None:
    black = _black_palette_color()
    white = _white_palette_color()

    image = _solid_input_image(
        black.rgb,
        size=3,
    )

    palette = _palette(
        black,
        white,
    )

    large = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(4) for y in range(4)},
        ),
    )
    undersized = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (4, 1),
            },
        ),
    )

    captured_minimum_circle_diameter_px: int | None = None

    class FakeComplexityReducer:
        def reduce(
            self,
            regions: tuple[Region, ...],
            *,
            minimum_circle_diameter_px: int,
        ) -> tuple[Region, ...]:
            nonlocal captured_minimum_circle_diameter_px
            captured_minimum_circle_diameter_px = minimum_circle_diameter_px

            return (
                large,
                undersized,
            )

    generator = RegionGenerator(
        color_distance=DeltaE2000(),
        complexity_reducer=FakeComplexityReducer(),
    )

    with pytest.raises(
        InvariantViolationError,
        match=(
            "Optional region complexity reduction left " "mergeable undersized regions"
        ),
    ):
        generator.generate(
            image=image,
            palette=palette,
            minimum_circle_diameter_px=2,
        )

    assert captured_minimum_circle_diameter_px == 2
