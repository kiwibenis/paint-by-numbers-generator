# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.exceptions import InvariantViolationError
from pbn.models import (
    Edge,
    Outline,
    Region,
)
from pbn.models.pixel_index import (
    MAXIMUM_COORDINATE,
    ROW_STRIDE,
)

Point = tuple[int, int]
Ring = tuple[Point, ...]


class OutlineTracer:
    """
    Generates polygon outlines from regions.
    """

    def trace(
        self,
        region: Region,
    ) -> Outline:
        raw_outline = self.trace_raw(
            region,
        )

        points = self._simplify_outline(
            raw_outline.points,
        )
        hole_rings = tuple(
            self._simplify_outline(
                ring,
            )
            for ring in raw_outline.hole_rings
        )

        return Outline(
            region_id=region.id,
            points=points,
            hole_rings=hole_rings,
        )

    def trace_raw(
        self,
        region: Region,
    ) -> Outline:
        """
        Generate an outline while preserving all grid boundary vertices.
        """
        edges = self._collect_edges(
            region,
        )
        rings = self._trace_rings(
            edges,
        )
        points, hole_rings = self._classify_rings(
            rings,
        )

        return Outline(
            region_id=region.id,
            points=points,
            hole_rings=hole_rings,
        )

    def _collect_edges(
        self,
        region: Region,
    ) -> frozenset[Edge]:
        """
        Return the boundary edges of a region.

        The four neighbor probes run on the packed indices, so a probe
        is an integer addition instead of a coordinate pair that has to
        be built first. The edges themselves stay in raster space,
        because that is what the ring tracing works on.
        """
        pixels = region.pixels

        edges: set[Edge] = set()

        for pixel in pixels:
            x = pixel & MAXIMUM_COORDINATE
            y = pixel >> 32

            if pixel - ROW_STRIDE not in pixels:
                edges.add(
                    Edge(
                        start=(x, y),
                        end=(x + 1, y),
                    )
                )

            if pixel + 1 not in pixels:
                edges.add(
                    Edge(
                        start=(x + 1, y),
                        end=(x + 1, y + 1),
                    )
                )

            if pixel + ROW_STRIDE not in pixels:
                edges.add(
                    Edge(
                        start=(x + 1, y + 1),
                        end=(x, y + 1),
                    )
                )

            if pixel - 1 not in pixels:
                edges.add(
                    Edge(
                        start=(x, y + 1),
                        end=(x, y),
                    )
                )

        return frozenset(edges)

    def _trace_rings(
        self,
        edges: frozenset[Edge],
    ) -> tuple[Ring, ...]:
        if not edges:
            return ()

        remaining = set(
            edges,
        )
        edges_by_start: dict[
            Point,
            set[Edge],
        ] = {}

        for edge in edges:
            edges_by_start.setdefault(
                edge.start,
                set(),
            ).add(
                edge,
            )

        rings: list[Ring] = []

        while remaining:
            first = min(
                remaining,
                key=self._edge_sort_key,
            )
            rings.append(
                self._trace_ring(
                    first,
                    remaining=remaining,
                    edges_by_start=edges_by_start,
                )
            )

        return tuple(
            rings,
        )

    def _trace_ring(
        self,
        first: Edge,
        *,
        remaining: set[Edge],
        edges_by_start: dict[
            Point,
            set[Edge],
        ],
    ) -> Ring:
        points = [
            first.start,
        ]
        current = first

        while True:
            remaining.remove(
                current,
            )
            edges_by_start[current.start].remove(
                current,
            )

            points.append(
                current.end,
            )

            if current.end == first.start:
                return tuple(
                    points[:-1],
                )

            next_edges = edges_by_start.get(
                current.end,
            )

            if not next_edges:
                raise InvariantViolationError(
                    "Outline is not closed.",
                )

            current = min(
                next_edges,
                key=lambda edge: (
                    self._turn_priority(
                        current,
                        edge,
                    ),
                    self._edge_sort_key(
                        edge,
                    ),
                ),
            )

    @classmethod
    def _classify_rings(
        cls,
        rings: tuple[Ring, ...],
    ) -> tuple[
        Ring,
        tuple[Ring, ...],
    ]:
        if not rings:
            return (
                (),
                (),
            )

        outer_rings: list[Ring] = []
        hole_rings: list[Ring] = []

        for ring in rings:
            signed_area_twice = cls._signed_area_twice(
                ring,
            )

            if signed_area_twice > 0:
                outer_rings.append(
                    ring,
                )
                continue

            if signed_area_twice < 0:
                hole_rings.append(
                    ring,
                )
                continue

            raise InvariantViolationError(
                "Outline ring has zero area.",
            )

        if len(outer_rings) != 1:
            raise InvariantViolationError(
                "Outline must contain exactly one outer boundary ring.",
            )

        return (
            outer_rings[0],
            tuple(
                sorted(
                    hole_rings,
                    key=lambda ring: (
                        min(
                            ring,
                        ),
                        ring,
                    ),
                )
            ),
        )

    @staticmethod
    def _edge_sort_key(
        edge: Edge,
    ) -> tuple[
        Point,
        Point,
    ]:
        return (
            edge.start,
            edge.end,
        )

    @classmethod
    def _turn_priority(
        cls,
        current: Edge,
        following: Edge,
    ) -> int:
        current_direction = cls._direction_index(
            current,
        )
        following_direction = cls._direction_index(
            following,
        )
        turn = (following_direction - current_direction) % 4

        priorities = {
            1: 0,
            0: 1,
            3: 2,
            2: 3,
        }

        return priorities[turn]

    @staticmethod
    def _direction_index(
        edge: Edge,
    ) -> int:
        direction = (
            edge.end[0] - edge.start[0],
            edge.end[1] - edge.start[1],
        )
        directions = {
            (1, 0): 0,
            (0, 1): 1,
            (-1, 0): 2,
            (0, -1): 3,
        }

        try:
            return directions[direction]
        except KeyError as error:
            raise InvariantViolationError(
                "Outline edge must follow the pixel grid.",
            ) from error

    @staticmethod
    def _signed_area_twice(
        points: Ring,
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

    def _simplify_outline(
        self,
        points: Ring,
    ) -> Ring:
        if len(points) < 3:
            return points

        simplified: list[Point] = []

        count = len(points)

        for index in range(count):
            previous = points[(index - 1) % count]
            current = points[index]
            following = points[(index + 1) % count]

            if (
                previous[0] == current[0] == following[0]
                or previous[1] == current[1] == following[1]
            ):
                continue

            simplified.append(
                current,
            )

        return tuple(
            simplified,
        )
