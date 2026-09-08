# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import RGB, InputImage, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    find_offset_collapsed_pairs,
    summarize_offset_collapsed_pairs,
)


class RedChannelConverter:
    """
    Deterministic test converter mapping red to Lab lightness.
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


class LightnessDistance:
    """
    Deterministic test color distance using Lab lightness only.
    """

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return abs(first.l - second.l)


def _rgb(
    value: int,
) -> RGB:
    return RGB(
        red=value,
        green=0,
        blue=0,
    )


def _palette_color(
    number: int,
    value: int,
) -> PaletteColor:
    rgb = _rgb(
        value,
    )

    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=rgb,
        lab=Lab(
            l=float(value),
            a=0.0,
            b=0.0,
        ),
    )


def _image(
    rows: tuple[
        tuple[RGB, ...],
        ...,
    ],
) -> InputImage:
    return InputImage.from_rows(rows)


def test_find_offset_collapsed_pairs_finds_horizontal_pair() -> None:
    first = _rgb(
        10,
    )
    middle = _rgb(
        11,
    )
    second = _rgb(
        30,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    pairs = find_offset_collapsed_pairs(
        image=_image(
            (
                (
                    first,
                    middle,
                    second,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            middle: palette_color,
            second: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        source_distance_threshold=5.0,
    )

    assert (
        len(
            pairs,
        )
        == 1
    )

    pair = pairs[0]

    assert pair.first_pixel == (
        0,
        0,
    )
    assert pair.second_pixel == (
        2,
        0,
    )
    assert pair.offset_px == 2
    assert pair.source_distance == 20.0
    assert pair.palette_color == palette_color


def test_find_offset_collapsed_pairs_finds_vertical_pair() -> None:
    first = _rgb(
        10,
    )
    middle = _rgb(
        11,
    )
    second = _rgb(
        30,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    pairs = find_offset_collapsed_pairs(
        image=_image(
            (
                (first,),
                (middle,),
                (second,),
            ),
        ),
        color_matches={
            first: palette_color,
            middle: palette_color,
            second: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        source_distance_threshold=5.0,
    )

    assert (
        len(
            pairs,
        )
        == 1
    )

    assert pairs[0].first_pixel == (
        0,
        0,
    )
    assert pairs[0].second_pixel == (
        0,
        2,
    )


def test_find_offset_collapsed_pairs_ignores_preserved_palette_boundary() -> None:
    first = _rgb(
        10,
    )
    middle = _rgb(
        11,
    )
    second = _rgb(
        30,
    )

    first_palette = _palette_color(
        100,
        10,
    )
    second_palette = _palette_color(
        101,
        30,
    )

    pairs = find_offset_collapsed_pairs(
        image=_image(
            (
                (
                    first,
                    middle,
                    second,
                ),
            ),
        ),
        color_matches={
            first: first_palette,
            middle: first_palette,
            second: second_palette,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        source_distance_threshold=5.0,
    )

    assert pairs == ()


def test_find_offset_collapsed_pairs_ignores_small_source_difference() -> None:
    first = _rgb(
        10,
    )
    middle = _rgb(
        11,
    )
    second = _rgb(
        15,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    pairs = find_offset_collapsed_pairs(
        image=_image(
            (
                (
                    first,
                    middle,
                    second,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            middle: palette_color,
            second: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        source_distance_threshold=5.0,
    )

    assert pairs == ()


def test_find_offset_collapsed_pairs_threshold_is_exclusive() -> None:
    first = _rgb(
        10,
    )
    middle = _rgb(
        11,
    )
    second = _rgb(
        15,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    pairs = find_offset_collapsed_pairs(
        image=_image(
            (
                (
                    first,
                    middle,
                    second,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            middle: palette_color,
            second: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        source_distance_threshold=5.0,
    )

    assert pairs == ()


def test_find_offset_collapsed_pairs_rejects_non_positive_offset() -> None:
    color = _rgb(
        10,
    )

    palette_color = _palette_color(
        100,
        10,
    )

    try:
        find_offset_collapsed_pairs(
            image=_image(
                ((color,),),
            ),
            color_matches={
                color: palette_color,
            },
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            offset_px=0,
            source_distance_threshold=5.0,
        )
    except ValueError as error:
        assert (
            str(
                error,
            )
            == "offset_px must be greater than zero"
        )
    else:
        raise AssertionError(
            "Expected ValueError.",
        )


def test_find_offset_collapsed_pairs_rejects_negative_threshold() -> None:
    color = _rgb(
        10,
    )

    palette_color = _palette_color(
        100,
        10,
    )

    try:
        find_offset_collapsed_pairs(
            image=_image(
                ((color,),),
            ),
            color_matches={
                color: palette_color,
            },
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            offset_px=2,
            source_distance_threshold=-1.0,
        )
    except ValueError as error:
        assert str(
            error,
        ) == ("source_distance_threshold must not be negative")
    else:
        raise AssertionError(
            "Expected ValueError.",
        )


def test_summarize_offset_collapsed_pairs_reports_distance_metrics() -> None:
    first = _rgb(
        10,
    )
    second = _rgb(
        20,
    )
    third = _rgb(
        40,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    pairs = find_offset_collapsed_pairs(
        image=_image(
            (
                (
                    first,
                    second,
                    third,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            second: palette_color,
            third: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=1,
        source_distance_threshold=5.0,
    )

    summary = summarize_offset_collapsed_pairs(
        offset_px=1,
        pairs=pairs,
    )

    assert summary.offset_px == 1
    assert summary.pair_count == 2
    assert summary.source_distance_min == 10.0
    assert summary.source_distance_max == 20.0
    assert summary.source_distance_mean == 15.0


def test_summarize_offset_collapsed_pairs_handles_empty_input() -> None:
    summary = summarize_offset_collapsed_pairs(
        offset_px=4,
        pairs=(),
    )

    assert summary.offset_px == 4
    assert summary.pair_count == 0
    assert summary.source_distance_min is None
    assert summary.source_distance_max is None
    assert summary.source_distance_mean is None
