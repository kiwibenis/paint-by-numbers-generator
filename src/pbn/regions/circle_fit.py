# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Set as AbstractSet
from math import ceil

from pbn.models import Region
from pbn.models.pixel_index import (
    MAXIMUM_COORDINATE,
    ROW_STRIDE,
)


class RegionCircleFit:
    """Determine whether a circle fits completely inside a region."""

    def __init__(self) -> None:
        self._circle_offsets_cache: dict[
            int,
            tuple[int, ...],
        ] = {}

    def fits(
        self,
        region: Region,
        diameter_px: int,
    ) -> bool:
        """Return whether a circle of the given diameter fits in the region."""
        return self.fits_pixels(
            pixels=region.pixels,
            diameter_px=diameter_px,
        )

    def fits_pixels(
        self,
        pixels: AbstractSet[int],
        diameter_px: int,
    ) -> bool:
        """
        Return whether a circle fits inside the supplied pixel set.

        The pixels are packed indices, and the circle offsets are packed
        the same way, so a candidate pixel is one integer addition rather
        than a coordinate pair that has to be built first.
        """
        if diameter_px <= 0 or not pixels:
            return False

        radius = diameter_px / 2.0
        circle_offsets = self._cached_circle_offsets(
            diameter_px,
            radius,
        )

        if len(pixels) < len(circle_offsets):
            return False

        pixel_iterator = iter(pixels)
        first = next(pixel_iterator)

        min_x = first & MAXIMUM_COORDINATE
        max_x = min_x
        min_y = first >> 32
        max_y = min_y

        for pixel in pixel_iterator:
            x = pixel & MAXIMUM_COORDINATE

            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x

            y = pixel >> 32

            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y

        center_min_x = ceil(min_x + radius)
        center_max_x = int(max_x - radius)
        center_min_y = ceil(min_y + radius)
        center_max_y = int(max_y - radius)

        if center_min_x > center_max_x or center_min_y > center_max_y:
            return False

        for center_x in range(
            center_min_x,
            center_max_x + 1,
        ):
            for center_y in range(
                center_min_y,
                center_max_y + 1,
            ):
                center = center_y * ROW_STRIDE + center_x
                fits = True

                for offset in circle_offsets:
                    if center + offset not in pixels:
                        fits = False
                        break

                if fits:
                    return True

        return False

    def _cached_circle_offsets(
        self,
        diameter_px: int,
        radius: float,
    ) -> tuple[int, ...]:
        cached = self._circle_offsets_cache.get(
            diameter_px,
        )

        if cached is not None:
            return cached

        circle_offsets = self._circle_offsets(
            radius,
        )
        self._circle_offsets_cache[diameter_px] = circle_offsets

        return circle_offsets

    def _circle_offsets(
        self,
        radius: float,
    ) -> tuple[int, ...]:
        """
        Return the packed offsets a circle of the given radius covers.

        A negative offset is a subtraction of the packed value, which is
        exact because every candidate center keeps the resulting
        coordinates inside the raster.
        """
        radius_squared = radius * radius
        pixel_radius = int(radius)

        return tuple(
            offset_y * ROW_STRIDE + offset_x
            for offset_y in range(
                -pixel_radius,
                pixel_radius + 1,
            )
            for offset_x in range(
                -pixel_radius,
                pixel_radius + 1,
            )
            if (offset_x * offset_x + offset_y * offset_y) <= radius_squared
        )
