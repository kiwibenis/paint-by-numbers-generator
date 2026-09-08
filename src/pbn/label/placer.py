# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from array import array
from collections.abc import Iterable
from math import hypot

from pbn.models import Label, Region
from pbn.models.pixel_index import (
    MAXIMUM_COORDINATE,
    ROW_STRIDE,
)


class LabelPlacer:
    """
    Places labels inside regions.
    """

    _MAX_DISTANCE_TRANSFORM_BYTES = 16 * 1024 * 1024
    _DISTANCE_VALUE_BYTES = array("q").itemsize

    def place(
        self,
        regions: tuple[Region, ...],
    ) -> tuple[Label, ...]:
        return tuple(self._place(region) for region in regions)

    def _place(
        self,
        region: Region,
    ) -> Label:
        position = self._best_position(region)

        return Label(
            region_id=region.id,
            text=str(region.color.number),
            position=position,
        )

    def _best_position(
        self,
        region: Region,
    ) -> tuple[float, float]:
        (
            boundary_pixels,
            min_x,
            max_x,
            min_y,
            max_y,
            center,
        ) = self._region_geometry(
            region.pixels,
        )

        width = max_x - min_x + 1
        height = max_y - min_y + 1
        bounding_box_area = width * height

        interior_pixel_count = len(region.pixels) - len(boundary_pixels)

        distances: array[int] | None = None

        if self._should_use_distance_transform(
            bounding_box_area=bounding_box_area,
            interior_pixel_count=interior_pixel_count,
            boundary_pixel_count=len(boundary_pixels),
        ):
            distances = self._distance_transform(
                boundary_pixels=boundary_pixels,
                min_x=min_x,
                min_y=min_y,
                width=width,
                height=height,
            )

        best_pixel = self._select_best_pixel(
            region_pixels=region.coordinates(),
            boundary_pixels=boundary_pixels,
            center=center,
            distances=distances,
            min_x=min_x,
            min_y=min_y,
            width=width,
        )

        return (
            float(best_pixel[0]),
            float(best_pixel[1]),
        )

    def _region_geometry(
        self,
        region_pixels: frozenset[int],
    ) -> tuple[
        frozenset[tuple[int, int]],
        int,
        int,
        int,
        int,
        tuple[float, float],
    ]:
        """
        Return the boundary, the bounding box, and the centroid.

        The eight-neighborhood test runs on the packed indices, because
        that turns each of the eight probes into an integer addition.
        The boundary is returned as coordinates, because every consumer
        of it works in raster space.
        """
        first = next(iter(region_pixels))

        min_x = first & MAXIMUM_COORDINATE
        max_x = min_x
        min_y = first >> 32
        max_y = min_y

        sum_x = 0
        sum_y = 0

        boundary_pixels: set[tuple[int, int]] = set()

        above = ROW_STRIDE
        above_left = ROW_STRIDE + 1
        above_right = ROW_STRIDE - 1

        for pixel in region_pixels:
            x = pixel & MAXIMUM_COORDINATE
            y = pixel >> 32

            sum_x += x
            sum_y += y

            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x

            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y

            if (
                pixel - above_left not in region_pixels
                or pixel - above not in region_pixels
                or pixel - above_right not in region_pixels
                or pixel - 1 not in region_pixels
                or pixel + 1 not in region_pixels
                or pixel + above_right not in region_pixels
                or pixel + above not in region_pixels
                or pixel + above_left not in region_pixels
            ):
                boundary_pixels.add(
                    (
                        x,
                        y,
                    ),
                )

        count = len(region_pixels)

        center = (
            sum_x / count,
            sum_y / count,
        )

        return (
            frozenset(boundary_pixels),
            min_x,
            max_x,
            min_y,
            max_y,
            center,
        )

    def _should_use_distance_transform(
        self,
        *,
        bounding_box_area: int,
        interior_pixel_count: int,
        boundary_pixel_count: int,
    ) -> bool:
        """
        Choose between the distance transform and pairwise distances.

        Two refusals, and they are not alike. The work comparison at the
        end picks whichever is cheaper, which for a small region is the
        pairwise scan. The memory refusal above it is a bound on the
        transform's array and hands the region to the pairwise scan
        regardless of what that costs.

        **That second refusal is a cliff, and it is measured.** The
        pairwise scan is `interior x boundary`, and a region large enough
        to trip the memory bound is large in all three of bounding box,
        interior and boundary at once, so it is handed the worst
        algorithm exactly where it hurts most. Complete generation of a
        `checkerboard` at 1,998,216 pixels takes 46.9 s; at 2,198,334
        pixels it exceeds 400 s, and at 2,392,744 pixels it took 1924 s
        on another machine, with every stack sample over 32 minutes
        inside `_squared_border_distance`.

        `_MAX_DISTANCE_TRANSFORM_BYTES` divided by `_DISTANCE_VALUE_BYTES`
        puts the cliff at a bounding box of 2,097,152 pixels.

        **It is unreachable at the processing resolution of ADR-0016.** A
        bounding box cannot exceed the image, and at 1.6 megapixels the
        whole image is smaller than the cliff. Nothing here is reached on
        any input this project accepts today.

        It is left as it is deliberately. Raising the processing
        resolution above 2.097 megapixels walks into it, which is why
        `docs/adversarial-input-measurements.md` says a deployment
        raising that resolution has to measure rather than extrapolate.
        """
        if interior_pixel_count == 0:
            return False

        distance_transform_bytes = bounding_box_area * self._DISTANCE_VALUE_BYTES

        if distance_transform_bytes > self._MAX_DISTANCE_TRANSFORM_BYTES:
            return False

        brute_force_comparisons = interior_pixel_count * boundary_pixel_count

        distance_transform_work = 2 * bounding_box_area + boundary_pixel_count

        return distance_transform_work <= brute_force_comparisons

    def _select_best_pixel(
        self,
        *,
        region_pixels: Iterable[tuple[int, int]],
        boundary_pixels: frozenset[tuple[int, int]],
        center: tuple[float, float],
        distances: array[int] | None,
        min_x: int,
        min_y: int,
        width: int,
    ) -> tuple[int, int]:
        def key(
            pixel: tuple[int, int],
        ) -> tuple[int, float, int, int]:
            if distances is None:
                border_distance = self._squared_border_distance(
                    pixel,
                    boundary_pixels,
                )
            else:
                distance_index = (pixel[1] - min_y) * width + pixel[0] - min_x
                border_distance = distances[distance_index]

            return (
                -border_distance,
                hypot(
                    pixel[0] - center[0],
                    pixel[1] - center[1],
                ),
                pixel[1],
                pixel[0],
            )

        return min(
            region_pixels,
            key=key,
        )

    def _squared_border_distance(
        self,
        pixel: tuple[int, int],
        boundary_pixels: frozenset[tuple[int, int]],
    ) -> int:
        if pixel in boundary_pixels:
            return 0

        x, y = pixel

        return min(
            (x - boundary_x) ** 2 + (y - boundary_y) ** 2
            for boundary_x, boundary_y in boundary_pixels
        )

    def _distance_transform(
        self,
        *,
        boundary_pixels: frozenset[tuple[int, int]],
        min_x: int,
        min_y: int,
        width: int,
        height: int,
    ) -> array[int]:
        infinite_distance = (width - 1) ** 2 + (height - 1) ** 2 + 1

        distances = array(
            "q",
            [
                infinite_distance,
            ],
        ) * (width * height)

        for x, y in boundary_pixels:
            index = (y - min_y) * width + x - min_x
            distances[index] = 0

        for y in range(height):
            row_start = y * width

            nearest_boundary = -1

            for x in range(width):
                index = row_start + x

                if distances[index] == 0:
                    nearest_boundary = x
                elif nearest_boundary >= 0:
                    difference = x - nearest_boundary
                    distances[index] = difference * difference

            nearest_boundary = width

            for x in range(
                width - 1,
                -1,
                -1,
            ):
                index = row_start + x

                if distances[index] == 0:
                    nearest_boundary = x
                elif nearest_boundary < width:
                    difference = nearest_boundary - x
                    squared_distance = difference * difference

                    distances[index] = min(distances[index], squared_distance)

        (
            nearest_positions,
            boundaries,
            result,
        ) = self._distance_transform_work_buffers(
            height,
        )

        for x in range(width):
            column = array(
                "q",
                (distances[y * width + x] for y in range(height)),
            )

            transformed_column = self._distance_transform_1d(
                column,
                nearest_positions=nearest_positions,
                boundaries=boundaries,
                result=result,
            )

            for y, distance in enumerate(
                transformed_column,
            ):
                distances[y * width + x] = distance

        return distances

    def _distance_transform_work_buffers(
        self,
        length: int,
    ) -> tuple[
        array[int],
        array[float],
        array[int],
    ]:
        nearest_positions = (
            array(
                "q",
                [
                    0,
                ],
            )
            * length
        )

        boundaries = array(
            "d",
            [
                0.0,
            ],
        ) * (length + 1)

        result = (
            array(
                "q",
                [
                    0,
                ],
            )
            * length
        )

        return (
            nearest_positions,
            boundaries,
            result,
        )

    def _distance_transform_1d(
        self,
        values: array[int],
        *,
        nearest_positions: array[int],
        boundaries: array[float],
        result: array[int],
    ) -> array[int]:
        length = len(values)

        envelope_index = 0
        nearest_positions[0] = 0
        boundaries[0] = float("-inf")
        boundaries[1] = float("inf")

        for position in range(1, length):
            previous_position = nearest_positions[envelope_index]

            intersection = (
                (values[position] + position * position)
                - (values[previous_position] + previous_position * previous_position)
            ) / (2 * (position - previous_position))

            while intersection <= boundaries[envelope_index]:
                envelope_index -= 1
                previous_position = nearest_positions[envelope_index]

                intersection = (
                    (values[position] + position * position)
                    - (
                        values[previous_position]
                        + previous_position * previous_position
                    )
                ) / (2 * (position - previous_position))

            envelope_index += 1
            nearest_positions[envelope_index] = position
            boundaries[envelope_index] = intersection
            boundaries[envelope_index + 1] = float("inf")

        envelope_index = 0

        for position in range(length):
            while boundaries[envelope_index + 1] < position:
                envelope_index += 1

            nearest_position = nearest_positions[envelope_index]
            difference = position - nearest_position

            result[position] = difference * difference + values[nearest_position]

        return result
