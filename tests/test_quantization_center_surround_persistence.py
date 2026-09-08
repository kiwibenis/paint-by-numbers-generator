# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.models import RGB, InputImage, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    CenterSurroundCandidate,
    CenterSurroundPersistence,
    CenterSurroundPersistenceSummary,
    build_center_surround_persistence,
    build_center_surround_persistence_preview_bmp,
    build_parser,
    center_surround_persistence_preview_path,
    format_center_surround_persistence_summary,
    summarize_center_surround_persistence,
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
        rgb=_rgb(
            value,
        ),
        lab=Lab(
            l=float(value),
            a=0.0,
            b=0.0,
        ),
    )


def _candidate(
    *,
    center_pixel: tuple[int, int],
    offset_px: int,
    orientation: str,
) -> CenterSurroundCandidate:
    palette_color = _palette_color(
        100,
        20,
    )

    center_source = _rgb(
        30,
    )
    first_background = _rgb(
        10,
    )
    second_background = _rgb(
        12,
    )

    x, y = center_pixel

    if orientation == "horizontal":
        first_background_pixel = (
            x - offset_px,
            y,
        )
        second_background_pixel = (
            x + offset_px,
            y,
        )
    else:
        first_background_pixel = (
            x,
            y - offset_px,
        )
        second_background_pixel = (
            x,
            y + offset_px,
        )

    return CenterSurroundCandidate(
        center_pixel=center_pixel,
        first_background_pixel=first_background_pixel,
        second_background_pixel=second_background_pixel,
        orientation=orientation,
        offset_px=offset_px,
        center_source=center_source,
        first_background_source=first_background,
        second_background_source=second_background,
        palette_color=palette_color,
        background_distance=2.0,
        first_center_distance=20.0,
        second_center_distance=18.0,
    )


def test_build_persistence_combines_same_center_across_offsets() -> None:
    persistence = build_center_surround_persistence(
        candidates=(
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=2,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=4,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=8,
                orientation="vertical",
            ),
        ),
        minimum_offset_support=2,
    )

    assert persistence == (
        CenterSurroundPersistence(
            center_pixel=(
                10,
                10,
            ),
            supported_offsets=(
                2,
                4,
                8,
            ),
            candidate_count=3,
            horizontal_count=2,
            vertical_count=1,
        ),
    )


def test_build_persistence_counts_distinct_offsets_only() -> None:
    persistence = build_center_surround_persistence(
        candidates=(
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=4,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=4,
                orientation="vertical",
            ),
        ),
        minimum_offset_support=2,
    )

    assert persistence == ()


def test_build_persistence_excludes_insufficient_offset_support() -> None:
    persistence = build_center_surround_persistence(
        candidates=(
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=2,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    20,
                    20,
                ),
                offset_px=2,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    20,
                    20,
                ),
                offset_px=4,
                orientation="horizontal",
            ),
        ),
        minimum_offset_support=2,
    )

    assert tuple(item.center_pixel for item in persistence) == (
        (
            20,
            20,
        ),
    )


def test_build_persistence_orders_centers_by_position() -> None:
    persistence = build_center_surround_persistence(
        candidates=(
            _candidate(
                center_pixel=(
                    20,
                    10,
                ),
                offset_px=2,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    20,
                    10,
                ),
                offset_px=4,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    30,
                    5,
                ),
                offset_px=2,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    30,
                    5,
                ),
                offset_px=4,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=2,
                orientation="horizontal",
            ),
            _candidate(
                center_pixel=(
                    10,
                    10,
                ),
                offset_px=4,
                orientation="horizontal",
            ),
        ),
        minimum_offset_support=2,
    )

    assert tuple(item.center_pixel for item in persistence) == (
        (
            30,
            5,
        ),
        (
            10,
            10,
        ),
        (
            20,
            10,
        ),
    )


def test_build_persistence_rejects_non_positive_minimum_support() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_offset_support must be greater than zero",
    ):
        build_center_surround_persistence(
            candidates=(),
            minimum_offset_support=0,
        )


def test_summarize_persistence_reports_support_histogram() -> None:
    persistence = (
        CenterSurroundPersistence(
            center_pixel=(
                10,
                10,
            ),
            supported_offsets=(
                2,
                4,
            ),
            candidate_count=2,
            horizontal_count=2,
            vertical_count=0,
        ),
        CenterSurroundPersistence(
            center_pixel=(
                20,
                20,
            ),
            supported_offsets=(
                2,
                4,
            ),
            candidate_count=3,
            horizontal_count=2,
            vertical_count=1,
        ),
        CenterSurroundPersistence(
            center_pixel=(
                30,
                30,
            ),
            supported_offsets=(
                2,
                4,
                8,
            ),
            candidate_count=3,
            horizontal_count=2,
            vertical_count=1,
        ),
    )

    summary = summarize_center_surround_persistence(
        persistence=persistence,
        minimum_offset_support=2,
    )

    assert summary == CenterSurroundPersistenceSummary(
        minimum_offset_support=2,
        center_count=3,
        support_histogram=(
            (
                2,
                2,
            ),
            (
                3,
                1,
            ),
        ),
    )


def test_format_persistence_summary_reports_histogram() -> None:
    summary = CenterSurroundPersistenceSummary(
        minimum_offset_support=2,
        center_count=553,
        support_histogram=(
            (
                2,
                458,
            ),
            (
                3,
                95,
            ),
        ),
    )

    assert format_center_surround_persistence_summary(
        summary,
    ) == (
        "center_surround_persistence="
        "minimum_offset_support=2, "
        "centers=553, "
        "support_histogram=2:458|3:95"
    )


def test_persistence_preview_marks_only_persistent_centers() -> None:
    first = _rgb(
        10,
    )
    persistent_center = _rgb(
        30,
    )
    other = _rgb(
        40,
    )

    image = InputImage.from_rows(
        (
            (
                first,
                persistent_center,
                other,
            ),
        )
    )

    persistence = (
        CenterSurroundPersistence(
            center_pixel=(
                1,
                0,
            ),
            supported_offsets=(
                2,
                4,
            ),
            candidate_count=2,
            horizontal_count=2,
            vertical_count=0,
        ),
    )

    preview = build_center_surround_persistence_preview_bmp(
        image=image,
        persistence=persistence,
    )

    assert preview[:2] == b"BM"

    pixel_offset = 54

    assert preview[pixel_offset : pixel_offset + 3] == bytes(
        (
            first.blue,
            first.green,
            first.red,
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
            other.blue,
            other.green,
            other.red,
        ),
    )


def test_persistence_preview_path_is_deterministic() -> None:
    assert center_surround_persistence_preview_path(
        output_directory=Path(
            "output",
        ),
        case="simple",
    ) == (
        Path(
            "output",
        )
        / "quantization-center-surround-persistent-simple.bmp"
    )


def test_parser_uses_default_minimum_offset_support() -> None:
    args = build_parser().parse_args(
        [],
    )

    assert args.center_surround_min_offset_support == 2


def test_parser_accepts_custom_minimum_offset_support() -> None:
    args = build_parser().parse_args(
        [
            "--center-surround-min-offset-support",
            "3",
        ],
    )

    assert args.center_surround_min_offset_support == 3
