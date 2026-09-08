# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.config import GeneratorConfig
from pbn.core.minimum_region_size import MinimumRegionSize
from pbn.models import (
    A3,
    A4,
    ImagePlacement,
    ImagePlacementGeometry,
    ImageSize,
    Orientation,
    PageSize,
    PhysicalOutputGeometry,
)
from pbn.pipeline.image_placement_calculator import (
    ImagePlacementCalculator,
)

_POINTS_PER_INCH = 72.0
_MILLIMETERS_PER_INCH = 25.4


class GeneratorConfigResolver:
    """
    Resolves application configuration into domain models.
    """

    def calculate_minimum_circle_diameter(
        self,
        config: GeneratorConfig,
        image_size: ImageSize,
    ) -> int:
        geometry = self.calculate_image_placement_geometry(
            config=config,
            image_size=image_size,
        )

        return MinimumRegionSize().to_pixel_diameter(
            minimum_region_size_mm=config.minimum_region_size_mm,
            geometry=geometry,
        )

    def resolve_physical_output_geometry(
        self,
        config: GeneratorConfig,
    ) -> PhysicalOutputGeometry:
        page_size = self._resolve_page_size(
            config.page,
        )
        orientation = self._resolve_orientation(
            config.orientation,
        )

        return PhysicalOutputGeometry(
            page_size=page_size,
            orientation=orientation,
        )

    def resolve_palette_legend_geometry(
        self,
        config: GeneratorConfig,
    ) -> PhysicalOutputGeometry:
        page_size = self._resolve_page_size(
            config.pdf_legend.page,
        )
        orientation = self._resolve_orientation(
            config.pdf_legend.orientation,
        )

        return PhysicalOutputGeometry(
            page_size=page_size,
            orientation=orientation,
        )

    def resolve_image_placement(
        self,
        config: GeneratorConfig,
    ) -> ImagePlacement:
        for placement in ImagePlacement:
            if placement.value == config.placement:
                return placement

        raise ValueError(
            f"Unsupported image placement: {config.placement}",
        )

    def calculate_image_placement_geometry(
        self,
        config: GeneratorConfig,
        image_size: ImageSize,
    ) -> ImagePlacementGeometry:
        geometry = self.resolve_physical_output_geometry(
            config,
        )
        placement = self.resolve_image_placement(
            config,
        )

        margin_mm = config.margin_mm + self._half_line_width_mm(
            config.line_width_pt,
        )

        return ImagePlacementCalculator().calculate(
            image_size=image_size,
            output=geometry,
            placement=placement,
            margin_mm=margin_mm,
        )

    @staticmethod
    def _half_line_width_mm(
        line_width_pt: float,
    ) -> float:
        return line_width_pt * _MILLIMETERS_PER_INCH / _POINTS_PER_INCH / 2.0

    def _resolve_page_size(
        self,
        page: str,
    ) -> PageSize:
        if page == "A4":
            return A4

        if page == "A3":
            return A3

        raise ValueError(
            f"Unsupported page size: {page}",
        )

    def _resolve_orientation(
        self,
        orientation: str,
    ) -> Orientation:
        for value in Orientation:
            if value.value == orientation:
                return value

        raise ValueError(
            f"Unsupported orientation: {orientation}",
        )
