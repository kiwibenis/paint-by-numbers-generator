# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.models import RGB, Lab, Outline, PaletteColor, Region
from pbn.models.pixel_index import pack_pixels
from pbn.outline.geometry_validator import OutlineGeometryValidator
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


def test_fallback_revalidates_only_affected_regions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = _color()

    fallback_region = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    unchanged_region = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (10, 0),
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

    valid_fallback_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ),
    )

    unchanged_outline = Outline(
        region_id=2,
        points=(
            (10, 0),
            (11, 0),
            (11, 1),
            (10, 1),
        ),
    )

    def fake_simplify(
        simplifier: DouglasPeuckerSimplifier,
        outline: Outline,
        *,
        tolerance: float,
    ) -> Outline:
        del simplifier

        if outline.region_id == 1:
            if tolerance > 0.25:
                return invalid_outline

            return valid_fallback_outline

        return unchanged_outline

    validation_region_id_filters: list[set[int] | None] = []
    original_invalid_region_ids = OutlineGeometryValidator.invalid_region_ids

    def tracking_invalid_region_ids(
        validator: OutlineGeometryValidator,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[int]:
        if region_ids is None:
            validation_region_id_filters.append(
                None,
            )
        else:
            validation_region_id_filters.append(
                set(region_ids),
            )

        return original_invalid_region_ids(
            validator,
            outlines,
            region_ids=region_ids,
        )

    monkeypatch.setattr(
        DouglasPeuckerSimplifier,
        "simplify",
        fake_simplify,
    )
    monkeypatch.setattr(
        OutlineGeometryValidator,
        "invalid_region_ids",
        tracking_invalid_region_ids,
    )

    outlines = OutlineTopologySimplifier().simplify(
        (
            fallback_region,
            unchanged_region,
        ),
        tolerance=1.0,
    )

    assert outlines == (
        valid_fallback_outline,
        unchanged_outline,
    )
    assert validation_region_id_filters == [
        None,
        None,
        {
            1,
        },
        {
            1,
        },
    ]
