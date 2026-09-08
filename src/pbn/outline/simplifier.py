# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import Outline

Point = tuple[int, int]
Ring = tuple[Point, ...]


class DouglasPeuckerSimplifier:
    """
    Simplifies closed polygon outlines using the Douglas-Peucker algorithm.
    """

    def simplify(
        self,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        """
        Return a simplified outline while preserving polygon identity.
        """
        if tolerance < 0.0:
            raise ValueError(
                "tolerance must not be negative",
            )

        tolerance_squared = tolerance * tolerance

        return Outline(
            region_id=outline.region_id,
            points=self._simplify_closed_ring(
                outline.points,
                tolerance_squared=tolerance_squared,
            ),
            hole_rings=tuple(
                self._simplify_closed_ring(
                    ring,
                    tolerance_squared=tolerance_squared,
                )
                for ring in outline.hole_rings
            ),
        )

    def _simplify_closed_ring(
        self,
        points: Ring,
        *,
        tolerance_squared: float,
    ) -> Ring:
        if len(points) <= 3:
            return points

        anchor_index = self._find_anchor_index(
            points,
        )

        if anchor_index == 0:
            return points

        first_chain = points[: anchor_index + 1]

        second_chain = points[anchor_index:] + (points[0],)

        simplified_first = self._simplify_open_chain_with_tolerance_squared(
            first_chain,
            tolerance_squared=tolerance_squared,
        )

        simplified_second = self._simplify_open_chain_with_tolerance_squared(
            second_chain,
            tolerance_squared=tolerance_squared,
        )

        simplified_points = simplified_first + simplified_second[1:-1]

        if len(simplified_points) < 3:
            simplified_points = self._build_minimum_polygon(
                points,
                anchor_index=anchor_index,
            )

        return simplified_points

    def simplify_open_chain(
        self,
        points: tuple[Point, ...],
        *,
        tolerance: float,
    ) -> tuple[Point, ...]:
        """
        Simplify an open point chain while preserving both endpoints.
        """
        if tolerance < 0.0:
            raise ValueError(
                "tolerance must not be negative",
            )

        return self._simplify_open_chain_with_tolerance_squared(
            points,
            tolerance_squared=tolerance * tolerance,
        )

    @staticmethod
    def _find_anchor_index(
        points: tuple[Point, ...],
    ) -> int:
        """
        Return the point farthest from the canonical first point.
        """
        first = points[0]

        farthest_index = 0
        farthest_distance_squared = 0

        for index in range(
            1,
            len(points),
        ):
            point = points[index]

            dx = point[0] - first[0]
            dy = point[1] - first[1]

            distance_squared = dx * dx + dy * dy

            if distance_squared > farthest_distance_squared:
                farthest_index = index
                farthest_distance_squared = distance_squared

        return farthest_index

    def _simplify_open_chain_with_tolerance_squared(
        self,
        points: tuple[Point, ...],
        *,
        tolerance_squared: float,
    ) -> tuple[Point, ...]:
        """
        Simplify one open point chain using iterative Douglas-Peucker.
        """
        if len(points) <= 2:
            return points

        kept_indices = {
            0,
            len(points) - 1,
        }

        pending_segments = [
            (
                0,
                len(points) - 1,
            ),
        ]

        while pending_segments:
            (
                start_index,
                end_index,
            ) = pending_segments.pop()

            farthest_index: int | None = None
            farthest_distance_squared = -1.0

            for index in range(
                start_index + 1,
                end_index,
            ):
                distance_squared = self._point_segment_distance_squared(
                    points[index],
                    points[start_index],
                    points[end_index],
                )

                if distance_squared > farthest_distance_squared:
                    farthest_index = index
                    farthest_distance_squared = distance_squared

            if farthest_index is None or farthest_distance_squared <= tolerance_squared:
                continue

            kept_indices.add(
                farthest_index,
            )

            pending_segments.append(
                (
                    farthest_index,
                    end_index,
                )
            )
            pending_segments.append(
                (
                    start_index,
                    farthest_index,
                )
            )

        return tuple(
            points[index]
            for index in sorted(
                kept_indices,
            )
        )

    def _build_minimum_polygon(
        self,
        points: tuple[Point, ...],
        *,
        anchor_index: int,
    ) -> tuple[Point, ...]:
        """
        Preserve at least three vertices for a closed polygon.
        """
        first = points[0]
        anchor = points[anchor_index]

        third_index: int | None = None
        largest_distance_squared = -1.0

        for index in range(
            1,
            len(points),
        ):
            if index == anchor_index:
                continue

            distance_squared = self._point_segment_distance_squared(
                points[index],
                first,
                anchor,
            )

            if distance_squared > largest_distance_squared:
                third_index = index
                largest_distance_squared = distance_squared

        if third_index is None:
            return points

        selected_indices = tuple(
            sorted(
                (
                    0,
                    anchor_index,
                    third_index,
                )
            )
        )

        return tuple(points[index] for index in selected_indices)

    @staticmethod
    def _point_segment_distance_squared(
        point: Point,
        start: Point,
        end: Point,
    ) -> float:
        """
        Return the squared distance from a point to a line segment.
        """
        segment_x = end[0] - start[0]
        segment_y = end[1] - start[1]

        segment_length_squared = segment_x * segment_x + segment_y * segment_y

        if segment_length_squared == 0:
            offset_x = point[0] - start[0]
            offset_y = point[1] - start[1]

            return float(offset_x * offset_x + offset_y * offset_y)

        offset_x = point[0] - start[0]
        offset_y = point[1] - start[1]

        projection = (
            offset_x * segment_x + offset_y * segment_y
        ) / segment_length_squared

        clamped_projection = max(
            0.0,
            min(
                1.0,
                projection,
            ),
        )

        closest_x = start[0] + clamped_projection * segment_x
        closest_y = start[1] + clamped_projection * segment_y

        distance_x = point[0] - closest_x
        distance_y = point[1] - closest_y

        return distance_x * distance_x + distance_y * distance_y
