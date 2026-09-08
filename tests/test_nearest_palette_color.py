# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.color import DeltaE2000, NearestPaletteColorFinder
from pbn.models import RGB, Lab, Palette, PaletteColor


class FakeColorDistance:
    def __init__(
        self,
        distances: dict[int, float],
    ) -> None:
        self._distances = distances

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return self._distances[int(second.l)]


class FakeRankingColorDistance:
    def __init__(
        self,
        ranking_values: dict[int, float],
    ) -> None:
        self._ranking_values = ranking_values

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        raise AssertionError(
            "distance() must not be used when ranking_value() is available.",
        )

    def ranking_value(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return self._ranking_values[int(second.l)]


class FakeProjectedRankingColorDistance:
    def __init__(self) -> None:
        self.ranking_calls = 0

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        raise AssertionError(
            "distance() must not be used when ranking_value() is available.",
        )

    def ranking_value(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        self.ranking_calls += 1

        delta_l = first.l - second.l
        delta_a = first.a - second.a
        delta_b = first.b - second.b

        return delta_l * delta_l + delta_a * delta_a + delta_b * delta_b

    def projection(
        self,
        color: Lab,
    ) -> float:
        return color.l


def _palette_color(
    number: int,
    lightness: float,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=lightness,
            a=0.0,
            b=0.0,
        ),
    )


def test_find_nearest_color() -> None:
    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            PaletteColor(
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
            ),
            PaletteColor(
                number=2,
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
        ),
    )

    finder = NearestPaletteColorFinder(
        color_distance=DeltaE2000(),
    )

    result = finder.find(
        Lab(
            l=95.0,
            a=0.0,
            b=0.0,
        ),
        palette,
    )

    assert result.number == 2


def test_find_uses_supplied_color_distance() -> None:
    first = PaletteColor(
        number=1,
        name="First",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=10.0,
            a=0.0,
            b=0.0,
        ),
    )

    second = PaletteColor(
        number=2,
        name="Second",
        rgb=RGB(
            red=255,
            green=255,
            blue=255,
        ),
        lab=Lab(
            l=20.0,
            a=0.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            first,
            second,
        ),
    )

    finder = NearestPaletteColorFinder(
        color_distance=FakeColorDistance(
            {
                10: 5.0,
                20: 1.0,
            },
        ),
    )

    result = finder.find(
        Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
        palette,
    )

    assert result is second


def test_find_uses_ranking_value_when_available() -> None:
    first = PaletteColor(
        number=1,
        name="First",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=10.0,
            a=0.0,
            b=0.0,
        ),
    )

    second = PaletteColor(
        number=2,
        name="Second",
        rgb=RGB(
            red=255,
            green=255,
            blue=255,
        ),
        lab=Lab(
            l=20.0,
            a=0.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            first,
            second,
        ),
    )

    finder = NearestPaletteColorFinder(
        color_distance=FakeRankingColorDistance(
            {
                10: 5.0,
                20: 1.0,
            },
        ),
    )

    result = finder.find(
        Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
        palette,
    )

    assert result is second


def test_find_prunes_candidates_with_squared_projection_lower_bound() -> None:
    colors = (
        _palette_color(
            number=1,
            lightness=100.0,
        ),
        _palette_color(
            number=2,
            lightness=0.0,
        ),
        _palette_color(
            number=3,
            lightness=50.0,
        ),
        _palette_color(
            number=4,
            lightness=75.0,
        ),
        _palette_color(
            number=5,
            lightness=25.0,
        ),
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=colors,
    )

    distance = FakeProjectedRankingColorDistance()
    finder = NearestPaletteColorFinder(
        color_distance=distance,
    )

    result = finder.find(
        Lab(
            l=50.0,
            a=0.0,
            b=0.0,
        ),
        palette,
    )

    assert result is colors[2]
    assert distance.ranking_calls == 1


def test_find_projection_preserves_palette_order_for_equal_distances() -> None:
    first = _palette_color(
        number=1,
        lightness=60.0,
    )
    second = _palette_color(
        number=2,
        lightness=40.0,
    )

    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            first,
            second,
        ),
    )

    finder = NearestPaletteColorFinder(
        color_distance=FakeProjectedRankingColorDistance(),
    )

    result = finder.find(
        Lab(
            l=50.0,
            a=0.0,
            b=0.0,
        ),
        palette,
    )

    assert result is first


def test_empty_palette() -> None:
    palette = Palette(
        id="empty",
        manufacturer="Test",
        display_name="Empty",
        version=1,
        colors=(),
    )

    finder = NearestPaletteColorFinder(
        color_distance=DeltaE2000(),
    )

    with pytest.raises(ValueError):
        finder.find(
            Lab(
                l=50.0,
                a=0.0,
                b=0.0,
            ),
            palette,
        )
