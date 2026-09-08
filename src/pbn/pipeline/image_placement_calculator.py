# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from math import floor

from pbn.models import (
    ImagePlacement,
    ImagePlacementGeometry,
    ImageSize,
    PhysicalOutputGeometry,
)


class ImagePlacementCalculator:
    """Calculate deterministic image placement geometry."""

    def calculate(
        self,
        image_size: ImageSize,
        output: PhysicalOutputGeometry,
        placement: ImagePlacement,
        margin_mm: float,
    ) -> ImagePlacementGeometry:
        """
        Calculate the physical placement of an image on the output page.
        """

        image_width = image_size.width
        image_height = image_size.height

        output_width = output.width_mm - 2.0 * margin_mm
        output_height = output.height_mm - 2.0 * margin_mm

        width_scale = output_width / image_width
        height_scale = output_height / image_height

        if placement is ImagePlacement.FIT:
            scale = min(
                width_scale,
                height_scale,
            )

            image_width_mm = image_width * scale
            image_height_mm = image_height * scale

            return ImagePlacementGeometry(
                scale=scale,
                image_width_mm=image_width_mm,
                image_height_mm=image_height_mm,
                crop_left_px=0,
                crop_top_px=0,
                crop_width_px=image_width,
                crop_height_px=image_height,
                output_offset_x_mm=(margin_mm + (output_width - image_width_mm) / 2.0),
                output_offset_y_mm=(
                    margin_mm + (output_height - image_height_mm) / 2.0
                ),
            )

        scale = max(
            width_scale,
            height_scale,
        )

        image_width_mm = image_width * scale
        image_height_mm = image_height * scale

        crop_width_px = floor(
            output_width / scale,
        )
        crop_height_px = floor(
            output_height / scale,
        )

        crop_left_px = (image_width - crop_width_px) // 2

        crop_top_px = (image_height - crop_height_px) // 2

        return ImagePlacementGeometry(
            scale=scale,
            image_width_mm=image_width_mm,
            image_height_mm=image_height_mm,
            crop_left_px=crop_left_px,
            crop_top_px=crop_top_px,
            crop_width_px=crop_width_px,
            crop_height_px=crop_height_px,
            output_offset_x_mm=margin_mm,
            output_offset_y_mm=margin_mm,
        )
