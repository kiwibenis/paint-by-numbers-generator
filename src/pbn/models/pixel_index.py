# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterable, Iterator

ROW_STRIDE = 1 << 32
"""
Distance between vertically adjacent pixel indices.

The stride is a power of two above any supported image width, so packing
is a shift rather than a multiplication and no coordinate can carry into
the row part.
"""

MAXIMUM_COORDINATE = ROW_STRIDE - 1


def pack_pixel(
    x: int,
    y: int,
) -> int:
    """
    Pack one pixel coordinate into a single integer.

    A set of integers costs less memory than a set of coordinate tuples
    and is faster to probe, because a neighbor is reached by integer
    arithmetic rather than by building a tuple.

    Both coordinates must be non-negative and at most
    `MAXIMUM_COORDINATE`. That holds for every raster coordinate, and the
    precondition is not checked here, because this function sits on the
    hottest path in the program.
    """
    return (y << 32) | x


def unpack_pixel(
    value: int,
) -> tuple[int, int]:
    """
    Return the coordinate a packed pixel index refers to.
    """
    return (
        value & MAXIMUM_COORDINATE,
        value >> 32,
    )


def pack_pixels(
    coordinates: Iterable[tuple[int, int]],
) -> frozenset[int]:
    """
    Pack a collection of coordinates.
    """
    return frozenset((y << 32) | x for x, y in coordinates)


def unpack_pixels(
    values: Iterable[int],
) -> Iterator[tuple[int, int]]:
    """
    Iterate the coordinates a collection of packed indices refers to.
    """
    for value in values:
        yield (
            value & MAXIMUM_COORDINATE,
            value >> 32,
        )
