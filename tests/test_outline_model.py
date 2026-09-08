# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import Outline


def test_outline_defaults_to_no_hole_rings() -> None:
    outline = Outline(
        region_id=7,
        points=(
            (0, 0),
            (2, 0),
            (2, 2),
            (0, 2),
        ),
    )

    assert outline.region_id == 7
    assert outline.points == (
        (0, 0),
        (2, 0),
        (2, 2),
        (0, 2),
    )
    assert outline.hole_rings == ()


def test_outline_stores_hole_rings() -> None:
    outline = Outline(
        region_id=7,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
        hole_rings=(
            (
                (1, 1),
                (2, 1),
                (2, 2),
                (1, 2),
            ),
            (
                (3, 1),
                (4, 1),
                (4, 2),
                (3, 2),
            ),
        ),
    )

    assert outline.hole_rings == (
        (
            (1, 1),
            (2, 1),
            (2, 2),
            (1, 2),
        ),
        (
            (3, 1),
            (4, 1),
            (4, 2),
            (3, 2),
        ),
    )
