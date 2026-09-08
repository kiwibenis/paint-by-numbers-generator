# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImagePlacementGeometry:
    """
    Immutable mapping between input-image pixels and physical output space.
    """

    scale: float
    image_width_mm: float
    image_height_mm: float
    crop_left_px: int
    crop_top_px: int
    crop_width_px: int
    crop_height_px: int
    output_offset_x_mm: float
    output_offset_y_mm: float

    def contains_input_position(
        self,
        x_px: float,
        y_px: float,
    ) -> bool:
        """
        Return whether an input position is inside the visible crop window.
        """

        return (
            self.crop_left_px <= x_px <= self.crop_left_px + self.crop_width_px
            and self.crop_top_px <= y_px <= self.crop_top_px + self.crop_height_px
        )

    def to_output_position(
        self,
        x_px: float,
        y_px: float,
    ) -> tuple[float, float]:
        x_mm = (x_px - self.crop_left_px) * self.scale + self.output_offset_x_mm

        y_mm = (y_px - self.crop_top_px) * self.scale + self.output_offset_y_mm

        return (
            x_mm,
            y_mm,
        )
