# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.models import RGB, InputImage, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    CenterSurroundCandidate,
    CenterSurroundSummary,
    build_center_surround_preview_bmp,
    build_parser,
    center_surround_preview_path,
    find_center_surround_candidates,
    format_center_surround_summary,
    summarize_center_surround_candidates,
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
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=_rgb(
            value,
        ),
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


def test_find_center_surround_candidates_finds_horizontal_structure() -> None:
    first_background = _rgb(
        10,
    )
    transition_left = _rgb(
        18,
    )
    center = _rgb(
        30,
    )
    transition_right = _rgb(
        20,
    )
    second_background = _rgb(
        12,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (
                    first_background,
                    transition_left,
                    center,
                    transition_right,
                    second_background,
                ),
            ),
        ),
        color_matches={
            first_background: palette_color,
            transition_left: palette_color,
            center: palette_color,
            transition_right: palette_color,
            second_background: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert (
        len(
            candidates,
        )
        == 1
    )

    candidate = candidates[0]

    assert candidate.center_pixel == (
        2,
        0,
    )
    assert candidate.first_background_pixel == (
        0,
        0,
    )
    assert candidate.second_background_pixel == (
        4,
        0,
    )

    assert candidate.orientation == "horizontal"
    assert candidate.offset_px == 2

    assert candidate.background_distance == 2.0
    assert candidate.first_center_distance == 20.0
    assert candidate.second_center_distance == 18.0

    assert candidate.palette_color == palette_color


def test_find_center_surround_candidates_finds_vertical_structure() -> None:
    first_background = _rgb(
        10,
    )
    transition_top = _rgb(
        18,
    )
    center = _rgb(
        30,
    )
    transition_bottom = _rgb(
        20,
    )
    second_background = _rgb(
        12,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (first_background,),
                (transition_top,),
                (center,),
                (transition_bottom,),
                (second_background,),
            ),
        ),
        color_matches={
            first_background: palette_color,
            transition_top: palette_color,
            center: palette_color,
            transition_bottom: palette_color,
            second_background: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=2,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert (
        len(
            candidates,
        )
        == 1
    )

    candidate = candidates[0]

    assert candidate.center_pixel == (
        0,
        2,
    )
    assert candidate.first_background_pixel == (
        0,
        0,
    )
    assert candidate.second_background_pixel == (
        0,
        4,
    )

    assert candidate.orientation == "vertical"


def test_find_center_surround_candidates_rejects_dissimilar_backgrounds() -> None:
    first_background = _rgb(
        10,
    )
    center = _rgb(
        50,
    )
    second_background = _rgb(
        30,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (
                    first_background,
                    center,
                    second_background,
                ),
            ),
        ),
        color_matches={
            first_background: palette_color,
            center: palette_color,
            second_background: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=1,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert candidates == ()


def test_find_center_surround_candidates_rejects_weak_center_contrast() -> None:
    first_background = _rgb(
        10,
    )
    center = _rgb(
        15,
    )
    second_background = _rgb(
        12,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (
                    first_background,
                    center,
                    second_background,
                ),
            ),
        ),
        color_matches={
            first_background: palette_color,
            center: palette_color,
            second_background: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=1,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert candidates == ()


def test_find_center_surround_candidates_rejects_preserved_center_color() -> None:
    first_background = _rgb(
        10,
    )
    center = _rgb(
        30,
    )
    second_background = _rgb(
        12,
    )

    background_palette = _palette_color(
        100,
        10,
    )
    center_palette = _palette_color(
        101,
        30,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (
                    first_background,
                    center,
                    second_background,
                ),
            ),
        ),
        color_matches={
            first_background: background_palette,
            center: center_palette,
            second_background: background_palette,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=1,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert candidates == ()


def test_find_center_surround_candidates_accepts_background_threshold_equality() -> (
    None
):
    first_background = _rgb(
        10,
    )
    center = _rgb(
        30,
    )
    second_background = _rgb(
        15,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (
                    first_background,
                    center,
                    second_background,
                ),
            ),
        ),
        color_matches={
            first_background: palette_color,
            center: palette_color,
            second_background: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=1,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert (
        len(
            candidates,
        )
        == 1
    )


def test_find_center_surround_candidates_rejects_center_threshold_equality() -> None:
    first_background = _rgb(
        10,
    )
    center = _rgb(
        15,
    )
    second_background = _rgb(
        10,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    candidates = find_center_surround_candidates(
        image=_image(
            (
                (
                    first_background,
                    center,
                    second_background,
                ),
            ),
        ),
        color_matches={
            first_background: palette_color,
            center: palette_color,
            second_background: palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        offset_px=1,
        background_distance_threshold=5.0,
        center_distance_threshold=5.0,
    )

    assert candidates == ()


def test_find_center_surround_candidates_rejects_non_positive_offset() -> None:
    color = _rgb(
        10,
    )
    palette_color = _palette_color(
        100,
        10,
    )

    with pytest.raises(
        ValueError,
        match="offset_px must be greater than zero",
    ):
        find_center_surround_candidates(
            image=_image(
                ((color,),),
            ),
            color_matches={
                color: palette_color,
            },
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            offset_px=0,
            background_distance_threshold=5.0,
            center_distance_threshold=5.0,
        )


def test_find_center_surround_candidates_rejects_negative_background_threshold() -> (
    None
):
    color = _rgb(
        10,
    )
    palette_color = _palette_color(
        100,
        10,
    )

    with pytest.raises(
        ValueError,
        match=("background_distance_threshold must not be negative"),
    ):
        find_center_surround_candidates(
            image=_image(
                ((color,),),
            ),
            color_matches={
                color: palette_color,
            },
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            offset_px=1,
            background_distance_threshold=-1.0,
            center_distance_threshold=5.0,
        )


def test_find_center_surround_candidates_rejects_negative_center_threshold() -> None:
    color = _rgb(
        10,
    )
    palette_color = _palette_color(
        100,
        10,
    )

    with pytest.raises(
        ValueError,
        match=("center_distance_threshold must not be negative"),
    ):
        find_center_surround_candidates(
            image=_image(
                ((color,),),
            ),
            color_matches={
                color: palette_color,
            },
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            offset_px=1,
            background_distance_threshold=5.0,
            center_distance_threshold=-1.0,
        )


def test_summarize_center_surround_candidates_reports_counts() -> None:
    palette_color = _palette_color(
        100,
        20,
    )

    horizontal = CenterSurroundCandidate(
        center_pixel=(
            2,
            0,
        ),
        first_background_pixel=(
            0,
            0,
        ),
        second_background_pixel=(
            4,
            0,
        ),
        orientation="horizontal",
        offset_px=2,
        center_source=_rgb(
            30,
        ),
        first_background_source=_rgb(
            10,
        ),
        second_background_source=_rgb(
            12,
        ),
        palette_color=palette_color,
        background_distance=2.0,
        first_center_distance=20.0,
        second_center_distance=18.0,
    )

    vertical_same_center = CenterSurroundCandidate(
        center_pixel=(
            2,
            0,
        ),
        first_background_pixel=(
            2,
            -2,
        ),
        second_background_pixel=(
            2,
            2,
        ),
        orientation="vertical",
        offset_px=2,
        center_source=_rgb(
            30,
        ),
        first_background_source=_rgb(
            11,
        ),
        second_background_source=_rgb(
            13,
        ),
        palette_color=palette_color,
        background_distance=2.0,
        first_center_distance=19.0,
        second_center_distance=17.0,
    )

    another_horizontal = CenterSurroundCandidate(
        center_pixel=(
            10,
            10,
        ),
        first_background_pixel=(
            8,
            10,
        ),
        second_background_pixel=(
            12,
            10,
        ),
        orientation="horizontal",
        offset_px=2,
        center_source=_rgb(
            40,
        ),
        first_background_source=_rgb(
            10,
        ),
        second_background_source=_rgb(
            10,
        ),
        palette_color=palette_color,
        background_distance=0.0,
        first_center_distance=30.0,
        second_center_distance=30.0,
    )

    summary = summarize_center_surround_candidates(
        offset_px=2,
        candidates=(
            horizontal,
            vertical_same_center,
            another_horizontal,
        ),
    )

    assert summary == CenterSurroundSummary(
        offset_px=2,
        candidate_count=3,
        unique_center_count=2,
        horizontal_count=2,
        vertical_count=1,
    )


def test_format_center_surround_summary_reports_counts() -> None:
    summary = CenterSurroundSummary(
        offset_px=4,
        candidate_count=30,
        unique_center_count=24,
        horizontal_count=17,
        vertical_count=13,
    )

    assert format_center_surround_summary(
        summary,
    ) == (
        "center_surround="
        "offset_px=4, "
        "candidates=30, "
        "unique_centers=24, "
        "horizontal=17, "
        "vertical=13"
    )


def test_center_surround_preview_marks_only_center_pixels() -> None:
    first_background = _rgb(
        10,
    )
    center = _rgb(
        30,
    )
    second_background = _rgb(
        12,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    image = _image(
        (
            (
                first_background,
                center,
                second_background,
            ),
        ),
    )

    candidate = CenterSurroundCandidate(
        center_pixel=(
            1,
            0,
        ),
        first_background_pixel=(
            0,
            0,
        ),
        second_background_pixel=(
            2,
            0,
        ),
        orientation="horizontal",
        offset_px=1,
        center_source=center,
        first_background_source=first_background,
        second_background_source=second_background,
        palette_color=palette_color,
        background_distance=2.0,
        first_center_distance=20.0,
        second_center_distance=18.0,
    )

    preview = build_center_surround_preview_bmp(
        image=image,
        candidates=(candidate,),
    )

    assert preview[:2] == b"BM"

    pixel_offset = 54

    assert preview[pixel_offset : pixel_offset + 3] == bytes(
        (
            first_background.blue,
            first_background.green,
            first_background.red,
        ),
    )

    assert preview[pixel_offset + 3 : pixel_offset + 6] == bytes(
        (
            0,
            0,
            255,
        ),
    )

    assert preview[pixel_offset + 6 : pixel_offset + 9] == bytes(
        (
            second_background.blue,
            second_background.green,
            second_background.red,
        ),
    )


def test_center_surround_preview_path_is_deterministic() -> None:
    assert center_surround_preview_path(
        output_directory=Path(
            "output",
        ),
        case="simple",
        offset_px=4,
    ) == (
        Path(
            "output",
        )
        / "quantization-center-surround-simple-4px.bmp"
    )


def test_parser_uses_default_center_surround_configuration() -> None:
    args = build_parser().parse_args(
        [],
    )

    assert args.center_surround_offsets == (
        2,
        4,
        8,
    )
    assert args.center_surround_background_threshold == 5.0
    assert args.center_surround_center_threshold == 5.0


def test_parser_accepts_custom_center_surround_configuration() -> None:
    args = build_parser().parse_args(
        [
            "--center-surround-offsets",
            "3",
            "6",
            "--center-surround-background-threshold",
            "4.0",
            "--center-surround-center-threshold",
            "8.0",
        ],
    )

    assert args.center_surround_offsets == [
        3,
        6,
    ]
    assert args.center_surround_background_threshold == 4.0
    assert args.center_surround_center_threshold == 8.0
