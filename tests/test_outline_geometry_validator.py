# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.models import Outline
from pbn.outline.geometry_validator import OutlineGeometryValidator


def test_invalid_region_ids_accepts_valid_outline() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 0),
            (2, 2),
            (0, 2),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (outline,),
    )

    assert invalid_region_ids == set()


def test_invalid_region_ids_rejects_degenerate_outline() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (2, 0),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (outline,),
    )

    assert invalid_region_ids == {
        1,
    }


def test_invalid_region_ids_rejects_self_intersecting_outline() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (1, 3),
            (3, 3),
            (0, 1),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (outline,),
    )

    assert invalid_region_ids == {
        1,
    }


def test_invalid_region_ids_marks_both_crossing_regions() -> None:
    first = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 0),
            (2, 2),
            (0, 2),
        ),
    )
    second = Outline(
        region_id=2,
        points=(
            (1, -1),
            (3, -1),
            (3, 1),
            (1, 1),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            first,
            second,
        ),
    )

    assert invalid_region_ids == {
        1,
        2,
    }


def test_invalid_region_ids_accepts_shared_boundary_without_crossing() -> None:
    first = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ),
    )
    second = Outline(
        region_id=2,
        points=(
            (1, 0),
            (2, 0),
            (2, 1),
            (1, 1),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            first,
            second,
        ),
    )

    assert invalid_region_ids == set()


def test_invalid_region_ids_accepts_corner_touching_outlines() -> None:
    first = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ),
    )
    second = Outline(
        region_id=2,
        points=(
            (1, 1),
            (2, 1),
            (2, 2),
            (1, 2),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            first,
            second,
        ),
    )

    assert invalid_region_ids == set()


def test_invalid_region_ids_rejects_contained_region() -> None:
    outer = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )
    inner = Outline(
        region_id=2,
        points=(
            (1, 1),
            (3, 1),
            (3, 3),
            (1, 3),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            outer,
            inner,
        ),
    )

    assert invalid_region_ids == {
        1,
        2,
    }


def test_invalid_region_ids_rejects_contained_region_with_shared_boundary() -> None:
    outer = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )
    inner = Outline(
        region_id=2,
        points=(
            (0, 1),
            (2, 1),
            (2, 3),
            (0, 3),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            outer,
            inner,
        ),
    )

    assert invalid_region_ids == {
        1,
        2,
    }


def test_cross_polygon_segment_candidates_require_bounding_box_overlap() -> None:
    validator = OutlineGeometryValidator()

    first_segments = (
        validator._segment(
            (0, 0),
            (4, 0),
        ),
        validator._segment(
            (0, 4),
            (4, 4),
        ),
    )
    second_segments = (
        validator._segment(
            (2, 0),
            (6, 0),
        ),
        validator._segment(
            (2, 2),
            (6, 2),
        ),
    )

    candidates = tuple(
        validator._cross_polygon_segment_candidates(
            first_segments,
            second_segments,
        )
    )

    assert candidates == (
        (
            first_segments[0],
            second_segments[0],
        ),
    )


def test_self_intersection_segment_candidates_require_bounding_box_overlap() -> None:
    validator = OutlineGeometryValidator()

    segments = (
        validator._segment(
            (0, 0),
            (4, 0),
        ),
        validator._segment(
            (2, 0),
            (2, 4),
        ),
        validator._segment(
            (0, 4),
            (4, 4),
        ),
    )

    candidates = tuple(
        validator._self_intersection_segment_candidates(
            segments,
        )
    )

    assert candidates == (
        (
            0,
            segments[0],
            1,
            segments[1],
        ),
        (
            1,
            segments[1],
            2,
            segments[2],
        ),
    )


def test_point_in_polygon_uses_polygon_bounding_box_check_only_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = OutlineGeometryValidator()
    segments = (
        validator._segment(
            (0, 0),
            (4, 0),
        ),
        validator._segment(
            (4, 0),
            (4, 4),
        ),
        validator._segment(
            (4, 4),
            (0, 4),
        ),
        validator._segment(
            (0, 4),
            (0, 0),
        ),
    )

    bounding_box_check = OutlineGeometryValidator._float_point_within_bounding_box
    call_count = 0

    def counting_bounding_box_check(
        point: tuple[float, float],
        bounding_box: tuple[int, int, int, int],
    ) -> bool:
        nonlocal call_count
        call_count += 1
        return bounding_box_check(
            point,
            bounding_box,
        )

    monkeypatch.setattr(
        OutlineGeometryValidator,
        "_float_point_within_bounding_box",
        staticmethod(
            counting_bounding_box_check,
        ),
    )

    is_inside = validator._point_is_strictly_inside_polygon(
        (2.0, 2.0),
        segments,
        bounding_box=(
            0,
            0,
            4,
            4,
        ),
    )

    assert is_inside is True
    assert call_count == 1


def test_invalid_region_ids_limits_local_validation_to_requested_regions() -> None:
    valid = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ),
    )
    invalid = Outline(
        region_id=2,
        points=(
            (10, 0),
            (11, 0),
            (12, 0),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            valid,
            invalid,
        ),
        region_ids={
            1,
        },
    )

    assert invalid_region_ids == set()


def test_invalid_region_ids_includes_crossing_neighbor_of_requested_region() -> None:
    first = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 0),
            (2, 2),
            (0, 2),
        ),
    )
    second = Outline(
        region_id=2,
        points=(
            (1, -1),
            (3, -1),
            (3, 1),
            (1, 1),
        ),
    )

    invalid_region_ids = OutlineGeometryValidator().invalid_region_ids(
        (
            first,
            second,
        ),
        region_ids={
            1,
        },
    )

    assert invalid_region_ids == {
        1,
        2,
    }
