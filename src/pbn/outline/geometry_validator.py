# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from pbn.models import Outline

Point = tuple[int, int]
FloatPoint = tuple[float, float]
BoundingBox = tuple[int, int, int, int]
Segment = tuple[Point, Point, BoundingBox]
RegionPair = tuple[int, int]


class OverlapDetector(Protocol):
    """
    Structural type for an accelerated overlap implementation.
    """

    def overlapping_region_pairs(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[RegionPair]: ...


class OutlineGeometryValidator:
    """
    Validates polygon geometry for region outlines.

    Pairwise overlap detection may be delegated to an accelerated
    implementation. Individual ring validity is always decided here, so the
    tolerated raster self-touch behavior never depends on the selected path.
    """

    _overlap_detector: OverlapDetector | None = None

    def __init__(
        self,
        overlap_detector: OverlapDetector | None = None,
    ) -> None:
        self._overlap_detector = overlap_detector

    def invalid_region_ids(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[int]:
        invalid_region_ids = self.invalid_outline_region_ids(
            outlines,
            region_ids=region_ids,
        )

        for first_region_id, second_region_id in self.overlapping_region_pairs(
            outlines,
            region_ids=region_ids,
        ):
            invalid_region_ids.add(
                first_region_id,
            )
            invalid_region_ids.add(
                second_region_id,
            )

        return invalid_region_ids

    @classmethod
    def invalid_outline_region_ids(
        cls,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[int]:
        return {
            outline.region_id
            for outline in outlines
            if (region_ids is None or outline.region_id in region_ids)
            and not cls._has_valid_outline_geometry(
                outline,
            )
        }

    def overlapping_region_pairs(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[RegionPair]:
        """
        Return region pairs whose outlines share positive interior area.
        """
        detector = self._overlap_detector

        if detector is None:
            return self.reference_overlapping_region_pairs(
                outlines,
                region_ids=region_ids,
            )

        return detector.overlapping_region_pairs(
            outlines,
            region_ids=region_ids,
        )

    @classmethod
    def reference_overlapping_region_pairs(
        cls,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[RegionPair]:
        """
        Detect overlapping region pairs without acceleration.

        This implementation defines the expected overlap semantics.
        """
        overlapping_region_pairs: set[RegionPair] = set()

        bounding_boxes = tuple(
            cls._outline_bounding_box(
                outline,
            )
            for outline in outlines
        )

        for first_index, first_outline in enumerate(
            outlines,
        ):
            first_bounding_box = bounding_boxes[first_index]

            if first_bounding_box is None:
                continue

            for second_index in range(
                first_index + 1,
                len(outlines),
            ):
                second_outline = outlines[second_index]

                if (
                    region_ids is not None
                    and first_outline.region_id not in region_ids
                    and second_outline.region_id not in region_ids
                ):
                    continue

                second_bounding_box = bounding_boxes[second_index]

                if second_bounding_box is None:
                    continue

                if not cls._bounding_boxes_overlap(
                    first_bounding_box,
                    second_bounding_box,
                ):
                    continue

                if cls._outlines_overlap_in_area(
                    first_outline,
                    second_outline,
                    first_bounding_box=first_bounding_box,
                    second_bounding_box=second_bounding_box,
                ):
                    overlapping_region_pairs.add(
                        (
                            min(
                                first_outline.region_id,
                                second_outline.region_id,
                            ),
                            max(
                                first_outline.region_id,
                                second_outline.region_id,
                            ),
                        )
                    )

        return overlapping_region_pairs

    @classmethod
    def _outlines_overlap_in_area(
        cls,
        first: Outline,
        second: Outline,
        *,
        first_bounding_box: BoundingBox,
        second_bounding_box: BoundingBox,
    ) -> bool:
        first_segments = cls._polygon_segments(
            first.points,
        )
        second_segments = cls._polygon_segments(
            second.points,
        )
        first_hole_boundaries = cls._prepared_hole_boundaries(
            first,
        )
        second_hole_boundaries = cls._prepared_hole_boundaries(
            second,
        )

        first_boundaries = (
            first_segments,
            *(segments for segments, _ in first_hole_boundaries),
        )
        second_boundaries = (
            second_segments,
            *(segments for segments, _ in second_hole_boundaries),
        )

        for first_boundary in first_boundaries:
            for second_boundary in second_boundaries:
                if cls._outlines_cross_properly(
                    first_boundary,
                    second_boundary,
                ):
                    return True

        if cls._polygon_has_sample_strictly_inside_outline(
            first.points,
            other_outer_segments=second_segments,
            other_outer_bounding_box=second_bounding_box,
            other_hole_boundaries=second_hole_boundaries,
        ):
            return True

        if cls._polygon_has_sample_strictly_inside_outline(
            second.points,
            other_outer_segments=first_segments,
            other_outer_bounding_box=first_bounding_box,
            other_hole_boundaries=first_hole_boundaries,
        ):
            return True

        return cls._polygon_boundaries_coincide(
            first.points,
            second.points,
        )

    @classmethod
    def _prepared_hole_boundaries(
        cls,
        outline: Outline,
    ) -> tuple[
        tuple[
            tuple[Segment, ...],
            BoundingBox,
        ],
        ...,
    ]:
        prepared_boundaries: list[
            tuple[
                tuple[Segment, ...],
                BoundingBox,
            ]
        ] = []

        for ring in outline.hole_rings:
            bounding_box = cls._ring_bounding_box(
                ring,
            )

            if bounding_box is None:
                continue

            prepared_boundaries.append(
                (
                    cls._polygon_segments(
                        ring,
                    ),
                    bounding_box,
                )
            )

        return tuple(
            prepared_boundaries,
        )

    @classmethod
    def _polygon_has_sample_strictly_inside_outline(
        cls,
        points: tuple[Point, ...],
        *,
        other_outer_segments: tuple[Segment, ...],
        other_outer_bounding_box: BoundingBox,
        other_hole_boundaries: tuple[
            tuple[
                tuple[Segment, ...],
                BoundingBox,
            ],
            ...,
        ],
    ) -> bool:
        for point in points:
            if cls._point_is_strictly_inside_outline(
                (
                    float(point[0]),
                    float(point[1]),
                ),
                outer_segments=other_outer_segments,
                outer_bounding_box=other_outer_bounding_box,
                hole_boundaries=other_hole_boundaries,
            ):
                return True

        for index in range(
            len(points),
        ):
            start = points[index]
            end = points[(index + 1) % len(points)]

            midpoint = (
                (start[0] + end[0]) / 2.0,
                (start[1] + end[1]) / 2.0,
            )

            if cls._point_is_strictly_inside_outline(
                midpoint,
                outer_segments=other_outer_segments,
                outer_bounding_box=other_outer_bounding_box,
                hole_boundaries=other_hole_boundaries,
            ):
                return True

        return False

    @classmethod
    def _point_is_strictly_inside_outline(
        cls,
        point: FloatPoint,
        *,
        outer_segments: tuple[Segment, ...],
        outer_bounding_box: BoundingBox,
        hole_boundaries: tuple[
            tuple[
                tuple[Segment, ...],
                BoundingBox,
            ],
            ...,
        ],
    ) -> bool:
        if not cls._point_is_strictly_inside_polygon(
            point,
            outer_segments,
            bounding_box=outer_bounding_box,
        ):
            return False

        for hole_segments, hole_bounding_box in hole_boundaries:
            if not cls._float_point_within_bounding_box(
                point,
                hole_bounding_box,
            ):
                continue

            if cls._point_is_on_prepared_polygon_boundary(
                point,
                hole_segments,
            ):
                return False

            if cls._point_is_strictly_inside_polygon(
                point,
                hole_segments,
                bounding_box=hole_bounding_box,
            ):
                return False

        return True

    @classmethod
    def _point_is_on_prepared_polygon_boundary(
        cls,
        point: FloatPoint,
        segments: tuple[Segment, ...],
    ) -> bool:
        point_x, point_y = point

        for start, end, bounding_box in segments:
            (
                min_x,
                min_y,
                max_x,
                max_y,
            ) = bounding_box

            if point_x < min_x or point_x > max_x or point_y < min_y or point_y > max_y:
                continue

            if cls._float_point_is_on_segment(
                point,
                start,
                end,
            ):
                return True

        return False

    @classmethod
    def _polygon_has_sample_strictly_inside(
        cls,
        points: tuple[Point, ...],
        *,
        other_segments: tuple[Segment, ...],
        other_bounding_box: BoundingBox,
    ) -> bool:
        for point in points:
            if cls._point_is_strictly_inside_polygon(
                (
                    float(point[0]),
                    float(point[1]),
                ),
                other_segments,
                bounding_box=other_bounding_box,
            ):
                return True

        for index in range(
            len(points),
        ):
            start = points[index]
            end = points[(index + 1) % len(points)]

            midpoint = (
                (start[0] + end[0]) / 2.0,
                (start[1] + end[1]) / 2.0,
            )

            if cls._point_is_strictly_inside_polygon(
                midpoint,
                other_segments,
                bounding_box=other_bounding_box,
            ):
                return True

        return False

    @classmethod
    def _polygon_boundaries_coincide(
        cls,
        first_points: tuple[Point, ...],
        second_points: tuple[Point, ...],
    ) -> bool:
        if abs(
            cls._signed_area_twice(
                first_points,
            )
        ) != abs(
            cls._signed_area_twice(
                second_points,
            )
        ):
            return False

        return all(
            cls._point_is_on_polygon_boundary(
                (
                    float(point[0]),
                    float(point[1]),
                ),
                second_points,
            )
            for point in first_points
        ) and all(
            cls._point_is_on_polygon_boundary(
                (
                    float(point[0]),
                    float(point[1]),
                ),
                first_points,
            )
            for point in second_points
        )

    @classmethod
    def _point_is_strictly_inside_polygon(
        cls,
        point: FloatPoint,
        segments: tuple[Segment, ...],
        *,
        bounding_box: BoundingBox,
    ) -> bool:
        if not cls._float_point_within_bounding_box(
            point,
            bounding_box,
        ):
            return False

        point_x, point_y = point
        inside = False

        for start, end, segment_bounding_box in segments:
            (
                segment_min_x,
                segment_min_y,
                segment_max_x,
                segment_max_y,
            ) = segment_bounding_box

            if point_y < segment_min_y or point_y > segment_max_y:
                continue

            if (
                segment_min_x <= point_x <= segment_max_x
                and cls._float_point_is_on_segment(
                    point,
                    start,
                    end,
                )
            ):
                return False

            if (start[1] > point_y) == (end[1] > point_y):
                continue

            intersection_x = start[0] + (point_y - start[1]) * (end[0] - start[0]) / (
                end[1] - start[1]
            )

            if intersection_x > point_x:
                inside = not inside

        return inside

    @staticmethod
    def _float_point_within_bounding_box(
        point: FloatPoint,
        bounding_box: BoundingBox,
    ) -> bool:
        return (
            bounding_box[0] <= point[0] <= bounding_box[2]
            and bounding_box[1] <= point[1] <= bounding_box[3]
        )

    @classmethod
    def _point_is_on_polygon_boundary(
        cls,
        point: FloatPoint,
        points: tuple[Point, ...],
    ) -> bool:
        return any(
            cls._float_point_is_on_segment(
                point,
                points[index],
                points[(index + 1) % len(points)],
            )
            for index in range(
                len(points),
            )
        )

    @staticmethod
    def _float_point_is_on_segment(
        point: FloatPoint,
        start: Point,
        end: Point,
    ) -> bool:
        orientation = (end[0] - start[0]) * (point[1] - start[1]) - (
            end[1] - start[1]
        ) * (point[0] - start[0])

        if orientation != 0.0:
            return False

        return min(
            start[0],
            end[0],
        ) <= point[0] <= max(
            start[0],
            end[0],
        ) and min(
            start[1],
            end[1],
        ) <= point[1] <= max(
            start[1],
            end[1],
        )

    @classmethod
    def _outlines_cross_properly(
        cls,
        first_segments: tuple[Segment, ...],
        second_segments: tuple[Segment, ...],
    ) -> bool:
        for first_segment, second_segment in cls._cross_polygon_segment_candidates(
            first_segments,
            second_segments,
        ):
            if cls._segments_cross_properly(
                first_segment,
                second_segment,
            ):
                return True

        return False

    @classmethod
    def _cross_polygon_segment_candidates(
        cls,
        first_segments: tuple[Segment, ...],
        second_segments: tuple[Segment, ...],
    ) -> Iterator[tuple[Segment, Segment]]:
        segment_groups = (
            first_segments,
            second_segments,
        )
        active_segment_indices: tuple[
            list[int],
            list[int],
        ] = (
            [],
            [],
        )

        for (
            _,
            event_kind,
            group_index,
            segment_index,
        ) in cls._segment_events(
            segment_groups,
        ):
            active_indices = active_segment_indices[group_index]

            if event_kind == 1:
                active_indices.remove(
                    segment_index,
                )
                continue

            segment = segment_groups[group_index][segment_index]
            other_group_index = 1 - group_index

            for other_segment_index in active_segment_indices[other_group_index]:
                other_segment = segment_groups[other_group_index][other_segment_index]

                if not cls._segment_y_ranges_overlap(
                    segment,
                    other_segment,
                ):
                    continue

                if group_index == 0:
                    yield (
                        segment,
                        other_segment,
                    )
                else:
                    yield (
                        other_segment,
                        segment,
                    )

            active_indices.append(
                segment_index,
            )

    @staticmethod
    def _segment_events(
        segment_groups: tuple[
            tuple[Segment, ...],
            ...,
        ],
    ) -> tuple[
        tuple[int, int, int, int],
        ...,
    ]:
        events: list[tuple[int, int, int, int]] = []

        for group_index, segments in enumerate(
            segment_groups,
        ):
            for segment_index, segment in enumerate(
                segments,
            ):
                bounding_box = segment[2]
                events.append(
                    (
                        bounding_box[0],
                        0,
                        group_index,
                        segment_index,
                    )
                )
                events.append(
                    (
                        bounding_box[2],
                        1,
                        group_index,
                        segment_index,
                    )
                )

        return tuple(
            sorted(
                events,
            )
        )

    @staticmethod
    def _segment_y_ranges_overlap(
        first: Segment,
        second: Segment,
    ) -> bool:
        first_bounding_box = first[2]
        second_bounding_box = second[2]

        return not (
            first_bounding_box[3] < second_bounding_box[1]
            or second_bounding_box[3] < first_bounding_box[1]
        )

    @classmethod
    def _segments_cross_properly(
        cls,
        first: Segment,
        second: Segment,
    ) -> bool:
        first_start, first_end, first_bounding_box = first
        second_start, second_end, second_bounding_box = second

        if not cls._bounding_boxes_overlap(
            first_bounding_box,
            second_bounding_box,
        ):
            return False

        first_orientation = cls._orientation(
            first_start,
            first_end,
            second_start,
        )
        second_orientation = cls._orientation(
            first_start,
            first_end,
            second_end,
        )
        third_orientation = cls._orientation(
            second_start,
            second_end,
            first_start,
        )
        fourth_orientation = cls._orientation(
            second_start,
            second_end,
            first_end,
        )

        return (
            first_orientation * second_orientation < 0
            and third_orientation * fourth_orientation < 0
        )

    @classmethod
    def _outline_bounding_box(
        cls,
        outline: Outline,
    ) -> BoundingBox | None:
        return cls._ring_bounding_box(
            outline.points,
        )

    @staticmethod
    def _ring_bounding_box(
        points: tuple[Point, ...],
    ) -> BoundingBox | None:
        if not points:
            return None

        x_values = tuple(point[0] for point in points)
        y_values = tuple(point[1] for point in points)

        return (
            min(x_values),
            min(y_values),
            max(x_values),
            max(y_values),
        )

    @staticmethod
    def _bounding_boxes_overlap(
        first: BoundingBox,
        second: BoundingBox,
    ) -> bool:
        return not (
            first[2] < second[0]
            or second[2] < first[0]
            or first[3] < second[1]
            or second[3] < first[1]
        )

    @classmethod
    def _polygon_segments(
        cls,
        points: tuple[Point, ...],
    ) -> tuple[Segment, ...]:
        return tuple(
            cls._segment(
                points[index],
                points[(index + 1) % len(points)],
            )
            for index in range(
                len(points),
            )
        )

    @staticmethod
    def _segment(
        start: Point,
        end: Point,
    ) -> Segment:
        return (
            start,
            end,
            (
                min(
                    start[0],
                    end[0],
                ),
                min(
                    start[1],
                    end[1],
                ),
                max(
                    start[0],
                    end[0],
                ),
                max(
                    start[1],
                    end[1],
                ),
            ),
        )

    @classmethod
    def _has_valid_outline_geometry(
        cls,
        outline: Outline,
    ) -> bool:
        if outline.points and not cls._has_valid_ring_geometry(
            outline.points,
        ):
            return False

        return all(
            cls._has_valid_ring_geometry(
                ring,
            )
            for ring in outline.hole_rings
        )

    @classmethod
    def _has_valid_ring_geometry(
        cls,
        points: tuple[Point, ...],
    ) -> bool:
        return (
            len(set(points)) >= 3
            and cls._signed_area_twice(
                points,
            )
            != 0
            and not cls._has_self_intersection(
                points,
            )
        )

    @staticmethod
    def _signed_area_twice(
        points: tuple[Point, ...],
    ) -> int:
        return sum(
            (
                points[index][0] * points[(index + 1) % len(points)][1]
                - points[(index + 1) % len(points)][0] * points[index][1]
            )
            for index in range(
                len(points),
            )
        )

    @classmethod
    def _has_self_intersection(
        cls,
        points: tuple[Point, ...],
    ) -> bool:
        segments = cls._polygon_segments(
            points,
        )
        segment_count = len(segments)

        for (
            first_index,
            first_segment,
            second_index,
            second_segment,
        ) in cls._self_intersection_segment_candidates(
            segments,
        ):
            if second_index == first_index + 1:
                continue

            if first_index == 0 and second_index == segment_count - 1:
                continue

            if cls._segments_intersect_invalidly(
                first_segment,
                second_segment,
            ):
                return True

        return False

    @classmethod
    def _self_intersection_segment_candidates(
        cls,
        segments: tuple[Segment, ...],
    ) -> Iterator[
        tuple[
            int,
            Segment,
            int,
            Segment,
        ]
    ]:
        active_segment_indices: list[int] = []

        for (
            _,
            event_kind,
            _,
            segment_index,
        ) in cls._segment_events(
            (segments,),
        ):
            if event_kind == 1:
                active_segment_indices.remove(
                    segment_index,
                )
                continue

            segment = segments[segment_index]

            for other_segment_index in active_segment_indices:
                other_segment = segments[other_segment_index]

                if not cls._segment_y_ranges_overlap(
                    segment,
                    other_segment,
                ):
                    continue

                first_index = min(
                    segment_index,
                    other_segment_index,
                )
                second_index = max(
                    segment_index,
                    other_segment_index,
                )

                yield (
                    first_index,
                    segments[first_index],
                    second_index,
                    segments[second_index],
                )

            active_segment_indices.append(
                segment_index,
            )

    @classmethod
    def _segments_intersect_invalidly(
        cls,
        first: Segment,
        second: Segment,
    ) -> bool:
        first_start, first_end, first_bounding_box = first
        second_start, second_end, second_bounding_box = second

        if not cls._bounding_boxes_overlap(
            first_bounding_box,
            second_bounding_box,
        ):
            return False

        first_orientation = cls._orientation(
            first_start,
            first_end,
            second_start,
        )
        second_orientation = cls._orientation(
            first_start,
            first_end,
            second_end,
        )
        third_orientation = cls._orientation(
            second_start,
            second_end,
            first_start,
        )
        fourth_orientation = cls._orientation(
            second_start,
            second_end,
            first_end,
        )

        if (
            first_orientation * second_orientation < 0
            and third_orientation * fourth_orientation < 0
        ):
            return True

        intersection_points: set[Point] = set()

        if third_orientation == 0 and cls._point_within_segment_bounds(
            first_start,
            second_start,
            second_end,
        ):
            intersection_points.add(
                first_start,
            )

        if fourth_orientation == 0 and cls._point_within_segment_bounds(
            first_end,
            second_start,
            second_end,
        ):
            intersection_points.add(
                first_end,
            )

        if first_orientation == 0 and cls._point_within_segment_bounds(
            second_start,
            first_start,
            first_end,
        ):
            intersection_points.add(
                second_start,
            )

        if second_orientation == 0 and cls._point_within_segment_bounds(
            second_end,
            first_start,
            first_end,
        ):
            intersection_points.add(
                second_end,
            )

        if not intersection_points:
            return False

        shared_endpoints = {
            first_start,
            first_end,
        }.intersection(
            {
                second_start,
                second_end,
            },
        )

        return not (
            len(shared_endpoints) == 1 and intersection_points == shared_endpoints
        )

    @staticmethod
    def _point_within_segment_bounds(
        point: Point,
        start: Point,
        end: Point,
    ) -> bool:
        return min(
            start[0],
            end[0],
        ) <= point[0] <= max(
            start[0],
            end[0],
        ) and min(
            start[1],
            end[1],
        ) <= point[1] <= max(
            start[1],
            end[1],
        )

    @staticmethod
    def _orientation(
        first: Point,
        second: Point,
        third: Point,
    ) -> int:
        return (second[0] - first[0]) * (third[1] - first[1]) - (
            second[1] - first[1]
        ) * (third[0] - first[0])
