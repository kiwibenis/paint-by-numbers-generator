# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import builtins
import sys

import pytest
from shapely.geometry.base import BaseGeometry

from pbn.exceptions import (
    GeometryAccelerationError,
    GeometryUnavailableError,
)
from pbn.infrastructure.overlap_detector_factory import (
    build_overlap_detector,
)
from pbn.infrastructure.shapely_overlap_detector import (
    ShapelyOverlapDetector,
)
from pbn.models import Outline
from pbn.outline.geometry_validator import OutlineGeometryValidator


def _reference(
    outlines: tuple[Outline, ...],
    *,
    region_ids: set[int] | None = None,
) -> set[tuple[int, int]]:
    return OutlineGeometryValidator().overlapping_region_pairs(
        outlines,
        region_ids=region_ids,
    )


def _accelerated(
    outlines: tuple[Outline, ...],
    *,
    region_ids: set[int] | None = None,
) -> set[tuple[int, int]]:
    return OutlineGeometryValidator(
        overlap_detector=ShapelyOverlapDetector(),
    ).overlapping_region_pairs(
        outlines,
        region_ids=region_ids,
    )


_SEPARATE = (
    Outline(region_id=1, points=((0, 0), (2, 0), (2, 2), (0, 2))),
    Outline(region_id=2, points=((5, 5), (7, 5), (7, 7), (5, 7))),
)

_SHARED_EDGE = (
    Outline(region_id=1, points=((0, 0), (2, 0), (2, 2), (0, 2))),
    Outline(region_id=2, points=((2, 0), (4, 0), (4, 2), (2, 2))),
)

_SHARED_CORNER = (
    Outline(region_id=1, points=((0, 0), (2, 0), (2, 2), (0, 2))),
    Outline(region_id=2, points=((2, 2), (4, 2), (4, 4), (2, 4))),
)

_OVERLAPPING = (
    Outline(region_id=1, points=((0, 0), (3, 0), (3, 3), (0, 3))),
    Outline(region_id=2, points=((2, 2), (5, 2), (5, 5), (2, 5))),
)

_RING = Outline(
    region_id=1,
    points=((0, 0), (10, 0), (10, 10), (0, 10)),
    hole_rings=((((3, 3), (3, 7), (7, 7), (7, 3))),),
)

_NESTED_IN_HOLE = (
    _RING,
    Outline(region_id=2, points=((4, 4), (6, 4), (6, 6), (4, 6))),
)

_CROSSING_HOLE_BOUNDARY = (
    _RING,
    Outline(region_id=2, points=((4, 4), (9, 4), (9, 6), (4, 6))),
)

_MULTI_HOLE = Outline(
    region_id=1,
    points=((0, 0), (20, 0), (20, 10), (0, 10)),
    hole_rings=(
        ((2, 2), (2, 5), (5, 5), (5, 2)),
        ((8, 2), (8, 5), (11, 5), (11, 2)),
    ),
)

_TWO_ISLANDS = (
    _MULTI_HOLE,
    Outline(region_id=2, points=((3, 3), (4, 3), (4, 4), (3, 4))),
    Outline(region_id=3, points=((9, 3), (10, 3), (10, 4), (9, 4))),
)

_RASTER_SELF_TOUCH = (
    Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (2, 0),
            (3, 0),
            (3, 1),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (3, 4),
            (2, 4),
            (2, 3),
            (3, 3),
            (3, 2),
            (2, 2),
            (2, 1),
            (1, 1),
            (1, 2),
            (2, 2),
            (2, 3),
            (1, 3),
            (0, 3),
            (0, 2),
            (0, 1),
        ),
    ),
    Outline(region_id=2, points=((4, 0), (6, 0), (6, 4), (4, 4))),
)


@pytest.mark.parametrize(
    "outlines",
    [
        _SEPARATE,
        _SHARED_EDGE,
        _SHARED_CORNER,
        _OVERLAPPING,
        _NESTED_IN_HOLE,
        _CROSSING_HOLE_BOUNDARY,
        _TWO_ISLANDS,
        _RASTER_SELF_TOUCH,
    ],
)
def test_accelerated_detection_matches_reference(
    outlines: tuple[Outline, ...],
) -> None:
    assert _accelerated(outlines) == _reference(outlines)


def test_touching_outlines_do_not_overlap() -> None:
    assert _accelerated(_SHARED_EDGE) == set()
    assert _accelerated(_SHARED_CORNER) == set()


def test_positive_area_overlap_is_detected() -> None:
    assert _accelerated(_OVERLAPPING) == {(1, 2)}


def test_region_nested_in_hole_is_not_an_overlap() -> None:
    assert _accelerated(_NESTED_IN_HOLE) == set()


def test_region_crossing_hole_boundary_overlaps() -> None:
    assert _accelerated(_CROSSING_HOLE_BOUNDARY) == {(1, 2)}


def test_tolerated_raster_self_touch_is_not_an_overlap() -> None:
    assert _accelerated(_RASTER_SELF_TOUCH) == set()


def test_region_filter_matches_reference() -> None:
    region_ids = {1}

    assert _accelerated(
        _OVERLAPPING,
        region_ids=region_ids,
    ) == _reference(
        _OVERLAPPING,
        region_ids=region_ids,
    )


def test_region_filter_excludes_unrelated_pairs() -> None:
    assert (
        _accelerated(
            _OVERLAPPING,
            region_ids={3},
        )
        == set()
    )


def test_detection_is_deterministic_across_runs() -> None:
    first = _accelerated(_TWO_ISLANDS)
    second = _accelerated(_TWO_ISLANDS)

    assert first == second


def test_empty_and_single_outline_inputs_are_handled() -> None:
    assert _accelerated(()) == set()
    assert _accelerated((_SEPARATE[0],)) == set()


def test_outlines_without_points_are_ignored() -> None:
    outlines = (
        Outline(region_id=1, points=()),
        _SEPARATE[0],
    )

    assert _accelerated(outlines) == _reference(outlines)


def test_minimum_overlap_area_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ShapelyOverlapDetector(
            minimum_overlap_area=0.0,
        )


def test_area_changing_repair_is_rejected() -> None:
    class _AreaChangingDetector(ShapelyOverlapDetector):
        @staticmethod
        def _to_polygon(outline: Outline) -> BaseGeometry:
            raise GeometryAccelerationError(
                "Geometry repair changed the enclosed area for region "
                f"{outline.region_id}.",
            )

    with pytest.raises(GeometryAccelerationError):
        _AreaChangingDetector().overlapping_region_pairs(
            _OVERLAPPING,
        )


def test_factory_returns_a_detector() -> None:
    assert build_overlap_detector() is not None


def _break_geometry_import(
    monkeypatch: pytest.MonkeyPatch,
    failure: ImportError,
) -> None:
    """
    Make importing the geometry library raise the given failure.

    The detector module is dropped from the cache first, so the factory
    performs a real import rather than finding the earlier one.
    """
    original_import = builtins.__import__

    def _failing_import(  # type: ignore[no-untyped-def]
        name,
        globals=None,
        locals=None,
        fromlist=(),
        level=0,
    ):
        if name.startswith("shapely"):
            raise failure

        return original_import(
            name,
            globals,
            locals,
            fromlist,
            level,
        )

    monkeypatch.delitem(
        sys.modules,
        "pbn.infrastructure.shapely_overlap_detector",
        raising=False,
    )
    monkeypatch.setattr(
        builtins,
        "__import__",
        _failing_import,
    )


def test_factory_raises_when_the_geometry_library_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A missing mandatory dependency must fail, not degrade.

    ADR-0015 defines the accelerated implementation as the supported
    production path. The pure Python implementation remains available
    only as reference behavior for tests and developer diagnostics.
    """
    _break_geometry_import(
        monkeypatch,
        ModuleNotFoundError(
            "No module named 'shapely'",
            name="shapely",
        ),
    )

    with pytest.raises(GeometryUnavailableError) as caught:
        build_overlap_detector()

    assert "not installed" in caught.value.diagnostic_message


def test_factory_distinguishes_a_dependency_of_the_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An absent library is an installation fault. A missing module beneath
    a present one is an environment fault, and calls for other action.
    """
    _break_geometry_import(
        monkeypatch,
        ModuleNotFoundError(
            "No module named 'numpy'",
            name="numpy",
        ),
    )

    with pytest.raises(GeometryUnavailableError) as caught:
        build_overlap_detector()

    assert "numpy" in caught.value.diagnostic_message
    assert "not installed" not in caught.value.diagnostic_message


def test_factory_distinguishes_a_library_that_fails_to_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A present library that raises on import is neither of the above.
    """
    _break_geometry_import(
        monkeypatch,
        ImportError(
            "Incompatible GEOS version.",
        ),
    )

    with pytest.raises(GeometryUnavailableError) as caught:
        build_overlap_detector()

    assert "could not be loaded" in caught.value.diagnostic_message


def test_the_reference_path_remains_available_to_tests() -> None:
    """
    The reference implementation remains available for differential tests
    and developer diagnostics, not as a production fallback, as required
    by ADR-0015.
    """
    validator = OutlineGeometryValidator(
        overlap_detector=None,
    )

    assert validator.overlapping_region_pairs(
        _OVERLAPPING,
    ) == {(1, 2)}


def test_validator_without_detector_uses_reference() -> None:
    validator = OutlineGeometryValidator()

    assert validator.overlapping_region_pairs(
        _OVERLAPPING,
    ) == OutlineGeometryValidator.reference_overlapping_region_pairs(
        _OVERLAPPING,
    )
