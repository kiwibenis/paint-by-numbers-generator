# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import RGB, Lab, Outline, PaletteColor, Region
from pbn.models.pixel_index import pack_pixels
from pbn.outline import OutlineTracer
from pbn.outline.geometry_validator import OutlineGeometryValidator
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


def test_simplify_falls_back_when_regions_would_overlap() -> None:
    color = _color()

    first_region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (3, 3),
                (3, 4),
                (4, 2),
                (4, 3),
                (4, 4),
                (4, 5),
                (4, 6),
                (5, 2),
                (5, 4),
            },
        ),
    )

    second_region = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (5, 5),
                (5, 6),
                (6, 2),
                (6, 3),
                (6, 4),
                (6, 5),
                (6, 6),
            },
        ),
    )

    assert first_region.pixels.isdisjoint(
        second_region.pixels,
    )

    tracer = OutlineTracer()
    raw_outlines = (
        tracer.trace_raw(
            first_region,
        ),
        tracer.trace_raw(
            second_region,
        ),
    )

    assert (
        OutlineGeometryValidator().invalid_region_ids(
            raw_outlines,
        )
        == set()
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            first_region,
            second_region,
        ),
        tolerance=2.0,
    )

    assert outlines == (
        Outline(
            region_id=1,
            points=(
                (6, 2),
                (6, 3),
                (6, 4),
                (5, 7),
                (3, 3),
            ),
        ),
        Outline(
            region_id=2,
            points=(
                (6, 4),
                (6, 3),
                (6, 2),
                (7, 7),
                (5, 7),
            ),
        ),
    )
