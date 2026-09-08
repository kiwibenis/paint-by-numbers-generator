# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from shapely import STRtree
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from pbn.exceptions import GeometryAccelerationError
from pbn.models import Outline

RegionPair = tuple[int, int]

DEFAULT_MINIMUM_OVERLAP_AREA = 1e-9

_AREA_REPAIR_TOLERANCE = 1e-9


class ShapelyOverlapDetector:
    """
    Detects pairwise outline overlap using compiled geometry predicates.

    Only pairwise positive-area overlap is delegated to the geometry
    library. Individual ring validity remains a Core responsibility, so the
    tolerated raster self-touch behavior is never decided here.
    """

    def __init__(
        self,
        minimum_overlap_area: float = DEFAULT_MINIMUM_OVERLAP_AREA,
    ) -> None:
        if minimum_overlap_area <= 0.0:
            raise ValueError(
                "minimum_overlap_area must be greater than zero",
            )

        self._minimum_overlap_area = minimum_overlap_area

    def overlapping_region_pairs(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[RegionPair]:
        """
        Return region pairs whose outlines share positive interior area.
        """
        indexed_polygons = [
            (
                index,
                self._to_polygon(
                    outline,
                ),
            )
            for index, outline in enumerate(
                outlines,
            )
            if outline.points
        ]

        if len(indexed_polygons) < 2:
            return set()

        tree = STRtree(
            [polygon for _, polygon in indexed_polygons],
        )

        overlapping_region_pairs: set[RegionPair] = set()

        for position, (index, polygon) in enumerate(
            indexed_polygons,
        ):
            for other_position in tree.query(
                polygon,
            ):
                if other_position <= position:
                    continue

                other_index, other_polygon = indexed_polygons[other_position]

                first_region_id = outlines[index].region_id
                second_region_id = outlines[other_index].region_id

                if (
                    region_ids is not None
                    and first_region_id not in region_ids
                    and second_region_id not in region_ids
                ):
                    continue

                if not self._overlaps_in_area(
                    polygon,
                    other_polygon,
                ):
                    continue

                overlapping_region_pairs.add(
                    (
                        min(
                            first_region_id,
                            second_region_id,
                        ),
                        max(
                            first_region_id,
                            second_region_id,
                        ),
                    ),
                )

        return overlapping_region_pairs

    def _overlaps_in_area(
        self,
        first: BaseGeometry,
        second: BaseGeometry,
    ) -> bool:
        return bool(
            first.intersection(
                second,
            ).area
            > self._minimum_overlap_area
        )

    @staticmethod
    def _to_polygon(
        outline: Outline,
    ) -> BaseGeometry:
        """
        Build an area-preserving geometry for one multi-ring outline.
        """
        polygon = Polygon(
            outline.points,
            [list(ring) for ring in outline.hole_rings],
        )

        if polygon.is_valid:
            return polygon

        repaired = make_valid(
            polygon,
        )

        if abs(repaired.area - polygon.area) > _AREA_REPAIR_TOLERANCE:
            raise GeometryAccelerationError(
                "Geometry repair changed the enclosed area for region "
                f"{outline.region_id}.",
            )

        return repaired
