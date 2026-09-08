# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.exceptions import InvariantViolationError
from pbn.models import (
    RGB,
    Edge,
    Lab,
    Outline,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.outline import OutlineTracer
from pbn.outline.geometry_validator import OutlineGeometryValidator


def test_outline_tracer_exists() -> None:
    tracer = OutlineTracer()

    assert tracer is not None


def test_trace_single_pixel_outline() -> None:
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

    region = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    tracer = OutlineTracer()

    outline = tracer.trace(
        region,
    )

    assert outline == Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ),
    )


def test_trace_two_pixel_outline() -> None:
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

    region = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )

    tracer = OutlineTracer()

    outline = tracer.trace(
        region,
    )

    assert outline == Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 0),
            (2, 1),
            (0, 1),
        ),
    )


def test_trace_concave_region_outline() -> None:
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

    region = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
                (0, 1),
                (1, 1),
            },
        ),
    )

    outline = OutlineTracer().trace(
        region,
    )

    assert outline == Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (2, 1),
            (2, 2),
            (0, 2),
        ),
    )


def test_trace_raw_preserves_grid_boundary_vertices() -> None:
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

    region = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )

    outline = OutlineTracer().trace_raw(
        region,
    )

    assert outline == Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (2, 0),
            (2, 1),
            (1, 1),
            (0, 1),
        ),
    )


def test_trace_raw_records_outer_and_hole_rings() -> None:
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
    region = Region(
        id=1,
        color=black,
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

    outline = OutlineTracer().trace_raw(
        region,
    )

    assert outline.points == (
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 0),
        (3, 1),
        (3, 2),
        (3, 3),
        (2, 3),
        (1, 3),
        (0, 3),
        (0, 2),
        (0, 1),
    )
    assert outline.hole_rings == (
        (
            (1, 1),
            (1, 2),
            (2, 2),
            (2, 1),
        ),
    )


def test_trace_rings_rejects_open_boundary() -> None:
    tracer = OutlineTracer()
    edges = frozenset(
        {
            Edge(
                start=(0, 0),
                end=(1, 0),
            ),
        }
    )

    with pytest.raises(
        InvariantViolationError,
        match="Outline is not closed.",
    ):
        tracer._trace_rings(
            edges,
        )


def test_trace_raw_preserves_hole_between_disjoint_regions() -> None:
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

    outer_region = Region(
        id=1,
        color=black,
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
    inner_region = Region(
        id=2,
        color=black,
        pixels=pack_pixels(
            {
                (1, 1),
            },
        ),
    )

    assert outer_region.pixels.isdisjoint(
        inner_region.pixels,
    )

    tracer = OutlineTracer()
    raw_outlines = (
        tracer.trace_raw(
            outer_region,
        ),
        tracer.trace_raw(
            inner_region,
        ),
    )

    assert (
        OutlineGeometryValidator().overlapping_region_pairs(
            raw_outlines,
        )
        == set()
    )
