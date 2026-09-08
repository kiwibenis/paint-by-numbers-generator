# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from unittest.mock import patch

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions import RegionMerger


def _color(
    number: int,
    name: str,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=name,
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=50.0,
            a=0.0,
            b=0.0,
        ),
    )


def test_defer_materialization_for_unchecked_merge_target() -> None:
    color = _color(
        number=1,
        name="Test",
    )

    regions = tuple(
        Region(
            id=region_id,
            color=color,
            pixels=pack_pixels(
                {
                    (region_id - 1, 0),
                },
            ),
        )
        for region_id in range(1, 5)
    )

    with patch(
        "pbn.regions.merger.Region",
        wraps=Region,
    ) as region_constructor:
        result = RegionMerger().merge(
            regions,
            minimum_circle_diameter_px=4,
        )

    assert len(result) == 1

    assert set(result[0].coordinates()) == {
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 0),
    }

    assert region_constructor.call_count == 1
