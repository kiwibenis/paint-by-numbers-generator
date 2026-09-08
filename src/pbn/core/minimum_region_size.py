# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from math import ceil

from pbn.models import ImagePlacementGeometry


class MinimumRegionSize:
    """Convert a physical minimum region size to input-image pixels."""

    def to_pixel_diameter(
        self,
        minimum_region_size_mm: float,
        geometry: ImagePlacementGeometry,
    ) -> int:
        """Return the required pixel diameter, rounded up."""
        return ceil(
            minimum_region_size_mm / geometry.scale,
        )
