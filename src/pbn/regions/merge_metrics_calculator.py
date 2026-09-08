# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbstractSet

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    Region,
    RegionMergeCandidate,
    RegionMergeMetrics,
)
from pbn.models.pixel_index import ROW_STRIDE


class RegionMergeMetricsCalculator:
    """
    Calculate raw metrics for directed region merge candidates.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
    ) -> None:
        self._color_distance = color_distance
        self._perimeter_cache: dict[
            int,
            tuple[
                Region,
                int,
            ],
        ] = {}

    def calculate(
        self,
        candidate: RegionMergeCandidate,
        regions: Mapping[int, Region],
        shared_borders: Mapping[
            int,
            Mapping[int, int],
        ],
    ) -> RegionMergeMetrics:
        """
        Calculate raw metrics for one directed merge candidate.
        """
        source = regions[candidate.source_id]
        target = regions[candidate.target_id]

        source_area = source.size
        target_area = target.size

        shared_border_length = shared_borders[source.id][target.id]

        source_perimeter = self._region_perimeter(
            source,
        )
        target_perimeter = self._region_perimeter(
            target,
        )

        if source.pixels.isdisjoint(
            target.pixels,
        ):
            merged_area = source_area + target_area
            merged_perimeter = (
                source_perimeter + target_perimeter - 2 * shared_border_length
            )
        else:
            merged_pixels = source.pixels | target.pixels
            merged_area = len(
                merged_pixels,
            )
            merged_perimeter = self._perimeter(
                merged_pixels,
            )

        return RegionMergeMetrics(
            color_difference=self._color_distance.distance(
                source.color.lab,
                target.color.lab,
            ),
            source_area=source_area,
            target_area=target_area,
            merged_area=merged_area,
            affected_area_ratio=(source_area / merged_area),
            shared_border_length=shared_border_length,
            source_perimeter=source_perimeter,
            target_perimeter=target_perimeter,
            merged_perimeter=merged_perimeter,
        )

    def _region_perimeter(
        self,
        region: Region,
    ) -> int:
        cached = self._perimeter_cache.get(
            region.id,
        )

        if cached is not None and cached[0] is region:
            return cached[1]

        perimeter = self._perimeter(
            region.pixels,
        )

        self._perimeter_cache[region.id] = (
            region,
            perimeter,
        )

        return perimeter

    def _perimeter(
        self,
        pixels: AbstractSet[int],
    ) -> int:
        perimeter = 0

        for pixel in pixels:
            neighbors = (
                pixel - 1,
                pixel + 1,
                pixel - ROW_STRIDE,
                pixel + ROW_STRIDE,
            )

            perimeter += sum(neighbor not in pixels for neighbor in neighbors)

        return perimeter
