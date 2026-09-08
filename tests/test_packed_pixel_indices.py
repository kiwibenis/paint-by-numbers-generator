# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import (
    MAXIMUM_COORDINATE,
    ROW_STRIDE,
    pack_pixel,
    pack_pixels,
    unpack_pixel,
    unpack_pixels,
)

_COORDINATES = (
    (0, 0),
    (1, 0),
    (0, 1),
    (7, 3),
    (MAXIMUM_COORDINATE, 0),
    (0, 1000),
)


@pytest.mark.parametrize(
    "coordinate",
    _COORDINATES,
)
def test_packing_round_trips(
    coordinate: tuple[int, int],
) -> None:
    assert (
        unpack_pixel(
            pack_pixel(*coordinate),
        )
        == coordinate
    )


def test_packing_is_injective() -> None:
    coordinates = {(x, y) for x in range(40) for y in range(40)}

    assert len(
        pack_pixels(coordinates),
    ) == len(coordinates)


def test_unpacking_reverses_packing_for_a_collection() -> None:
    coordinates = {(x, y) for x in range(11) for y in range(7)}

    assert (
        set(
            unpack_pixels(
                pack_pixels(coordinates),
            ),
        )
        == coordinates
    )


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (1, (4, 2)),
        (-1, (2, 2)),
        (ROW_STRIDE, (3, 3)),
        (-ROW_STRIDE, (3, 1)),
        (ROW_STRIDE + 1, (4, 3)),
        (-ROW_STRIDE - 1, (2, 1)),
    ],
)
def test_neighbors_are_constant_offsets(
    offset: int,
    expected: tuple[int, int],
) -> None:
    """
    Every consumer on a membership path relies on this identity.
    """
    assert (
        unpack_pixel(
            pack_pixel(3, 2) + offset,
        )
        == expected
    )


def test_a_row_of_a_maximum_width_image_cannot_reach_the_next_row() -> None:
    """
    The stride is what keeps a column from carrying into a row.
    """
    assert pack_pixel(
        MAXIMUM_COORDINATE,
        4,
    ) + 1 == pack_pixel(
        0,
        5,
    )


def test_region_exposes_its_coordinates() -> None:
    coordinates = {
        (0, 0),
        (1, 0),
        (0, 1),
    }

    region = Region(
        id=1,
        color=PaletteColor(
            number=1,
            name="Black",
            rgb=RGB(
                red=0,
                green=0,
                blue=0,
            ),
            lab=Lab(
                l=0.0,
                a=0.0,
                b=0.0,
            ),
        ),
        pixels=pack_pixels(coordinates),
    )

    assert set(region.coordinates()) == coordinates
    assert region.size == len(coordinates)
