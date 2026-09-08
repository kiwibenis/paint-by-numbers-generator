# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.core.minimum_region_size import MinimumRegionSize
from pbn.models import ImagePlacementGeometry


def test_minimum_region_size_can_be_used_for_region_circle_check() -> None:
    geometry = ImagePlacementGeometry(
        scale=0.1,
        image_width_mm=400.0,
        image_height_mm=300.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=4000,
        crop_height_px=3000,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    diameter_px = MinimumRegionSize().to_pixel_diameter(
        minimum_region_size_mm=3.0,
        geometry=geometry,
    )

    assert diameter_px == 30


def test_converts_mm_to_exact_pixel_diameter() -> None:
    geometry = ImagePlacementGeometry(
        scale=0.1,
        image_width_mm=400.0,
        image_height_mm=300.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=4000,
        crop_height_px=3000,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    result = MinimumRegionSize().to_pixel_diameter(
        minimum_region_size_mm=3.0,
        geometry=geometry,
    )

    assert result == 30


def test_rounds_pixel_diameter_up() -> None:
    geometry = ImagePlacementGeometry(
        scale=0.06944,
        image_width_mm=280.0,
        image_height_mm=210.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=4032,
        crop_height_px=3024,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    result = MinimumRegionSize().to_pixel_diameter(
        minimum_region_size_mm=3.0,
        geometry=geometry,
    )

    assert result == 44
