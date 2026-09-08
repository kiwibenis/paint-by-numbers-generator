# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.models import (
    A4,
    ImagePlacement,
    ImageSize,
    Orientation,
    PageSize,
    PhysicalOutputGeometry,
)
from pbn.pipeline.image_placement_calculator import (
    ImagePlacementCalculator,
)


def test_matching_aspect_ratio_does_not_crop() -> None:
    image_size = ImageSize(
        width=4000,
        height=3000,
    )

    output = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=400.0,
            height_mm=300.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    calculator = ImagePlacementCalculator()

    fit_result = calculator.calculate(
        image_size=image_size,
        output=output,
        placement=ImagePlacement.FIT,
        margin_mm=0.0,
    )

    crop_result = calculator.calculate(
        image_size=image_size,
        output=output,
        placement=ImagePlacement.CROP,
        margin_mm=0.0,
    )

    assert fit_result == crop_result

    assert fit_result.image_width_mm == 400.0
    assert fit_result.image_height_mm == 300.0
    assert fit_result.crop_left_px == 0
    assert fit_result.crop_top_px == 0
    assert fit_result.crop_width_px == 4000
    assert fit_result.crop_height_px == 3000


def test_fit_uses_complete_image() -> None:
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

    assert result.crop_left_px == 0
    assert result.crop_top_px == 87
    assert result.crop_width_px == 4032
    assert result.crop_height_px == 2850


def test_fit_stays_inside_configured_margin() -> None:
    image_size = ImageSize(
        width=400,
        height=300,
    )

    output = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=300.0,
            height_mm=200.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    result = ImagePlacementCalculator().calculate(
        image_size=image_size,
        output=output,
        placement=ImagePlacement.FIT,
        margin_mm=10.0,
    )

    assert result.scale == pytest.approx(0.6)
    assert result.image_width_mm == pytest.approx(240.0)
    assert result.image_height_mm == pytest.approx(180.0)

    assert result.crop_left_px == 0
    assert result.crop_top_px == 0
    assert result.crop_width_px == 400
    assert result.crop_height_px == 300

    assert result.output_offset_x_mm == pytest.approx(30.0)
    assert result.output_offset_y_mm == pytest.approx(10.0)


def test_crop_fills_only_area_inside_configured_margin() -> None:
    image_size = ImageSize(
        width=400,
        height=300,
    )

    output = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=300.0,
            height_mm=200.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    result = ImagePlacementCalculator().calculate(
        image_size=image_size,
        output=output,
        placement=ImagePlacement.CROP,
        margin_mm=10.0,
    )

    assert result.scale == pytest.approx(0.7)
    assert result.image_width_mm == pytest.approx(280.0)
    assert result.image_height_mm == pytest.approx(210.0)

    assert result.crop_left_px == 0
    assert result.crop_top_px == 21
    assert result.crop_width_px == 400
    assert result.crop_height_px == 257

    assert result.output_offset_x_mm == pytest.approx(10.0)
    assert result.output_offset_y_mm == pytest.approx(10.0)
