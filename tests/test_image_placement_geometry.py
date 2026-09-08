# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import (
    A4,
    ImagePlacement,
    ImagePlacementGeometry,
    ImageSize,
    Orientation,
    PhysicalOutputGeometry,
)
from pbn.pipeline.image_placement_calculator import (
    ImagePlacementCalculator,
)


def test_maps_cropped_image_pixel_to_physical_output_position() -> None:
    geometry = ImagePlacementGeometry(
        scale=297.0 / 4032.0,
        image_width_mm=297.0,
        image_height_mm=222.75,
        crop_left_px=0,
        crop_top_px=87,
        crop_width_px=4032,
        crop_height_px=2850,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    result = geometry.to_output_position(
        x_px=0,
        y_px=87,
    )

    assert result == (
        0.0,
        0.0,
    )


def test_maps_image_pixel_to_physical_output_position() -> None:
    geometry = ImagePlacementGeometry(
        scale=0.1,
        image_width_mm=280.0,
        image_height_mm=210.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=2800,
        crop_height_px=2100,
        output_offset_x_mm=8.5,
        output_offset_y_mm=0.0,
    )

    result = geometry.to_output_position(
        x_px=100,
        y_px=200,
    )

    assert result == (
        18.5,
        20.0,
    )


def test_fit_preserves_complete_image() -> None:
    image_size = ImageSize(
        width=4032,
        height=3024,
    )

    output = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.LANDSCAPE,
    )

    result = ImagePlacementCalculator().calculate(
        image_size=image_size,
        output=output,
        placement=ImagePlacement.FIT,
        margin_mm=0.0,
    )

    assert result.scale == 210.0 / 3024.0
    assert result.image_width_mm == 280.0
    assert result.image_height_mm == 210.0

    assert result.output_offset_x_mm == 8.5
    assert result.output_offset_y_mm == 0.0

    assert result.crop_left_px == 0
    assert result.crop_top_px == 0
    assert result.crop_width_px == 4032
    assert result.crop_height_px == 3024


def test_crop_fills_output_without_distortion() -> None:
    image_size = ImageSize(
        width=4032,
        height=3024,
    )

    output = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.LANDSCAPE,
    )

    result = ImagePlacementCalculator().calculate(
        image_size=image_size,
        output=output,
        placement=ImagePlacement.CROP,
        margin_mm=0.0,
    )

    assert result.scale == 297.0 / 4032.0
    assert result.image_width_mm == 297.0
    assert result.image_height_mm == 222.75

    assert result.output_offset_x_mm == 0.0
    assert result.output_offset_y_mm == 0.0

    assert result.crop_left_px == 0
    assert result.crop_top_px == 87
    assert result.crop_width_px == 4032
    assert result.crop_height_px == 2850
