# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Set as AbstractSet

from pbn.models import RGB, InputImage, Lab
from pbn.regions.circle_fit import RegionCircleFit
from tools.evaluate_quantization_collisions import (
    LocalSourceComponent,
    build_local_source_components,
    build_unpaintable_component_preview_bmp,
    rank_unpaintable_components,
    summarize_local_source_components,
)


class LightnessDistance:
    """
    Deterministic test color distance using only CIELAB lightness.
    """

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return abs(first.l - second.l)


class RedChannelConverter:
    """
    Deterministic test converter mapping red to CIELAB lightness.
    """

    def convert(
        self,
        rgb: RGB,
    ) -> Lab:
        return Lab(
            l=float(rgb.red),
            a=0.0,
            b=0.0,
        )


class MinimumPixelCountFit:
    """
    Test paintability rule based on component pixel count.

    Takes packed pixel indices, as `PixelCircleFit` declares and as
    `RegionCircleFit` reads them. This fake used to declare coordinate
    pairs, matching a protocol that was wrong, and since it only counted
    the elements it accepted either. The tool passed coordinate pairs to
    the real implementation and raised TypeError, and these tests stayed
    green throughout. The element check below is what makes the
    representation part of the assertion rather than an assumption.
    """

    def __init__(
        self,
        minimum_pixel_count: int,
    ) -> None:
        self._minimum_pixel_count = minimum_pixel_count

    def fits_pixels(
        self,
        pixels: AbstractSet[int],
        diameter_px: int,
    ) -> bool:
        del diameter_px

        assert all(
            isinstance(
                pixel,
                int,
            )
            for pixel in pixels
        )

        return len(pixels) >= self._minimum_pixel_count


def _rgb(
    value: int,
) -> RGB:
    return RGB(
        red=value,
        green=0,
        blue=0,
    )


def test_build_local_source_components_works_with_the_real_circle_fit() -> None:
    """
    The one test here that does not substitute the circle fit.

    Every other test in this module supplies its own, so all of them
    passed while the tool handed the real `RegionCircleFit` a set of
    coordinate pairs and it raised TypeError on the first component
    large enough to reach the coordinate arithmetic. A fake cannot
    detect a mismatch with the implementation it replaces.

    The component has to exceed the circle offset count, or the
    implementation returns on the length check before reading an
    element, which is exactly why the smaller cases never failed.
    """
    image = InputImage.from_rows(
        tuple(tuple(_rgb(10) for _ in range(8)) for _ in range(8)),
    )

    components = build_local_source_components(
        image=image,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=2.0,
        minimum_circle_diameter_px=4,
        circle_fit=RegionCircleFit(),
    )

    assert len(components) == 1
    assert len(components[0].pixels) == 64
    assert components[0].paintable is True


def test_build_local_source_components_groups_adjacent_similar_pixels() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(10),
                _rgb(11),
                _rgb(30),
            ),
            (
                _rgb(10),
                _rgb(12),
                _rgb(30),
            ),
        )
    )

    components = build_local_source_components(
        image=image,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=2.0,
        minimum_circle_diameter_px=1,
        circle_fit=MinimumPixelCountFit(
            minimum_pixel_count=1,
        ),
    )

    assert components == (
        LocalSourceComponent(
            representative=_rgb(10),
            pixels=frozenset(
                {
                    (0, 0),
                    (1, 0),
                    (0, 1),
                    (1, 1),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=_rgb(30),
            pixels=frozenset(
                {
                    (2, 0),
                    (2, 1),
                },
            ),
            paintable=True,
        ),
    )


def test_build_local_source_components_does_not_chain_color_distance() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(10),
                _rgb(12),
                _rgb(14),
            ),
        )
    )

    components = build_local_source_components(
        image=image,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=2.0,
        minimum_circle_diameter_px=1,
        circle_fit=MinimumPixelCountFit(
            minimum_pixel_count=1,
        ),
    )

    assert components == (
        LocalSourceComponent(
            representative=_rgb(10),
            pixels=frozenset(
                {
                    (0, 0),
                    (1, 0),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=_rgb(14),
            pixels=frozenset(
                {
                    (2, 0),
                },
            ),
            paintable=True,
        ),
    )


def test_build_local_source_components_keeps_separate_islands() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(10),
                _rgb(30),
                _rgb(10),
            ),
        )
    )

    components = build_local_source_components(
        image=image,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=2.0,
        minimum_circle_diameter_px=1,
        circle_fit=MinimumPixelCountFit(
            minimum_pixel_count=1,
        ),
    )

    assert len(components) == 3

    assert components[0].pixels == frozenset(
        {
            (0, 0),
        },
    )
    assert components[1].pixels == frozenset(
        {
            (1, 0),
        },
    )
    assert components[2].pixels == frozenset(
        {
            (2, 0),
        },
    )


def test_build_local_source_components_reports_paintability() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(10),
                _rgb(10),
                _rgb(30),
                _rgb(40),
            ),
        )
    )

    components = build_local_source_components(
        image=image,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=0.0,
        minimum_circle_diameter_px=7,
        circle_fit=MinimumPixelCountFit(
            minimum_pixel_count=2,
        ),
    )

    assert tuple(component.paintable for component in components) == (
        True,
        False,
        False,
    )


def test_summarize_local_source_components_reports_counts() -> None:
    components = (
        LocalSourceComponent(
            representative=_rgb(10),
            pixels=frozenset(
                {
                    (0, 0),
                    (1, 0),
                    (0, 1),
                    (1, 1),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=_rgb(20),
            pixels=frozenset(
                {
                    (2, 0),
                },
            ),
            paintable=False,
        ),
        LocalSourceComponent(
            representative=_rgb(30),
            pixels=frozenset(
                {
                    (2, 1),
                    (3, 1),
                },
            ),
            paintable=False,
        ),
    )

    summary = summarize_local_source_components(
        components=components,
    )

    assert summary.component_count == 3
    assert summary.paintable_component_count == 1
    assert summary.unpaintable_component_count == 2
    assert summary.paintable_pixel_count == 4
    assert summary.unpaintable_pixel_count == 3


def test_local_components_use_four_connected_adjacency() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(10),
                _rgb(30),
            ),
            (
                _rgb(30),
                _rgb(10),
            ),
        )
    )

    components = build_local_source_components(
        image=image,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=0.0,
        minimum_circle_diameter_px=1,
        circle_fit=MinimumPixelCountFit(
            minimum_pixel_count=1,
        ),
    )

    assert len(components) == 4


def test_rank_unpaintable_components_reports_largest_first() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(10),
                _rgb(10),
                _rgb(20),
                _rgb(30),
                _rgb(30),
            ),
            (
                _rgb(10),
                _rgb(20),
                _rgb(20),
                _rgb(30),
                _rgb(40),
            ),
        )
    )

    components = (
        LocalSourceComponent(
            representative=_rgb(10),
            pixels=frozenset(
                {
                    (0, 0),
                    (1, 0),
                    (0, 1),
                },
            ),
            paintable=False,
        ),
        LocalSourceComponent(
            representative=_rgb(20),
            pixels=frozenset(
                {
                    (2, 0),
                    (1, 1),
                    (2, 1),
                },
            ),
            paintable=False,
        ),
        LocalSourceComponent(
            representative=_rgb(30),
            pixels=frozenset(
                {
                    (3, 0),
                    (4, 0),
                    (3, 1),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=_rgb(40),
            pixels=frozenset(
                {
                    (4, 1),
                },
            ),
            paintable=False,
        ),
    )

    diagnostics = rank_unpaintable_components(
        image=image,
        components=components,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    assert tuple(diagnostic.pixel_count for diagnostic in diagnostics) == (
        3,
        3,
        1,
    )


def test_rank_unpaintable_components_reports_bounding_box() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(30),
                _rgb(30),
                _rgb(30),
            ),
            (
                _rgb(30),
                _rgb(10),
                _rgb(10),
            ),
            (
                _rgb(30),
                _rgb(10),
                _rgb(30),
            ),
        )
    )

    component = LocalSourceComponent(
        representative=_rgb(10),
        pixels=frozenset(
            {
                (1, 1),
                (2, 1),
                (1, 2),
            },
        ),
        paintable=False,
    )

    diagnostics = rank_unpaintable_components(
        image=image,
        components=(component,),
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    diagnostic = diagnostics[0]

    assert diagnostic.min_x == 1
    assert diagnostic.min_y == 1
    assert diagnostic.max_x == 2
    assert diagnostic.max_y == 2


def test_rank_unpaintable_components_reports_dominant_neighbor() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(30),
                _rgb(10),
                _rgb(20),
            ),
            (
                _rgb(30),
                _rgb(10),
                _rgb(20),
            ),
        )
    )

    components = (
        LocalSourceComponent(
            representative=_rgb(30),
            pixels=frozenset(
                {
                    (0, 0),
                    (0, 1),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=_rgb(10),
            pixels=frozenset(
                {
                    (1, 0),
                    (1, 1),
                },
            ),
            paintable=False,
        ),
        LocalSourceComponent(
            representative=_rgb(20),
            pixels=frozenset(
                {
                    (2, 0),
                    (2, 1),
                },
            ),
            paintable=True,
        ),
    )

    diagnostics = rank_unpaintable_components(
        image=image,
        components=components,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    diagnostic = diagnostics[0]

    assert diagnostic.neighbor_representative == _rgb(20)
    assert diagnostic.shared_boundary_px == 2
    assert diagnostic.neighbor_distance == 10.0


def test_rank_unpaintable_components_prefers_longer_shared_boundary() -> None:
    image = InputImage.from_rows(
        (
            (
                _rgb(30),
                _rgb(10),
                _rgb(20),
            ),
            (
                _rgb(30),
                _rgb(10),
                _rgb(20),
            ),
            (
                _rgb(30),
                _rgb(10),
                _rgb(20),
            ),
        )
    )

    components = (
        LocalSourceComponent(
            representative=_rgb(30),
            pixels=frozenset(
                {
                    (0, 0),
                    (0, 1),
                    (0, 2),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=_rgb(10),
            pixels=frozenset(
                {
                    (1, 0),
                    (1, 1),
                    (1, 2),
                },
            ),
            paintable=False,
        ),
        LocalSourceComponent(
            representative=_rgb(20),
            pixels=frozenset(
                {
                    (2, 0),
                    (2, 1),
                    (2, 2),
                },
            ),
            paintable=True,
        ),
    )

    diagnostics = rank_unpaintable_components(
        image=image,
        components=components,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    diagnostic = diagnostics[0]

    assert diagnostic.shared_boundary_px == 3


def test_unpaintable_component_preview_marks_only_unpaintable_pixels() -> None:
    image = InputImage.from_rows(
        (
            (
                RGB(
                    red=10,
                    green=20,
                    blue=30,
                ),
                RGB(
                    red=40,
                    green=50,
                    blue=60,
                ),
            ),
        )
    )

    components = (
        LocalSourceComponent(
            representative=image.rgb_at(0, 0),
            pixels=frozenset(
                {
                    (0, 0),
                },
            ),
            paintable=True,
        ),
        LocalSourceComponent(
            representative=image.rgb_at(1, 0),
            pixels=frozenset(
                {
                    (1, 0),
                },
            ),
            paintable=False,
        ),
    )

    preview = build_unpaintable_component_preview_bmp(
        image=image,
        components=components,
    )

    assert preview[:2] == b"BM"

    pixel_offset = int.from_bytes(
        preview[10:14],
        byteorder="little",
    )

    first_pixel = preview[pixel_offset : pixel_offset + 3]
    second_pixel = preview[pixel_offset + 3 : pixel_offset + 6]

    assert first_pixel == bytes(
        (
            30,
            20,
            10,
        ),
    )

    assert second_pixel == bytes(
        (
            0,
            0,
            255,
        ),
    )
