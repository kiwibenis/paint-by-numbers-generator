# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

from pbn.models import RGB, InputImage, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    CollapsedBoundary,
    PaletteCandidate,
    QuantizationRescueDiagnostic,
    build_collapsed_boundary_component_preview_bmp,
    build_collapsed_boundary_components,
    collapsed_boundary_component_preview_path,
    rank_collapsed_boundary_components,
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


def _image(
    rows: tuple[
        tuple[RGB, ...],
        ...,
    ],
) -> InputImage:
    return InputImage.from_rows(rows)


def _diagnostic(
    *,
    first: RGB,
    second: RGB,
    palette_color: PaletteColor,
    source_distance: float,
    rescue_cost: float | None,
) -> QuantizationRescueDiagnostic:
    first_source, second_source = sorted(
        (
            first,
            second,
        ),
        key=lambda color: color.as_tuple(),
    )

    alternative = (
        PaletteCandidate(
            color=_palette_color(
                200,
                200,
            ),
            distance=(1.0 + rescue_cost),
            additional_distance=rescue_cost,
        )
        if rescue_cost is not None
        else None
    )

    return QuantizationRescueDiagnostic(
        collision=CollapsedBoundary(
            first_source=first_source,
            second_source=second_source,
            palette_color=palette_color,
            boundary_length_px=1,
            source_pixel_count=2,
        ),
        source_distance=source_distance,
        first_alternative=alternative,
        second_alternative=None,
        minimum_rescue_cost=rescue_cost,
    )


def test_collapsed_boundary_components_join_adjacent_spatial_edges() -> None:
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
        100,
    )

    image = _image(
        (
            (
                first,
                second,
            ),
            (
                first,
                third,
            ),
        ),
    )

    diagnostics = (
        _diagnostic(
            first=first,
            second=second,
            palette_color=palette_color,
            source_distance=10.0,
            rescue_cost=1.0,
        ),
        _diagnostic(
            first=first,
            second=third,
            palette_color=palette_color,
            source_distance=12.0,
            rescue_cost=2.0,
        ),
        _diagnostic(
            first=second,
            second=third,
            palette_color=palette_color,
            source_distance=2.0,
            rescue_cost=0.5,
        ),
    )

    components = build_collapsed_boundary_components(
        image=image,
        color_matches={
            first: palette_color,
            second: palette_color,
            third: palette_color,
        },
        rescue_diagnostics=diagnostics,
        source_distance_threshold=5.0,
    )

    assert (
        len(
            components,
        )
        == 1
    )
    assert components[0].edge_count == 2


def test_collapsed_boundary_components_keep_disconnected_edges_separate() -> None:
    first = _rgb(
        10,
    )
    second = _rgb(
        30,
    )
    separator = _rgb(
        70,
    )

    collapsed_palette = _palette_color(
        100,
        100,
    )
    separator_palette = _palette_color(
        101,
        200,
    )

    image = _image(
        (
            (
                first,
                second,
                separator,
                first,
                second,
            ),
        ),
    )

    components = build_collapsed_boundary_components(
        image=image,
        color_matches={
            first: collapsed_palette,
            second: collapsed_palette,
            separator: separator_palette,
        },
        rescue_diagnostics=(
            _diagnostic(
                first=first,
                second=second,
                palette_color=collapsed_palette,
                source_distance=10.0,
                rescue_cost=1.0,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert (
        len(
            components,
        )
        == 2
    )
    assert tuple(component.edge_count for component in components) == (
        1,
        1,
    )


def test_collapsed_boundary_components_exclude_low_source_distance() -> None:
    first = _rgb(
        10,
    )
    second = _rgb(
        30,
    )

    palette_color = _palette_color(
        100,
        100,
    )

    components = build_collapsed_boundary_components(
        image=_image(
            (
                (
                    first,
                    second,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            second: palette_color,
        },
        rescue_diagnostics=(
            _diagnostic(
                first=first,
                second=second,
                palette_color=palette_color,
                source_distance=5.0,
                rescue_cost=0.5,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert components == ()


def test_collapsed_boundary_component_reports_spatial_metrics() -> None:
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
        100,
    )

    image = _image(
        (
            (
                first,
                second,
            ),
            (
                first,
                third,
            ),
        ),
    )

    components = build_collapsed_boundary_components(
        image=image,
        color_matches={
            first: palette_color,
            second: palette_color,
            third: palette_color,
        },
        rescue_diagnostics=(
            _diagnostic(
                first=first,
                second=second,
                palette_color=palette_color,
                source_distance=6.0,
                rescue_cost=0.5,
            ),
            _diagnostic(
                first=first,
                second=third,
                palette_color=palette_color,
                source_distance=10.0,
                rescue_cost=2.0,
            ),
            _diagnostic(
                first=second,
                second=third,
                palette_color=palette_color,
                source_distance=14.0,
                rescue_cost=None,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert (
        len(
            components,
        )
        == 1
    )

    component = components[0]

    assert component.edge_count == 3

    assert (
        component.min_x,
        component.min_y,
        component.max_x,
        component.max_y,
    ) == (
        0,
        0,
        1,
        1,
    )

    assert component.source_distance_min == 6.0
    assert component.source_distance_max == 14.0
    assert component.source_distance_mean == 10.0

    assert component.rescue_cost_min == 0.5
    assert component.rescue_cost_mean == 1.25

    assert component.unavailable_rescue_edge_count == 1
    assert component.dominant_palette_color == palette_color


def test_collapsed_boundary_component_ranking_prefers_longer_component() -> None:
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
        100,
    )

    long_components = build_collapsed_boundary_components(
        image=_image(
            (
                (
                    first,
                    second,
                ),
                (
                    first,
                    third,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            second: palette_color,
            third: palette_color,
        },
        rescue_diagnostics=(
            _diagnostic(
                first=first,
                second=second,
                palette_color=palette_color,
                source_distance=10.0,
                rescue_cost=1.0,
            ),
            _diagnostic(
                first=first,
                second=third,
                palette_color=palette_color,
                source_distance=12.0,
                rescue_cost=1.0,
            ),
            _diagnostic(
                first=second,
                second=third,
                palette_color=palette_color,
                source_distance=2.0,
                rescue_cost=1.0,
            ),
        ),
        source_distance_threshold=5.0,
    )

    short_components = build_collapsed_boundary_components(
        image=_image(
            (
                (
                    first,
                    second,
                ),
            ),
        ),
        color_matches={
            first: palette_color,
            second: palette_color,
        },
        rescue_diagnostics=(
            _diagnostic(
                first=first,
                second=second,
                palette_color=palette_color,
                source_distance=20.0,
                rescue_cost=0.1,
            ),
        ),
        source_distance_threshold=5.0,
    )

    ranked = rank_collapsed_boundary_components(
        (
            short_components[0],
            long_components[0],
        ),
    )

    assert ranked == (
        long_components[0],
        short_components[0],
    )


def test_collapsed_boundary_component_preview_marks_incident_pixels() -> None:
    first = _rgb(
        10,
    )
    second = _rgb(
        30,
    )
    untouched = _rgb(
        70,
    )

    collapsed_palette = _palette_color(
        100,
        100,
    )
    untouched_palette = _palette_color(
        101,
        200,
    )

    image = _image(
        (
            (
                first,
                second,
                untouched,
            ),
        ),
    )

    components = build_collapsed_boundary_components(
        image=image,
        color_matches={
            first: collapsed_palette,
            second: collapsed_palette,
            untouched: untouched_palette,
        },
        rescue_diagnostics=(
            _diagnostic(
                first=first,
                second=second,
                palette_color=collapsed_palette,
                source_distance=10.0,
                rescue_cost=1.0,
            ),
        ),
        source_distance_threshold=5.0,
    )

    preview = build_collapsed_boundary_component_preview_bmp(
        image=image,
        components=components,
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
            0,
            0,
            255,
        ),
    )

    assert preview[pixel_offset + 6 : pixel_offset + 9] == bytes(
        (
            untouched.blue,
            untouched.green,
            untouched.red,
        ),
    )


def test_collapsed_boundary_component_preview_path_is_deterministic() -> None:
    assert collapsed_boundary_component_preview_path(
        output_directory=Path(
            "output",
        ),
        case="simple",
    ) == (
        Path(
            "output",
        )
        / "quantization-collapsed-boundary-components-simple.bmp"
    )
