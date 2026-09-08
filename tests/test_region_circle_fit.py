# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import RGB, Lab, PaletteColor, Region
from pbn.models.pixel_index import pack_pixels
from pbn.regions.circle_fit import RegionCircleFit


def _region(
    pixels: set[tuple[int, int]],
) -> Region:
    return Region(
        id=1,
        color=PaletteColor(
            number=101,
            name="White",
            rgb=RGB(
                red=255,
                green=255,
                blue=255,
            ),
            lab=Lab(
                l=100.0,
                a=0.0,
                b=0.0,
            ),
        ),
        pixels=pack_pixels(
            pixels,
        ),
    )


def test_circle_fits_inside_region() -> None:
    pixels = {(x, y) for x in range(10) for y in range(10)}

    region = _region(pixels)

    assert RegionCircleFit().fits(
        region=region,
        diameter_px=6,
    )


def test_circle_does_not_fit_inside_small_region() -> None:
    pixels = {(x, y) for x in range(5) for y in range(5)}

    region = _region(pixels)

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=6,
    )


def test_sparse_region_does_not_fit_circle() -> None:
    region = _region(
        {
            (0, 0),
            (9, 0),
            (0, 9),
            (9, 9),
        },
    )

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=6,
    )


def test_large_but_narrow_region_does_not_fit_circle() -> None:
    pixels = {(x, y) for x in range(30) for y in range(3)}

    region = _region(pixels)

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=6,
    )


def test_circle_does_not_fit_in_concave_region() -> None:
    pixels = {
        (x, y)
        for x in range(10)
        for y in range(10)
        if (x < 2 or x >= 8 or y < 2 or y >= 8)
    }

    region = _region(pixels)

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=6,
    )


def test_circle_requires_all_pixels_inside_region() -> None:
    pixels = {
        (x, y)
        for x in range(10)
        for y in range(10)
        if not (3 <= x <= 6 and 3 <= y <= 6)
    }

    region = _region(pixels)

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=6,
    )


def test_reuse_circle_offsets_by_diameter() -> None:
    class CountingRegionCircleFit(RegionCircleFit):
        def __init__(self) -> None:
            super().__init__()
            self.circle_offset_calculations = 0

        def _circle_offsets(
            self,
            radius: float,
        ) -> tuple[int, ...]:
            self.circle_offset_calculations += 1
            return super()._circle_offsets(
                radius,
            )

    region = _region(
        {(x, y) for x in range(12) for y in range(12)},
    )

    circle_fit = CountingRegionCircleFit()

    assert circle_fit.fits(
        region=region,
        diameter_px=6,
    )
    assert circle_fit.fits(
        region=region,
        diameter_px=6,
    )
    assert circle_fit.fits(
        region=region,
        diameter_px=8,
    )
    assert circle_fit.fits(
        region=region,
        diameter_px=6,
    )

    assert circle_fit.circle_offset_calculations == 2


def test_non_positive_diameter_does_not_fit() -> None:
    region = _region(
        {(x, y) for x in range(10) for y in range(10)},
    )

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=0,
    )

    assert not RegionCircleFit().fits(
        region=region,
        diameter_px=-1,
    )
