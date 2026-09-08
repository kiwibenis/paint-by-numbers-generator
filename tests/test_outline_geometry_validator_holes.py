# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import Outline
from pbn.outline.geometry_validator import OutlineGeometryValidator


def test_overlapping_region_pairs_accepts_region_inside_hole() -> None:
    surrounding = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
        hole_rings=(
            (
                (1, 1),
                (1, 3),
                (3, 3),
                (3, 1),
            ),
        ),
    )
    nested = Outline(
        region_id=2,
        points=(
            (1, 1),
            (3, 1),
            (3, 3),
            (1, 3),
        ),
    )

    overlapping_region_pairs = OutlineGeometryValidator().overlapping_region_pairs(
        (
            surrounding,
            nested,
        ),
    )

    assert overlapping_region_pairs == set()


def test_overlapping_region_pairs_rejects_region_crossing_hole_boundary() -> None:
    surrounding = Outline(
        region_id=1,
        points=(
            (0, 0),
            (6, 0),
            (6, 6),
            (0, 6),
        ),
        hole_rings=(
            (
                (2, 2),
                (2, 4),
                (4, 4),
                (4, 2),
            ),
        ),
    )
    crossing = Outline(
        region_id=2,
        points=(
            (1, 1),
            (3, 1),
            (3, 3),
            (1, 3),
        ),
    )

    overlapping_region_pairs = OutlineGeometryValidator().overlapping_region_pairs(
        (
            surrounding,
            crossing,
        ),
    )

    assert overlapping_region_pairs == {
        (
            1,
            2,
        ),
    }


def test_invalid_outline_region_ids_accepts_valid_hole_rings() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (8, 0),
            (8, 8),
            (0, 8),
        ),
        hole_rings=(
            (
                (1, 1),
                (1, 3),
                (3, 3),
                (3, 1),
            ),
            (
                (5, 5),
                (5, 7),
                (7, 7),
                (7, 5),
            ),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_outline_region_ids(
        (outline,),
    )

    assert invalid_region_ids == set()


def test_invalid_outline_region_ids_rejects_degenerate_hole_ring() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (6, 0),
            (6, 6),
            (0, 6),
        ),
        hole_rings=(
            (
                (1, 1),
                (2, 1),
                (3, 1),
            ),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_outline_region_ids(
        (outline,),
    )

    assert invalid_region_ids == {
        1,
    }


def test_invalid_outline_region_ids_rejects_self_intersecting_hole_ring() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (8, 0),
            (8, 8),
            (0, 8),
        ),
        hole_rings=(
            (
                (1, 1),
                (5, 1),
                (2, 4),
                (4, 4),
                (1, 2),
            ),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_outline_region_ids(
        (outline,),
    )

    assert invalid_region_ids == {
        1,
    }
