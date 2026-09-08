# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions import RegionAdjacency


def _color(
    number: int,
    name: str,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=name,
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
    )


def test_detect_adjacent_regions() -> None:
    black = PaletteColor(
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
    )

    white = PaletteColor(
        number=2,
        name="White",
        rgb=RGB(
            red=255,
            green=255,
            blue=255,
        ),
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    left = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )

    right = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (2, 0),
                (3, 0),
            },
        ),
    )

    adjacency = RegionAdjacency()

    neighbors = adjacency.neighbors(
        (
            left,
            right,
        ),
    )

    assert neighbors == {
        1: {2},
        2: {1},
    }


def test_detect_non_adjacent_regions() -> None:
    black = PaletteColor(
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
    )

    white = PaletteColor(
        number=2,
        name="White",
        rgb=RGB(
            red=255,
            green=255,
            blue=255,
        ),
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    left = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )

    right = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (4, 0),
                (5, 0),
            },
        ),
    )

    adjacency = RegionAdjacency()

    neighbors = adjacency.neighbors(
        (
            left,
            right,
        ),
    )

    assert neighbors == {
        1: set(),
        2: set(),
    }


def test_shared_border_lengths() -> None:
    black = PaletteColor(
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
    )

    white = PaletteColor(
        number=2,
        name="White",
        rgb=RGB(
            red=255,
            green=255,
            blue=255,
        ),
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    left = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (0, 1),
                (1, 1),
            },
        ),
    )

    right = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (2, 0),
                (2, 1),
            },
        ),
    )

    adjacency = RegionAdjacency()

    borders = adjacency.shared_borders(
        (
            left,
            right,
        ),
    )

    assert borders == {
        1: {
            2: 2,
        },
        2: {
            1: 2,
        },
    }


def test_shared_borders_reports_disjoint_regions() -> None:
    color = _color(
        number=1,
        name="Test",
    )

    left = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    right = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (1, 0),
            },
        ),
    )

    adjacency = RegionAdjacency()

    borders, has_overlap = adjacency.shared_borders_with_overlap_status(
        (
            left,
            right,
        ),
    )

    assert borders == {
        1: {2: 1},
        2: {1: 1},
    }
    assert not has_overlap


def test_detect_adjacency_between_multiple_regions() -> None:
    color = _color(
        number=1,
        name="Test",
    )

    left = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    center = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (1, 0),
            },
        ),
    )

    right = Region(
        id=3,
        color=color,
        pixels=pack_pixels(
            {
                (2, 0),
            },
        ),
    )

    isolated = Region(
        id=4,
        color=color,
        pixels=pack_pixels(
            {
                (10, 10),
            },
        ),
    )

    adjacency = RegionAdjacency()

    assert adjacency.neighbors(
        (
            right,
            isolated,
            left,
            center,
        ),
    ) == {
        1: {2},
        2: {1, 3},
        3: {2},
        4: set(),
    }

    assert adjacency.shared_borders(
        (
            right,
            isolated,
            left,
            center,
        ),
    ) == {
        1: {2: 1},
        2: {1: 1, 3: 1},
        3: {2: 1},
        4: {},
    }


def test_adjacency_preserves_overlapping_region_behavior() -> None:
    color = _color(
        number=1,
        name="Test",
    )

    first = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )

    second = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (1, 0),
                (2, 0),
            },
        ),
    )

    adjacency = RegionAdjacency()

    assert adjacency.neighbors(
        (
            first,
            second,
        ),
    ) == {
        1: {2},
        2: {1},
    }

    assert adjacency.shared_borders(
        (
            first,
            second,
        ),
    ) == {
        1: {2: 2},
        2: {1: 2},
    }

    borders, has_overlap = adjacency.shared_borders_with_overlap_status(
        (
            first,
            second,
        ),
    )

    assert borders == {
        1: {2: 2},
        2: {1: 2},
    }
    assert has_overlap
