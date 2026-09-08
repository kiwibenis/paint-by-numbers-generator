# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import (
    QuantizedImage,
    Region,
)


class RegionDetector:
    """
    Detects connected color regions in a quantized image.
    """

    def detect(
        self,
        image: QuantizedImage,
    ) -> tuple[Region, ...]:
        width = image.width
        height = image.height

        visited = [bytearray(width) for _ in range(height)]

        regions: list[Region] = []

        next_id = 1

        for y in range(height):
            for x in range(width):
                if visited[y][x]:
                    continue

                pixels = self._flood_fill(
                    image,
                    (x, y),
                    visited,
                )

                color = image.color_at(x, y)

                regions.append(
                    Region(
                        id=next_id,
                        color=color,
                        pixels=pixels,
                    ),
                )

                next_id += 1

        return tuple(regions)

    def _flood_fill(
        self,
        image: QuantizedImage,
        start: tuple[int, int],
        visited: list[bytearray],
    ) -> frozenset[int]:
        width = image.width
        height = image.height
        indices = image.indices

        start_x, start_y = start
        start_index = indices[start_y * width + start_x]

        stack = [start]
        visited[start_y][start_x] = 1

        pixels: list[int] = []

        while stack:
            x, y = stack.pop()

            pixels.append(
                (y << 32) | x,
            )

            row_offset = y * width

            if (
                x > 0
                and not visited[y][x - 1]
                and indices[row_offset + x - 1] == start_index
            ):
                visited[y][x - 1] = 1
                stack.append(
                    (x - 1, y),
                )

            if (
                x < width - 1
                and not visited[y][x + 1]
                and indices[row_offset + x + 1] == start_index
            ):
                visited[y][x + 1] = 1
                stack.append(
                    (x + 1, y),
                )

            if (
                y > 0
                and not visited[y - 1][x]
                and indices[row_offset - width + x] == start_index
            ):
                visited[y - 1][x] = 1
                stack.append(
                    (x, y - 1),
                )

            if (
                y < height - 1
                and not visited[y + 1][x]
                and indices[row_offset + width + x] == start_index
            ):
                visited[y + 1][x] = 1
                stack.append(
                    (x, y + 1),
                )

        return frozenset(pixels)
