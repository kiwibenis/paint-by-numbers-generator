# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.exceptions import InvariantViolationError
from pbn.models import (
    RGB,
    Lab,
    Outline,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.outline import OutlineTracer
from pbn.outline.simplifier import DouglasPeuckerSimplifier
from pbn.outline.topology_simplifier import OutlineTopologySimplifier


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


def _outline_segments(
    outline: Outline,
) -> set[frozenset[tuple[int, int]]]:
    points = outline.points

    return {
        frozenset(
            (
                points[index],
                points[(index + 1) % len(points)],
            )
        )
        for index in range(len(points))
    }


def _signed_area_twice(
    outline: Outline,
) -> int:
    points = outline.points

    return sum(
        (
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
        )
        for index in range(len(points))
    )


def _orientation(
    first: tuple[int, int],
    second: tuple[int, int],
    third: tuple[int, int],
) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (
        third[0] - first[0]
    )


def _point_on_segment(
    point: tuple[int, int],
    start: tuple[int, int],
    end: tuple[int, int],
) -> bool:
    return (
        _orientation(
            start,
            end,
            point,
        )
        == 0
        and min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def _segments_intersect(
    first_start: tuple[int, int],
    first_end: tuple[int, int],
    second_start: tuple[int, int],
    second_end: tuple[int, int],
) -> bool:
    first_orientation = _orientation(
        first_start,
        first_end,
        second_start,
    )
    second_orientation = _orientation(
        first_start,
        first_end,
        second_end,
    )
    third_orientation = _orientation(
        second_start,
        second_end,
        first_start,
    )
    fourth_orientation = _orientation(
        second_start,
        second_end,
        first_end,
    )

    if (
        first_orientation * second_orientation < 0
        and third_orientation * fourth_orientation < 0
    ):
        return True

    if first_orientation == 0 and _point_on_segment(
        second_start,
        first_start,
        first_end,
    ):
        return True

    if second_orientation == 0 and _point_on_segment(
        second_end,
        first_start,
        first_end,
    ):
        return True

    if third_orientation == 0 and _point_on_segment(
        first_start,
        second_start,
        second_end,
    ):
        return True

    return fourth_orientation == 0 and _point_on_segment(
        first_end,
        second_start,
        second_end,
    )


def _has_self_intersection(
    outline: Outline,
) -> bool:
    points = outline.points
    point_count = len(points)

    for first_index in range(point_count):
        first_start = points[first_index]
        first_end = points[(first_index + 1) % point_count]

        for second_index in range(
            first_index + 1,
            point_count,
        ):
            if second_index == first_index + 1:
                continue

            if first_index == 0 and second_index == point_count - 1:
                continue

            second_start = points[second_index]
            second_end = points[(second_index + 1) % point_count]

            if _segments_intersect(
                first_start,
                first_end,
                second_start,
                second_end,
            ):
                return True

    return False


def _outlines_cross_properly(
    first: Outline,
    second: Outline,
) -> bool:
    first_points = first.points
    second_points = second.points

    for first_index in range(
        len(first_points),
    ):
        first_start = first_points[first_index]
        first_end = first_points[(first_index + 1) % len(first_points)]

        for second_index in range(
            len(second_points),
        ):
            second_start = second_points[second_index]
            second_end = second_points[(second_index + 1) % len(second_points)]

            first_orientation = _orientation(
                first_start,
                first_end,
                second_start,
            )
            second_orientation = _orientation(
                first_start,
                first_end,
                second_end,
            )
            third_orientation = _orientation(
                second_start,
                second_end,
                first_start,
            )
            fourth_orientation = _orientation(
                second_start,
                second_end,
                first_end,
            )

            if (
                first_orientation * second_orientation < 0
                and third_orientation * fourth_orientation < 0
            ):
                return True

    return False


def test_simplify_preserves_identical_shared_boundary() -> None:
    color = _color()

    left = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (0, 1),
                (1, 1),
                (2, 1),
                (0, 2),
                (1, 2),
                (0, 3),
                (1, 3),
                (2, 3),
                (0, 4),
                (1, 4),
            },
        ),
    )

    right = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (2, 0),
                (3, 0),
                (4, 0),
                (5, 0),
                (3, 1),
                (4, 1),
                (5, 1),
                (2, 2),
                (3, 2),
                (4, 2),
                (5, 2),
                (3, 3),
                (4, 3),
                (5, 3),
                (2, 4),
                (3, 4),
                (4, 4),
                (5, 4),
            },
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            left,
            right,
        ),
        tolerance=1.1,
    )

    by_region = {outline.region_id: outline for outline in outlines}

    expected_shared_segment = frozenset(
        (
            (2, 0),
            (2, 5),
        )
    )

    assert expected_shared_segment in _outline_segments(
        by_region[1],
    )
    assert expected_shared_segment in _outline_segments(
        by_region[2],
    )


def test_simplify_preserves_isolated_region_geometry() -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (0, 1),
                (1, 1),
            },
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (region,),
        tolerance=1.0,
    )

    assert outlines == (
        Outline(
            region_id=1,
            points=(
                (0, 0),
                (2, 0),
                (2, 2),
                (0, 2),
            ),
        ),
    )


def test_simplify_is_independent_of_region_order() -> None:
    color = _color()

    left = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (0, 1),
                (1, 1),
                (2, 1),
                (0, 2),
                (1, 2),
                (0, 3),
                (1, 3),
                (2, 3),
                (0, 4),
                (1, 4),
            },
        ),
    )

    right = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (2, 0),
                (3, 0),
                (4, 0),
                (5, 0),
                (3, 1),
                (4, 1),
                (5, 1),
                (2, 2),
                (3, 2),
                (4, 2),
                (5, 2),
                (3, 3),
                (4, 3),
                (5, 3),
                (2, 4),
                (3, 4),
                (4, 4),
                (5, 4),
            },
        ),
    )

    simplifier = OutlineTopologySimplifier()

    forward = simplifier.simplify(
        (
            left,
            right,
        ),
        tolerance=1.1,
    )

    reverse = simplifier.simplify(
        (
            right,
            left,
        ),
        tolerance=1.1,
    )

    forward_by_region = {outline.region_id: outline for outline in forward}
    reverse_by_region = {outline.region_id: outline for outline in reverse}

    assert forward_by_region == reverse_by_region


def test_simplify_preserves_at_least_three_distinct_polygon_points() -> None:
    color = _color()

    corner = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    surrounding = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (1, 0),
                (0, 1),
                (1, 1),
            },
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            corner,
            surrounding,
        ),
        tolerance=1.0,
    )

    for outline in outlines:
        assert len(set(outline.points)) >= 3


def test_simplify_preserves_nonzero_polygon_area() -> None:
    color = _color()

    lower = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 4),
                (0, 5),
                (1, 5),
                (2, 4),
                (2, 5),
            },
        ),
    )

    upper = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (0, 3),
                (1, 2),
                (1, 3),
                (2, 3),
            },
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            lower,
            upper,
        ),
        tolerance=2.5,
    )

    for outline in outlines:
        assert _signed_area_twice(outline) != 0


def test_simplify_preserves_non_self_intersecting_polygon() -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (2, 0),
                (2, 1),
                (3, 1),
                (1, 2),
                (2, 2),
            },
        ),
    )

    outlines = OutlineTopologySimplifier().simplify(
        (region,),
        tolerance=1.5,
    )

    assert len(outlines) == 1
    assert not _has_self_intersection(
        outlines[0],
    )


def test_simplify_handles_existing_raster_self_touch() -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (0, 1),
                (0, 2),
                (1, 0),
                (1, 2),
                (2, 0),
                (2, 1),
                (2, 3),
                (3, 1),
                (3, 2),
                (3, 3),
            },
        ),
    )

    tracer = OutlineTracer()

    baseline = tracer.trace(
        region,
    )

    requested = DouglasPeuckerSimplifier().simplify(
        tracer.trace_raw(
            region,
        ),
        tolerance=1.0,
    )

    assert _has_self_intersection(
        baseline,
    )
    assert _has_self_intersection(
        requested,
    )

    outlines = OutlineTopologySimplifier().simplify(
        (region,),
        tolerance=1.0,
    )

    assert len(outlines) == 1
    assert outlines[0].region_id == region.id
    assert outlines[0] != requested
    assert len(outlines[0].points) <= len(
        baseline.points,
    )


def test_simplify_accepts_existing_raster_vertex_touch_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (0, 1),
                (0, 2),
                (1, 0),
                (1, 2),
                (2, 0),
                (2, 1),
                (2, 3),
                (3, 1),
                (3, 2),
                (3, 3),
            },
        ),
    )

    original_simplify = DouglasPeuckerSimplifier.simplify
    tolerances: list[float] = []

    def tracking_simplify(
        simplifier: DouglasPeuckerSimplifier,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        tolerances.append(
            tolerance,
        )

        return original_simplify(
            simplifier,
            outline,
            tolerance=tolerance,
        )

    monkeypatch.setattr(
        DouglasPeuckerSimplifier,
        "simplify",
        tracking_simplify,
    )

    OutlineTopologySimplifier().simplify(
        (region,),
        tolerance=0.0,
    )

    assert tolerances == [
        0.0,
    ]


def test_simplify_preserves_valid_isolated_region_when_another_falls_back() -> None:
    color = _color()

    invalid_region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (0, 1),
                (0, 2),
                (1, 0),
                (1, 2),
                (2, 0),
                (2, 1),
                (2, 3),
                (3, 1),
                (3, 2),
                (3, 3),
            },
        ),
    )

    valid_region = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (10, 0),
                (11, 0),
                (12, 0),
                (12, 1),
                (12, 2),
            },
        ),
    )

    tracer = OutlineTracer()

    requested_invalid = DouglasPeuckerSimplifier().simplify(
        tracer.trace_raw(
            invalid_region,
        ),
        tolerance=1.0,
    )

    expected_valid = DouglasPeuckerSimplifier().simplify(
        tracer.trace_raw(
            valid_region,
        ),
        tolerance=1.0,
    )

    valid_baseline = tracer.trace(
        valid_region,
    )

    assert expected_valid != valid_baseline

    outlines = OutlineTopologySimplifier().simplify(
        (
            invalid_region,
            valid_region,
        ),
        tolerance=1.0,
    )

    by_region = {outline.region_id: outline for outline in outlines}

    assert by_region[1] != requested_invalid
    assert by_region[2] == expected_valid


def test_simplify_does_not_introduce_crossing_between_regions() -> None:
    color = _color()

    first_region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 4),
                (0, 5),
                (1, 3),
                (1, 4),
                (2, 3),
                (3, 0),
                (3, 1),
                (3, 2),
                (3, 3),
                (4, 2),
            },
        ),
    )

    second_region = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (2, 5),
            },
        ),
    )

    tracer = OutlineTracer()

    first_baseline = tracer.trace(
        first_region,
    )
    second_baseline = tracer.trace(
        second_region,
    )

    assert not _outlines_cross_properly(
        first_baseline,
        second_baseline,
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            first_region,
            second_region,
        ),
        tolerance=1.0,
    )

    by_region = {outline.region_id: outline for outline in outlines}

    assert not _has_self_intersection(
        by_region[1],
    )
    assert not _has_self_intersection(
        by_region[2],
    )
    assert not _outlines_cross_properly(
        by_region[1],
        by_region[2],
    )


def test_simplify_reduces_tolerance_before_zero_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    invalid_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 1),
            (0, 1),
            (1, 0),
        ),
    )

    valid_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ),
    )

    tolerances: list[float] = []

    def fake_simplify(
        simplifier: DouglasPeuckerSimplifier,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        del simplifier
        del outline

        tolerances.append(
            tolerance,
        )

        if tolerance > 0.25:
            return invalid_outline

        return valid_outline

    monkeypatch.setattr(
        DouglasPeuckerSimplifier,
        "simplify",
        fake_simplify,
    )

    outlines = OutlineTopologySimplifier().simplify(
        (region,),
        tolerance=1.0,
    )

    assert outlines == (valid_outline,)
    assert tolerances == [
        1.0,
        0.5,
        0.25,
    ]


def test_simplify_raises_before_simplification_when_raw_geometry_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    invalid_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 1),
            (0, 1),
            (1, 0),
        ),
    )

    simplification_called = False

    def invalid_trace_raw(
        tracer: OutlineTracer,
        traced_region: Region,
    ) -> Outline:
        del tracer
        del traced_region

        return invalid_outline

    def tracking_simplify(
        simplifier: DouglasPeuckerSimplifier,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        nonlocal simplification_called

        del simplifier
        del tolerance

        simplification_called = True

        return outline

    monkeypatch.setattr(
        OutlineTracer,
        "trace_raw",
        invalid_trace_raw,
    )
    monkeypatch.setattr(
        DouglasPeuckerSimplifier,
        "simplify",
        tracking_simplify,
    )

    with pytest.raises(
        InvariantViolationError,
        match=(
            r"Outline tracing produced invalid polygon geometry "
            r"for region ids: \[1\]\."
        ),
    ):
        OutlineTopologySimplifier().simplify(
            (region,),
            tolerance=1.0,
        )

    assert not simplification_called


def test_simplify_raises_when_geometry_remains_invalid_at_zero_tolerance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()

    region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    invalid_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 1),
            (0, 1),
            (1, 0),
        ),
    )

    tolerances: list[float] = []

    def always_invalid_simplify(
        simplifier: DouglasPeuckerSimplifier,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        del simplifier
        del outline

        tolerances.append(
            tolerance,
        )

        return invalid_outline

    monkeypatch.setattr(
        DouglasPeuckerSimplifier,
        "simplify",
        always_invalid_simplify,
    )

    with pytest.raises(
        InvariantViolationError,
        match=r"region ids: \[1\]",
    ):
        OutlineTopologySimplifier().simplify(
            (region,),
            tolerance=1.0,
        )

    assert tolerances == [
        1.0,
        0.5,
        0.25,
        0.125,
        0.0,
    ]
