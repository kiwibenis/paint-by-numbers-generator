# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from collections import deque
from collections.abc import Iterable
from unittest.mock import patch

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions import RegionAdjacency, RegionMerger
from pbn.regions.circle_fit import RegionCircleFit


def _color(
    number: int,
    name: str,
    red: int,
    green: int,
    blue: int,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=name,
        rgb=RGB(
            red=red,
            green=green,
            blue=blue,
        ),
        lab=Lab(
            l=50.0,
            a=0.0,
            b=0.0,
        ),
    )


def test_merge_region_without_minimum_circle() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    large = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    small = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (5, 2),
            },
        ),
    )

    result = RegionMerger().merge(
        (
            large,
            small,
        ),
        minimum_circle_diameter_px=4,
    )

    assert len(result) == 1

    merged = result[0]

    assert merged.id == large.id
    assert merged.color == black
    assert merged.pixels == frozenset(
        large.pixels | small.pixels,
    )


def test_keep_isolated_region_without_minimum_circle() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
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

    result = RegionMerger().merge(
        (region,),
        minimum_circle_diameter_px=4,
    )

    assert result == (region,)


def test_keep_region_that_contains_minimum_circle() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    region = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    result = RegionMerger().merge(
        (region,),
        minimum_circle_diameter_px=4,
    )

    assert result == (region,)


def test_skip_adjacency_when_all_regions_contain_minimum_circle() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    first = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    second = Region(
        id=2,
        color=black,
        pixels=pack_pixels(
            {(x + 5, y) for x in range(5) for y in range(5)},
        ),
    )

    with patch.object(
        RegionAdjacency,
        "shared_borders_with_overlap_status",
    ) as shared_borders:
        result = RegionMerger().merge(
            (
                first,
                second,
            ),
            minimum_circle_diameter_px=4,
        )

    assert result == (
        first,
        second,
    )
    shared_borders.assert_not_called()


def test_reuse_adjacency_across_multiple_merges() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    large = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    first_small = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (5, 1),
            },
        ),
    )

    second_small = Region(
        id=3,
        color=white,
        pixels=pack_pixels(
            {
                (5, 3),
            },
        ),
    )

    with patch.object(
        RegionAdjacency,
        "shared_borders_with_overlap_status",
        autospec=True,
        wraps=RegionAdjacency.shared_borders_with_overlap_status,
    ) as shared_borders:
        result = RegionMerger().merge(
            (
                first_small,
                second_small,
                large,
            ),
            minimum_circle_diameter_px=4,
        )

    assert len(result) == 1

    merged = result[0]

    assert merged.id == large.id
    assert merged.color == black
    assert merged.pixels == frozenset(
        large.pixels | first_small.pixels | second_small.pixels
    )

    assert shared_borders.call_count == 1


def test_reuse_circle_fit_for_unchanged_region_across_merges() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    stable = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    target = Region(
        id=2,
        color=black,
        pixels=pack_pixels(
            {(x + 10, y) for x in range(5) for y in range(5)},
        ),
    )

    first_small = Region(
        id=3,
        color=white,
        pixels=pack_pixels(
            {
                (9, 1),
            },
        ),
    )

    second_small = Region(
        id=4,
        color=white,
        pixels=pack_pixels(
            {
                (9, 3),
            },
        ),
    )

    with patch.object(
        RegionCircleFit,
        "fits",
        autospec=True,
        wraps=RegionCircleFit.fits,
    ) as fits:
        result = RegionMerger().merge(
            (
                stable,
                first_small,
                second_small,
                target,
            ),
            minimum_circle_diameter_px=4,
        )

    stable_fit_calls = [
        call for call in fits.call_args_list if call.kwargs["region"] is stable
    ]

    assert len(stable_fit_calls) == 1

    assert len(result) == 2
    assert stable in result

    merged = next(region for region in result if region.id == target.id)

    assert merged.pixels == frozenset(
        target.pixels | first_small.pixels | second_small.pixels
    )


def test_do_not_recheck_unchanged_region_after_merges() -> None:
    class SpyRegionMerger(RegionMerger):
        def __init__(self) -> None:
            super().__init__()
            self.checked_regions: list[Region] = []

        def _fits(
            self,
            region: Region,
            minimum_circle_diameter_px: int,
            fit_cache: dict[int, tuple[Region, bool]],
        ) -> bool:
            self.checked_regions.append(region)
            return super()._fits(
                region,
                minimum_circle_diameter_px,
                fit_cache,
            )

    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    stable = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    target = Region(
        id=2,
        color=black,
        pixels=pack_pixels(
            {(x + 10, y) for x in range(5) for y in range(5)},
        ),
    )

    first_small = Region(
        id=3,
        color=white,
        pixels=pack_pixels(
            {
                (9, 1),
            },
        ),
    )

    second_small = Region(
        id=4,
        color=white,
        pixels=pack_pixels(
            {
                (9, 3),
            },
        ),
    )

    merger = SpyRegionMerger()

    result = merger.merge(
        (
            stable,
            first_small,
            second_small,
            target,
        ),
        minimum_circle_diameter_px=4,
    )

    stable_fit_calls = [region for region in merger.checked_regions if region is stable]

    assert len(stable_fit_calls) == 1
    assert len(result) == 2
    assert stable in result

    merged = next(region for region in result if region.id == target.id)

    assert merged.pixels == frozenset(
        target.pixels | first_small.pixels | second_small.pixels
    )


def test_pending_queue_does_not_store_region_objects() -> None:
    queued_items: list[object] = []

    class TrackingDeque:
        def __init__(
            self,
            values: Iterable[object],
        ) -> None:
            items = tuple(values)
            queued_items.extend(items)
            self._items: deque[object] = deque(items)

        def __bool__(self) -> bool:
            return bool(self._items)

        def popleft(self) -> object:
            return self._items.popleft()

        def append(
            self,
            value: object,
        ) -> None:
            queued_items.append(value)
            self._items.append(value)

    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    first = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {
                (0, 0),
            },
        ),
    )

    second = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (1, 0),
            },
        ),
    )

    with patch(
        "pbn.regions.merger.deque",
        TrackingDeque,
    ):
        result = RegionMerger().merge(
            (
                first,
                second,
            ),
            minimum_circle_diameter_px=4,
        )

    assert len(result) == 1
    assert result[0].pixels == frozenset(
        first.pixels | second.pixels,
    )

    assert queued_items
    assert all(not isinstance(item, Region) for item in queued_items)


def test_incremental_adjacency_does_not_rewrite_unchanged_neighbor() -> None:
    class TrackingBorders(dict[int, int]):
        def __init__(
            self,
            borders: dict[int, int],
        ) -> None:
            super().__init__(borders)
            self.write_count = 0

        def __setitem__(
            self,
            key: int,
            value: int,
        ) -> None:
            self.write_count += 1
            super().__setitem__(
                key,
                value,
            )

    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    target = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x + 5, y) for x in range(5) for y in range(5)},
        ),
    )

    source = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (10, 2),
            },
        ),
    )

    unchanged_neighbor = Region(
        id=3,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    unchanged_neighbor_borders = TrackingBorders(
        {
            target.id: 5,
        },
    )

    shared_borders: dict[int, dict[int, int]] = {
        target.id: {
            source.id: 1,
            unchanged_neighbor.id: 5,
        },
        source.id: {
            target.id: 1,
        },
        unchanged_neighbor.id: unchanged_neighbor_borders,
    }

    with patch.object(
        RegionAdjacency,
        "shared_borders_with_overlap_status",
        return_value=(
            shared_borders,
            False,
        ),
    ):
        result = RegionMerger().merge(
            (
                source,
                target,
                unchanged_neighbor,
            ),
            minimum_circle_diameter_px=4,
        )

    assert unchanged_neighbor_borders.write_count == 0
    assert len(result) == 2

    merged = next(region for region in result if region.id == target.id)

    assert merged.pixels == frozenset(
        target.pixels | source.pixels,
    )


def test_defer_target_materialization_across_multiple_merges() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    target = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x + 10, y) for x in range(5) for y in range(5)},
        ),
    )

    first_small = Region(
        id=2,
        color=white,
        pixels=pack_pixels(
            {
                (9, 0),
            },
        ),
    )

    second_small = Region(
        id=3,
        color=white,
        pixels=pack_pixels(
            {
                (9, 2),
            },
        ),
    )

    third_small = Region(
        id=4,
        color=white,
        pixels=pack_pixels(
            {
                (9, 4),
            },
        ),
    )

    with patch(
        "pbn.regions.merger.Region",
        wraps=Region,
    ) as region_constructor:
        result = RegionMerger().merge(
            (
                target,
                first_small,
                second_small,
                third_small,
            ),
            minimum_circle_diameter_px=4,
        )

    assert len(result) == 1

    merged = result[0]

    assert merged.id == target.id
    assert merged.color == target.color
    assert merged.pixels == frozenset(
        target.pixels | first_small.pixels | second_small.pixels | third_small.pixels
    )

    assert region_constructor.call_count == 1


def test_merge_small_region_uses_deterministic_tie_breaker() -> None:
    black = _color(
        number=1,
        name="Black",
        red=0,
        green=0,
        blue=0,
    )

    white = _color(
        number=2,
        name="White",
        red=255,
        green=255,
        blue=255,
    )

    first_neighbor = Region(
        id=1,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(5) for y in range(5)},
        ),
    )

    small = Region(
        id=3,
        color=white,
        pixels=pack_pixels(
            {
                (5, 2),
            },
        ),
    )

    second_neighbor = Region(
        id=2,
        color=black,
        pixels=pack_pixels(
            {(x, y) for x in range(6, 11) for y in range(5)},
        ),
    )

    result = RegionMerger().merge(
        (
            small,
            second_neighbor,
            first_neighbor,
        ),
        minimum_circle_diameter_px=4,
    )

    assert len(result) == 2

    merged = next(region for region in result if region.id == 1)

    assert merged.pixels == frozenset(
        first_neighbor.pixels | small.pixels,
    )
