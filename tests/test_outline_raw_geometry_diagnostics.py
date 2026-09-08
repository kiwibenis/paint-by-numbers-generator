# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.exceptions import InvariantViolationError
from pbn.models import RGB, Lab, Outline, PaletteColor, Region
from pbn.models.pixel_index import pack_pixels
from pbn.outline import OutlineTracer
from pbn.outline.geometry_validator import OutlineGeometryValidator
from pbn.outline.topology_simplifier import OutlineTopologySimplifier

Run = tuple[int, int, int]

# Extracted from examples/input/complex.png with
# palettes/faberCastellPolychromos120-v1.json, delta_e_2000 and
# minimum_circle_diameter_px=17.
_COMPLEX_POLYCHROMOS120_COORDINATE_OFFSET = (1368, 0)
_COMPLEX_POLYCHROMOS120_REGION_RUNS: dict[int, tuple[Run, ...]] = {
    162: (
        (0, 16, 105),
        (0, 120, 141),
        (1, 15, 104),
        (1, 120, 140),
        (2, 14, 102),
        (2, 120, 140),
        (3, 14, 102),
        (3, 121, 140),
        (4, 14, 100),
        (4, 122, 140),
        (5, 15, 99),
        (5, 121, 141),
        (6, 15, 50),
        (6, 54, 97),
        (6, 121, 140),
        (7, 15, 49),
        (7, 54, 96),
        (7, 121, 140),
        (8, 15, 48),
        (8, 54, 87),
        (8, 89, 91),
        (8, 93, 94),
        (8, 120, 138),
        (9, 15, 46),
        (9, 54, 87),
        (9, 119, 138),
        (10, 14, 45),
        (10, 55, 85),
        (10, 119, 138),
        (11, 14, 44),
        (11, 55, 85),
        (11, 117, 137),
        (12, 14, 42),
        (12, 55, 84),
        (12, 115, 137),
        (13, 14, 41),
        (13, 54, 84),
        (13, 114, 136),
        (14, 13, 40),
        (14, 54, 84),
        (14, 114, 135),
        (15, 13, 39),
        (15, 54, 83),
        (15, 113, 133),
        (16, 12, 35),
        (16, 54, 82),
        (16, 112, 132),
        (17, 12, 34),
        (17, 54, 81),
        (17, 111, 130),
        (18, 12, 32),
        (18, 54, 81),
        (18, 111, 130),
        (19, 12, 29),
        (19, 31, 31),
        (19, 54, 81),
        (19, 110, 129),
        (20, 12, 29),
        (20, 53, 80),
        (20, 108, 125),
        (21, 12, 29),
        (21, 52, 76),
        (21, 78, 79),
        (21, 107, 124),
        (22, 12, 28),
        (22, 52, 75),
        (22, 106, 124),
        (23, 13, 27),
        (23, 51, 77),
        (23, 104, 124),
        (24, 12, 26),
        (24, 51, 77),
        (24, 103, 123),
        (25, 13, 26),
        (25, 51, 77),
        (25, 99, 122),
        (26, 12, 25),
        (26, 51, 77),
        (26, 96, 96),
        (26, 99, 121),
        (27, 12, 25),
        (27, 51, 77),
        (27, 87, 87),
        (27, 93, 119),
        (28, 11, 24),
        (28, 51, 77),
        (28, 86, 89),
        (28, 91, 119),
        (29, 11, 24),
        (29, 51, 78),
        (29, 83, 119),
        (30, 11, 24),
        (30, 51, 78),
        (30, 81, 118),
        (31, 11, 24),
        (31, 50, 117),
        (32, 11, 24),
        (32, 50, 116),
        (33, 11, 24),
        (33, 49, 114),
        (34, 12, 24),
        (34, 49, 114),
        (35, 12, 23),
        (35, 49, 110),
        (36, 12, 23),
        (36, 49, 109),
        (37, 11, 23),
        (37, 48, 107),
        (38, 11, 23),
        (38, 47, 67),
        (38, 70, 107),
        (39, 12, 23),
        (39, 46, 66),
        (39, 70, 104),
        (40, 10, 22),
        (40, 45, 65),
        (40, 70, 82),
        (40, 84, 103),
        (41, 8, 22),
        (41, 44, 64),
        (41, 70, 80),
        (41, 87, 103),
        (42, 6, 22),
        (42, 42, 63),
        (42, 70, 76),
        (42, 89, 101),
        (43, 6, 22),
        (43, 41, 62),
        (43, 70, 76),
        (44, 6, 22),
        (44, 40, 61),
        (44, 71, 75),
        (45, 5, 23),
        (45, 40, 59),
        (46, 5, 22),
        (46, 40, 58),
        (47, 5, 22),
        (47, 40, 57),
        (48, 4, 22),
        (48, 40, 56),
        (49, 1, 7),
        (49, 10, 10),
        (49, 14, 23),
        (49, 39, 55),
        (50, 0, 6),
        (50, 16, 23),
        (50, 38, 55),
        (51, 0, 5),
        (51, 17, 23),
        (51, 37, 54),
        (52, 0, 4),
        (52, 17, 23),
        (52, 36, 53),
        (53, 1, 2),
        (53, 17, 23),
        (53, 34, 52),
        (54, 17, 23),
        (54, 33, 52),
        (55, 17, 23),
        (55, 32, 51),
        (56, 17, 24),
        (56, 32, 36),
        (56, 41, 50),
        (57, 17, 24),
        (57, 30, 36),
        (57, 42, 49),
        (58, 17, 27),
        (58, 29, 35),
        (58, 42, 47),
        (59, 17, 34),
        (60, 17, 33),
        (61, 18, 33),
        (62, 21, 32),
        (63, 23, 31),
        (64, 25, 30),
    ),
    539: (
        (6, 51, 53),
        (7, 50, 53),
        (8, 49, 53),
        (9, 47, 53),
        (10, 46, 54),
        (11, 45, 54),
        (12, 43, 54),
        (13, 42, 53),
        (14, 41, 53),
        (15, 40, 53),
        (16, 36, 53),
        (17, 35, 53),
        (18, 33, 53),
        (19, 30, 30),
        (19, 32, 53),
        (20, 30, 52),
        (21, 30, 51),
        (22, 29, 51),
        (23, 28, 50),
        (24, 27, 50),
        (25, 27, 50),
        (26, 26, 50),
        (27, 26, 50),
        (28, 25, 50),
        (29, 25, 50),
        (30, 25, 50),
        (31, 25, 49),
        (32, 25, 49),
        (33, 25, 48),
        (34, 25, 48),
        (35, 24, 48),
        (36, 24, 48),
        (37, 24, 47),
        (38, 24, 46),
        (39, 24, 45),
        (40, 23, 44),
        (41, 23, 43),
        (42, 23, 41),
        (43, 23, 40),
        (44, 23, 39),
        (45, 24, 39),
        (46, 23, 39),
        (47, 23, 39),
        (48, 23, 39),
        (49, 24, 38),
        (50, 24, 37),
        (51, 24, 36),
        (52, 24, 35),
        (53, 24, 33),
        (54, 24, 32),
        (55, 24, 31),
        (56, 25, 31),
        (57, 25, 29),
        (58, 28, 28),
    ),
}


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


def _complex_polychromos120_region(
    region_id: int,
) -> Region:
    offset_x, offset_y = _COMPLEX_POLYCHROMOS120_COORDINATE_OFFSET
    runs = _COMPLEX_POLYCHROMOS120_REGION_RUNS[region_id]

    return Region(
        id=region_id,
        color=_color(),
        pixels=pack_pixels(
            (
                x + offset_x,
                y + offset_y,
            )
            for y, start_x, end_x in runs
            for x in range(
                start_x,
                end_x + 1,
            )
        ),
    )


def test_raw_geometry_error_reports_invalid_individual_regions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    region = Region(
        id=1,
        color=_color(),
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

    def invalid_trace_raw(
        tracer: OutlineTracer,
        traced_region: Region,
    ) -> Outline:
        del tracer
        del traced_region
        return invalid_outline

    monkeypatch.setattr(
        OutlineTracer,
        "trace_raw",
        invalid_trace_raw,
    )

    with pytest.raises(
        InvariantViolationError,
        match=(
            r"Outline tracing produced invalid polygon geometry "
            r"for region ids: \[1\]\. "
            r"Invalid individual region ids: \[1\]\. "
            r"Overlapping region pairs: \[\]\."
        ),
    ):
        OutlineTopologySimplifier().simplify(
            (region,),
            tolerance=1.0,
        )


def test_raw_geometry_error_reports_overlapping_region_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()
    first_region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )
    second_region = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (10, 10),
            },
        ),
    )
    raw_outlines = {
        1: Outline(
            region_id=1,
            points=(
                (0, 0),
                (2, 0),
                (2, 2),
                (0, 2),
            ),
        ),
        2: Outline(
            region_id=2,
            points=(
                (1, -1),
                (3, -1),
                (3, 1),
                (1, 1),
            ),
        ),
    }

    def overlapping_trace_raw(
        tracer: OutlineTracer,
        traced_region: Region,
    ) -> Outline:
        del tracer
        return raw_outlines[traced_region.id]

    monkeypatch.setattr(
        OutlineTracer,
        "trace_raw",
        overlapping_trace_raw,
    )

    with pytest.raises(
        InvariantViolationError,
        match=(
            r"Outline tracing produced invalid polygon geometry "
            r"for region ids: \[1, 2\]\. "
            r"Invalid individual region ids: \[\]\. "
            r"Overlapping region pairs: \[\(1, 2\)\]\."
        ),
    ):
        OutlineTopologySimplifier().simplify(
            (
                first_region,
                second_region,
            ),
            tolerance=1.0,
        )


def test_complex_polychromos120_raw_outline_preserves_nested_region() -> None:
    outer_region = _complex_polychromos120_region(
        162,
    )
    nested_region = _complex_polychromos120_region(
        539,
    )

    assert len(outer_region.pixels) == 4014
    assert len(nested_region.pixels) == 912
    assert outer_region.pixels.isdisjoint(
        nested_region.pixels,
    )

    tracer = OutlineTracer()
    outer_outline = tracer.trace_raw(
        outer_region,
    )
    nested_outline = tracer.trace_raw(
        nested_region,
    )

    assert len(outer_outline.hole_rings) == 1
    assert nested_outline.hole_rings == ()

    validator = OutlineGeometryValidator()
    raw_outlines = (
        outer_outline,
        nested_outline,
    )

    assert (
        validator.invalid_region_ids(
            raw_outlines,
        )
        == set()
    )
    assert (
        validator.overlapping_region_pairs(
            raw_outlines,
        )
        == set()
    )

    legacy_single_ring_outlines = (
        Outline(
            region_id=outer_outline.region_id,
            points=outer_outline.points,
        ),
        nested_outline,
    )

    assert validator.overlapping_region_pairs(
        legacy_single_ring_outlines,
    ) == {
        (162, 539),
    }

    simplified_outlines = OutlineTopologySimplifier().simplify(
        (
            outer_region,
            nested_region,
        ),
        tolerance=1.0,
    )

    assert {outline.region_id for outline in simplified_outlines} == {
        162,
        539,
    }
