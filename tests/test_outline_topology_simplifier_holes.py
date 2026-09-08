# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.models import RGB, Lab, Outline, PaletteColor, Region
from pbn.models.pixel_index import pack_pixels
from pbn.outline.geometry_validator import OutlineGeometryValidator
from pbn.outline.simplifier import DouglasPeuckerSimplifier
from pbn.outline.topology_simplifier import OutlineTopologySimplifier

Point = tuple[int, int]
Ring = tuple[Point, ...]


def _color() -> PaletteColor:
    return PaletteColor(
        number=1,
        name="Test",
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


def _ring_segments(
    ring: Ring,
) -> set[frozenset[Point]]:
    return {
        frozenset(
            (
                ring[index],
                ring[(index + 1) % len(ring)],
            )
        )
        for index in range(
            len(ring),
        )
    }


def test_simplify_preserves_hole_ring() -> None:
    color = _color()
    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (2, 0),
                (0, 1),
                (2, 1),
                (0, 2),
                (1, 2),
                (2, 2),
            },
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (region,),
        tolerance=0.0,
    )

    assert len(outlines) == 1
    assert outlines[0].hole_rings == (
        (
            (1, 1),
            (1, 2),
            (2, 2),
            (2, 1),
        ),
    )


def test_simplify_preserves_shared_closed_hole_boundary() -> None:
    color = _color()
    inner_pixels = frozenset(
        {
            (3, 2),
            (2, 3),
            (3, 3),
            (4, 3),
            (3, 4),
        },
    )
    surrounding_pixels = frozenset(
        (x, y) for y in range(7) for x in range(7) if (x, y) not in inner_pixels
    )
    surrounding = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            surrounding_pixels,
        ),
    )
    inner = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            inner_pixels,
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            surrounding,
            inner,
        ),
        tolerance=1.0,
    )
    by_region = {outline.region_id: outline for outline in outlines}

    assert len(by_region[1].hole_rings) == 1
    assert _ring_segments(
        by_region[1].hole_rings[0],
    ) == _ring_segments(
        by_region[2].points,
    )


def test_simplify_fallback_preserves_shared_closed_hole_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()
    inner_pixels = frozenset(
        {
            (3, 2),
            (2, 3),
            (3, 3),
            (4, 3),
            (3, 4),
        },
    )
    surrounding_pixels = frozenset(
        (x, y) for y in range(7) for x in range(7) if (x, y) not in inner_pixels
    )
    surrounding = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            surrounding_pixels,
        ),
    )
    inner = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            inner_pixels,
        ),
    )

    original_invalid_region_ids = OutlineGeometryValidator.invalid_region_ids
    validation_call_count = 0

    def force_first_simplified_geometry_invalid(
        validator: OutlineGeometryValidator,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[int]:
        nonlocal validation_call_count

        validation_call_count += 1

        if validation_call_count == 2:
            return {
                1,
            }

        return original_invalid_region_ids(
            validator,
            outlines,
            region_ids=region_ids,
        )

    original_simplify = DouglasPeuckerSimplifier.simplify
    shared_ring_tolerances: list[float] = []

    def track_shared_ring_tolerance(
        simplifier: DouglasPeuckerSimplifier,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        x_values = tuple(point[0] for point in outline.points)
        y_values = tuple(point[1] for point in outline.points)

        if (
            min(x_values) == 2
            and min(y_values) == 2
            and max(x_values) == 5
            and max(y_values) == 5
        ):
            shared_ring_tolerances.append(
                tolerance,
            )

        return original_simplify(
            simplifier,
            outline,
            tolerance=tolerance,
        )

    monkeypatch.setattr(
        OutlineGeometryValidator,
        "invalid_region_ids",
        force_first_simplified_geometry_invalid,
    )
    monkeypatch.setattr(
        DouglasPeuckerSimplifier,
        "simplify",
        track_shared_ring_tolerance,
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            surrounding,
            inner,
        ),
        tolerance=1.0,
    )
    by_region = {outline.region_id: outline for outline in outlines}

    assert shared_ring_tolerances == [
        1.0,
        0.5,
    ]
    assert len(by_region[1].hole_rings) == 1
    assert _ring_segments(
        by_region[1].hole_rings[0],
    ) == _ring_segments(
        by_region[2].points,
    )
