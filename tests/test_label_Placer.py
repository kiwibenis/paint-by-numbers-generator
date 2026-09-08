# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from array import array
from math import hypot
from unittest.mock import patch

from pbn.label import LabelPlacer
from pbn.models import (
    RGB,
    Lab,
    Label,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels


def _reference_best_position(
    region: Region,
) -> tuple[float, float]:
    coordinates = frozenset(
        region.coordinates(),
    )

    count = len(coordinates)

    center = (
        sum(pixel[0] for pixel in coordinates) / count,
        sum(pixel[1] for pixel in coordinates) / count,
    )

    boundary_pixels = tuple(
        pixel
        for pixel in coordinates
        if _reference_is_boundary_pixel(
            pixel,
            coordinates,
        )
    )

    def border_distance(
        pixel: tuple[int, int],
    ) -> float:
        if pixel in boundary_pixels:
            return 0.0

        return min(
            hypot(
                pixel[0] - boundary_x,
                pixel[1] - boundary_y,
            )
            for boundary_x, boundary_y in boundary_pixels
        )

    best_pixel = min(
        coordinates,
        key=lambda pixel: (
            -border_distance(pixel),
            hypot(
                pixel[0] - center[0],
                pixel[1] - center[1],
            ),
            pixel[1],
            pixel[0],
        ),
    )

    return (
        float(best_pixel[0]),
        float(best_pixel[1]),
    )


def _reference_is_boundary_pixel(
    pixel: tuple[int, int],
    region_pixels: frozenset[tuple[int, int]],
) -> bool:
    x, y = pixel

    return any(
        neighbor not in region_pixels
        for neighbor in (
            (x - 1, y - 1),
            (x, y - 1),
            (x + 1, y - 1),
            (x - 1, y),
            (x + 1, y),
            (x - 1, y + 1),
            (x, y + 1),
            (x + 1, y + 1),
        )
    )


def test_place_label_inside_non_convex_region() -> None:
    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
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
        id=42,
        color=red,
        pixels=pack_pixels(
            {
                (x, y)
                for x in range(5)
                for y in range(5)
                if x in (0, 1, 3, 4) or y in (0, 1, 3, 4)
            },
        ),
    )

    labels = LabelPlacer().place(
        (region,),
    )

    label = labels[0]

    assert label.position == (
        2.0,
        1.0,
    )


def test_place_single_label() -> None:
    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
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
        id=42,
        color=red,
        pixels=pack_pixels(
            {
                (0, 0),
                (2, 0),
                (0, 2),
                (2, 2),
            },
        ),
    )

    placer = LabelPlacer()

    labels = placer.place(
        (region,),
    )

    assert labels == (
        Label(
            region_id=42,
            text="7",
            position=(
                0.0,
                0.0,
            ),
        ),
    )


def test_place_label_prefers_center_of_compact_region() -> None:
    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
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
        id=42,
        color=red,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    labels = LabelPlacer().place(
        (region,),
    )

    assert labels == (
        Label(
            region_id=42,
            text="7",
            position=(
                2.0,
                2.0,
            ),
        ),
    )


def test_place_label_uses_y_then_x_as_final_tie_breakers() -> None:
    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
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
        id=42,
        color=red,
        pixels=pack_pixels(
            {(x, y) for x in range(4) for y in range(4)},
        ),
    )

    labels = LabelPlacer().place(
        (region,),
    )

    assert labels == (
        Label(
            region_id=42,
            text="7",
            position=(
                1.0,
                1.0,
            ),
        ),
    )


def test_place_combines_center_with_region_geometry() -> None:
    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
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
        id=42,
        color=red,
        pixels=pack_pixels(
            {(x, y) for x in range(7) for y in range(7)},
        ),
    )

    with patch.object(
        LabelPlacer,
        "_center",
        side_effect=AssertionError(
            "Separate center scan must not be used.",
        ),
        create=True,
    ):
        label = LabelPlacer().place(
            (region,),
        )[0]

    assert label.position == _reference_best_position(
        region,
    )


def test_place_matches_brute_force_reference_for_varied_regions() -> None:
    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    compact_pixels = frozenset((x, y) for x in range(7) for y in range(7))

    concave_pixels = frozenset(
        (x, y) for x in range(7) for y in range(7) if not (x >= 3 and 2 <= y <= 4)
    )

    thin_pixels = frozenset((x, y) for x in range(3) for y in range(11))

    sparse_pixels = frozenset(
        {
            *{(x, y) for x in range(3) for y in range(3)},
            *{(x + 1000, y + 1000) for x in range(3) for y in range(3)},
        },
    )

    pixel_sets = (
        compact_pixels,
        concave_pixels,
        thin_pixels,
        sparse_pixels,
    )

    for region_id, pixels in enumerate(
        pixel_sets,
        start=1,
    ):
        region = Region(
            id=region_id,
            color=red,
            pixels=pack_pixels(
                pixels,
            ),
        )

        label = LabelPlacer().place(
            (region,),
        )[0]

        assert label.position == _reference_best_position(
            region,
        )


def test_use_distance_transform_for_sparse_region_when_cheaper() -> None:
    class TrackingLabelPlacer(LabelPlacer):
        def __init__(self) -> None:
            self.distance_transform_calls = 0

        def _distance_transform(
            self,
            *,
            boundary_pixels: frozenset[tuple[int, int]],
            min_x: int,
            min_y: int,
            width: int,
            height: int,
        ) -> array[int]:
            self.distance_transform_calls += 1

            return super()._distance_transform(
                boundary_pixels=boundary_pixels,
                min_x=min_x,
                min_y=min_y,
                width=width,
                height=height,
            )

    red = PaletteColor(
        number=7,
        name="Red",
        rgb=RGB(
            red=255,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    pixels = frozenset(
        (x, y)
        for x in range(101)
        for y in range(101)
        if (48 <= x <= 52 or 48 <= y <= 52)
    )

    region = Region(
        id=42,
        color=red,
        pixels=pack_pixels(
            pixels,
        ),
    )

    placer = TrackingLabelPlacer()

    label = placer.place(
        (region,),
    )[0]

    assert label.position == _reference_best_position(
        region,
    )
    assert placer.distance_transform_calls == 1


def test_distance_transform_uses_compact_flat_storage() -> None:
    class InspectableLabelPlacer(LabelPlacer):
        def distance_transform(
            self,
            *,
            boundary_pixels: frozenset[tuple[int, int]],
            min_x: int,
            min_y: int,
            width: int,
            height: int,
        ) -> array[int]:
            return self._distance_transform(
                boundary_pixels=boundary_pixels,
                min_x=min_x,
                min_y=min_y,
                width=width,
                height=height,
            )

    distances = InspectableLabelPlacer().distance_transform(
        boundary_pixels=frozenset(
            {
                (0, 0),
            },
        ),
        min_x=0,
        min_y=0,
        width=3,
        height=3,
    )

    assert isinstance(
        distances,
        array,
    )
    assert len(distances) == 9
    assert distances[0] == 0
    assert distances[8] == 8


def test_distance_transform_matches_exact_squared_distances() -> None:
    class InspectableLabelPlacer(LabelPlacer):
        def distance_transform(
            self,
            *,
            boundary_pixels: frozenset[tuple[int, int]],
            min_x: int,
            min_y: int,
            width: int,
            height: int,
        ) -> array[int]:
            return self._distance_transform(
                boundary_pixels=boundary_pixels,
                min_x=min_x,
                min_y=min_y,
                width=width,
                height=height,
            )

    distances = InspectableLabelPlacer().distance_transform(
        boundary_pixels=frozenset(
            {
                (0, 0),
                (4, 2),
            },
        ),
        min_x=0,
        min_y=0,
        width=5,
        height=3,
    )

    assert list(distances) == [
        0,
        1,
        4,
        5,
        4,
        1,
        2,
        5,
        2,
        1,
        4,
        5,
        4,
        1,
        0,
    ]


def test_distance_transform_reuses_1d_work_buffers() -> None:
    class InspectableLabelPlacer(LabelPlacer):
        def distance_transform(
            self,
            *,
            boundary_pixels: frozenset[tuple[int, int]],
            min_x: int,
            min_y: int,
            width: int,
            height: int,
        ) -> array[int]:
            return self._distance_transform(
                boundary_pixels=boundary_pixels,
                min_x=min_x,
                min_y=min_y,
                width=width,
                height=height,
            )

    real_array = array

    with patch(
        "pbn.label.placer.array",
        side_effect=real_array,
    ) as array_constructor:
        distances = InspectableLabelPlacer().distance_transform(
            boundary_pixels=frozenset(
                {
                    (0, 0),
                },
            ),
            min_x=0,
            min_y=0,
            width=4,
            height=3,
        )

    assert distances[0] == 0
    assert distances[-1] == 13
    assert array_constructor.call_count == 8


def test_distance_transform_respects_memory_budget() -> None:
    class InspectableLabelPlacer(LabelPlacer):
        def should_use_distance_transform(
            self,
            *,
            bounding_box_area: int,
            interior_pixel_count: int,
            boundary_pixel_count: int,
        ) -> bool:
            return self._should_use_distance_transform(
                bounding_box_area=bounding_box_area,
                interior_pixel_count=interior_pixel_count,
                boundary_pixel_count=boundary_pixel_count,
            )

    placer = InspectableLabelPlacer()

    assert placer.should_use_distance_transform(
        bounding_box_area=1_600_000,
        interior_pixel_count=200_000,
        boundary_pixel_count=2_000,
    )

    assert not placer.should_use_distance_transform(
        bounding_box_area=2_200_000,
        interior_pixel_count=200_000,
        boundary_pixel_count=2_000,
    )
