# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.models import Outline
from pbn.outline.simplifier import DouglasPeuckerSimplifier


def test_simplifier_preserves_outline_identity() -> None:
    outline = Outline(
        region_id=7,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=0.5,
    )

    assert simplified.region_id == 7


def test_simplifier_preserves_rectangle_corners() -> None:
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
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=0.5,
    )

    assert simplified == Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )


def test_simplifier_removes_point_within_tolerance() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 1),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=1.1,
    )

    assert simplified == Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )


def test_simplifier_preserves_point_outside_tolerance() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 2),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=1.0,
    )

    assert (2, 2) in simplified.points


def test_simplifier_preserves_triangle() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (2, 4),
        ),
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=100.0,
    )

    assert simplified == outline


def test_simplifier_preserves_empty_outline() -> None:
    outline = Outline(
        region_id=1,
        points=(),
    )

    simplified = DouglasPeuckerSimplifier().simplify(
        outline,
        tolerance=1.0,
    )

    assert simplified == outline


def test_simplifier_rejects_negative_tolerance() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    with pytest.raises(
        ValueError,
        match="tolerance must not be negative",
    ):
        DouglasPeuckerSimplifier().simplify(
            outline,
            tolerance=-0.1,
        )


def test_simplifier_is_deterministic() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (2, 1),
            (3, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    simplifier = DouglasPeuckerSimplifier()

    first = simplifier.simplify(
        outline,
        tolerance=1.0,
    )
    second = simplifier.simplify(
        outline,
        tolerance=1.0,
    )

    assert first == second


def test_simplifier_simplifies_open_chain() -> None:
    points = (
        (2, 0),
        (2, 1),
        (3, 1),
        (3, 2),
        (2, 2),
        (2, 3),
        (3, 3),
        (3, 4),
        (2, 4),
        (2, 5),
    )

    simplified = DouglasPeuckerSimplifier().simplify_open_chain(
        points,
        tolerance=1.1,
    )

    assert simplified == (
        (2, 0),
        (2, 5),
    )


def test_simplifier_rejects_negative_open_chain_tolerance() -> None:
    with pytest.raises(
        ValueError,
        match="tolerance must not be negative",
    ):
        DouglasPeuckerSimplifier().simplify_open_chain(
            (
                (0, 0),
                (1, 0),
            ),
            tolerance=-0.1,
        )
