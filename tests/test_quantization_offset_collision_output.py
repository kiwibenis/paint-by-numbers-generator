# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

from pbn.models import RGB, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    OffsetCollapsedPair,
    OffsetCollapsedSummary,
    build_offset_collapsed_pair_preview_bmp,
    build_parser,
    format_offset_collapsed_summary,
    offset_collapsed_pair_preview_path,
)


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
        rgb=_rgb(value),
        lab=Lab(
            l=float(value),
            a=0.0,
            b=0.0,
        ),
    )


def test_parser_uses_default_offset_distances() -> None:
    args = build_parser().parse_args(
        [],
    )

    assert args.offset_distances == (
        2,
        4,
        8,
    )


def test_parser_accepts_custom_offset_distances() -> None:
    args = build_parser().parse_args(
        [
            "--offset-distances",
            "3",
            "6",
            "12",
        ],
    )

    assert args.offset_distances == [
        3,
        6,
        12,
    ]


def test_format_offset_collapsed_summary_reports_metrics() -> None:
    summary = OffsetCollapsedSummary(
        offset_px=4,
        pair_count=25,
        source_distance_min=5.5,
        source_distance_max=18.0,
        source_distance_mean=9.25,
    )

    assert format_offset_collapsed_summary(
        summary,
    ) == (
        "offset_collisions="
        "offset_px=4, "
        "pairs=25, "
        "source_delta_e_min=5.500000, "
        "source_delta_e_max=18.000000, "
        "source_delta_e_mean=9.250000"
    )


def test_format_offset_collapsed_summary_handles_empty_summary() -> None:
    summary = OffsetCollapsedSummary(
        offset_px=8,
        pair_count=0,
        source_distance_min=None,
        source_distance_max=None,
        source_distance_mean=None,
    )

    assert format_offset_collapsed_summary(
        summary,
    ) == (
        "offset_collisions="
        "offset_px=8, "
        "pairs=0, "
        "source_delta_e_min=none, "
        "source_delta_e_max=none, "
        "source_delta_e_mean=none"
    )


def test_offset_collapsed_pair_preview_marks_pair_endpoints() -> None:
    first = _rgb(
        10,
    )
    middle = _rgb(
        20,
    )
    second = _rgb(
        30,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    from pbn.models import InputImage

    image = InputImage.from_rows(
        (
            (
                first,
                middle,
                second,
            ),
        )
    )

    pairs = (
        OffsetCollapsedPair(
            first_pixel=(
                0,
                0,
            ),
            second_pixel=(
                2,
                0,
            ),
            first_source=first,
            second_source=second,
            palette_color=palette_color,
            offset_px=2,
            source_distance=20.0,
        ),
    )

    preview = build_offset_collapsed_pair_preview_bmp(
        image=image,
        pairs=pairs,
    )

    assert preview[:2] == b"BM"

    pixel_offset = 54

    assert preview[pixel_offset : pixel_offset + 3] == bytes(
        (
            0,
            0,
            255,
        ),
    )

    assert preview[pixel_offset + 3 : pixel_offset + 6] == bytes(
        (
            middle.blue,
            middle.green,
            middle.red,
        ),
    )

    assert preview[pixel_offset + 6 : pixel_offset + 9] == bytes(
        (
            0,
            0,
            255,
        ),
    )


def test_offset_collapsed_pair_preview_marks_all_incident_pixels() -> None:
    first = _rgb(
        10,
    )
    second = _rgb(
        30,
    )
    third = _rgb(
        50,
    )

    palette_color = _palette_color(
        100,
        20,
    )

    from pbn.models import InputImage

    image = InputImage.from_rows(
        (
            (
                first,
                second,
                third,
            ),
        )
    )

    pairs = (
        OffsetCollapsedPair(
            first_pixel=(
                0,
                0,
            ),
            second_pixel=(
                1,
                0,
            ),
            first_source=first,
            second_source=second,
            palette_color=palette_color,
            offset_px=1,
            source_distance=20.0,
        ),
        OffsetCollapsedPair(
            first_pixel=(
                1,
                0,
            ),
            second_pixel=(
                2,
                0,
            ),
            first_source=second,
            second_source=third,
            palette_color=palette_color,
            offset_px=1,
            source_distance=20.0,
        ),
    )

    preview = build_offset_collapsed_pair_preview_bmp(
        image=image,
        pairs=pairs,
    )

    pixel_offset = 54

    assert preview[pixel_offset : pixel_offset + 9] == bytes(
        (
            0,
            0,
            255,
            0,
            0,
            255,
            0,
            0,
            255,
        ),
    )


def test_offset_collapsed_pair_preview_path_is_deterministic() -> None:
    assert offset_collapsed_pair_preview_path(
        output_directory=Path(
            "output",
        ),
        case="simple",
        offset_px=4,
    ) == (
        Path(
            "output",
        )
        / "quantization-offset-collisions-simple-4px.bmp"
    )
