# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import Outline
from pbn.outline.simplifier import DouglasPeuckerSimplifier


def test_simplify_preserves_and_simplifies_hole_rings() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 0),
            (4, 0),
            (4, 2),
            (4, 4),
            (2, 4),
            (0, 4),
            (0, 2),
        ),
        hole_rings=(
            (
                (1, 1),
                (2, 1),
                (3, 1),
                (3, 2),
                (3, 3),
                (2, 3),
                (1, 3),
                (1, 2),
            ),
        ),
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=0.0,
    )

    assert simplified.points == (
        (0, 0),
        (4, 0),
        (4, 4),
        (0, 4),
    )
    assert simplified.hole_rings == (
        (
            (1, 1),
            (3, 1),
            (3, 3),
            (1, 3),
        ),
    )
