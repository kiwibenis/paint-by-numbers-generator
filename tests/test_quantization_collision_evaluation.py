# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
)
from tools.evaluate_quantization_collisions import (
    cluster_source_colors,
    find_collapsed_boundaries,
    rank_palette_candidates,
    summarize_palette_utilization,
)
from tools.quantization_source_spread import (
    build_palette_source_color_spreads,
    format_palette_source_color_spread,
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
            l=float(
                rgb.red,
            ),
            a=0.0,
            b=0.0,
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
    *,
    number: int,
    name: str,
    lightness: float,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=name,
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


def _palette(
    *colors: PaletteColor,
) -> Palette:
    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test Palette",
        version=1,
        colors=colors,
    )


def test_rank_palette_candidates_reports_three_nearest_colors() -> None:
    palette = _palette(
        _palette_color(
            number=1,
            name="First",
            lightness=0.0,
        ),
        _palette_color(
            number=2,
            name="Nearest",
            lightness=9.0,
        ),
        _palette_color(
            number=3,
            name="Second",
            lightness=12.0,
        ),
        _palette_color(
            number=4,
            name="Tied Later",
            lightness=20.0,
        ),
    )

    candidates = rank_palette_candidates(
        source=Lab(
            l=10.0,
            a=0.0,
            b=0.0,
        ),
        palette=palette,
        color_distance=LightnessDistance(),
        limit=3,
    )

    assert tuple(candidate.color.number for candidate in candidates) == (
        2,
        3,
        1,
    )

    assert tuple(candidate.distance for candidate in candidates) == pytest.approx(
        (
            1.0,
            2.0,
            10.0,
        ),
    )

    assert tuple(
        candidate.additional_distance for candidate in candidates
    ) == pytest.approx(
        (
            0.0,
            1.0,
            9.0,
        ),
    )


def test_rank_palette_candidates_preserves_palette_order_for_ties() -> None:
    palette = _palette(
        _palette_color(
            number=10,
            name="Earlier",
            lightness=8.0,
        ),
        _palette_color(
            number=20,
            name="Later",
            lightness=12.0,
        ),
    )

    candidates = rank_palette_candidates(
        source=Lab(
            l=10.0,
            a=0.0,
            b=0.0,
        ),
        palette=palette,
        color_distance=LightnessDistance(),
        limit=2,
    )

    assert tuple(candidate.color.number for candidate in candidates) == (
        10,
        20,
    )


def test_rank_palette_candidates_rejects_non_positive_limit() -> None:
    palette = _palette(
        _palette_color(
            number=1,
            name="Only",
            lightness=10.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        rank_palette_candidates(
            source=Lab(
                l=10.0,
                a=0.0,
                b=0.0,
            ),
            palette=palette,
            color_distance=LightnessDistance(),
            limit=0,
        )


def test_rank_palette_candidates_rejects_empty_palette() -> None:
    with pytest.raises(
        ValueError,
        match="Palette contains no colors",
    ):
        rank_palette_candidates(
            source=Lab(
                l=10.0,
                a=0.0,
                b=0.0,
            ),
            palette=_palette(),
            color_distance=LightnessDistance(),
            limit=3,
        )


def test_cluster_source_colors_groups_colors_within_threshold() -> None:
    colors = (
        _rgb(
            10,
        ),
        _rgb(
            11,
        ),
        _rgb(
            13,
        ),
        _rgb(
            30,
        ),
    )

    clusters = cluster_source_colors(
        colors=colors,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=2.0,
    )

    assert clusters == (
        (
            _rgb(
                10,
            ),
            _rgb(
                11,
            ),
        ),
        (
            _rgb(
                13,
            ),
        ),
        (
            _rgb(
                30,
            ),
        ),
    )


def test_cluster_source_colors_uses_first_seen_representative() -> None:
    colors = (
        _rgb(
            20,
        ),
        _rgb(
            19,
        ),
        _rgb(
            21,
        ),
    )

    clusters = cluster_source_colors(
        colors=colors,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=1.0,
    )

    assert clusters == (
        (
            _rgb(
                20,
            ),
            _rgb(
                19,
            ),
            _rgb(
                21,
            ),
        ),
    )


def test_cluster_source_colors_does_not_chain_clusters() -> None:
    colors = (
        _rgb(
            10,
        ),
        _rgb(
            12,
        ),
        _rgb(
            14,
        ),
    )

    clusters = cluster_source_colors(
        colors=colors,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
        maximum_distance=2.0,
    )

    assert clusters == (
        (
            _rgb(
                10,
            ),
            _rgb(
                12,
            ),
        ),
        (
            _rgb(
                14,
            ),
        ),
    )


def test_cluster_source_colors_rejects_negative_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_distance must not be negative",
    ):
        cluster_source_colors(
            colors=(
                _rgb(
                    10,
                ),
            ),
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            maximum_distance=-1.0,
        )


def test_cluster_source_colors_handles_empty_input() -> None:
    assert (
        cluster_source_colors(
            colors=(),
            converter=RedChannelConverter(),
            color_distance=LightnessDistance(),
            maximum_distance=1.0,
        )
        == ()
    )


def test_summarize_palette_utilization_reports_actual_usage() -> None:
    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        20,
    )
    third_source = _rgb(
        30,
    )

    first_palette_color = _palette_color(
        number=1,
        name="First",
        lightness=10.0,
    )
    second_palette_color = _palette_color(
        number=2,
        name="Second",
        lightness=20.0,
    )
    unused_palette_color = _palette_color(
        number=3,
        name="Unused",
        lightness=30.0,
    )

    image = InputImage.from_rows(
        (
            (
                first_source,
                first_source,
                second_source,
            ),
            (
                third_source,
                third_source,
                third_source,
            ),
        )
    )

    summary = summarize_palette_utilization(
        image=image,
        palette=_palette(
            first_palette_color,
            second_palette_color,
            unused_palette_color,
        ),
        color_matches={
            first_source: first_palette_color,
            second_source: first_palette_color,
            third_source: second_palette_color,
        },
    )

    assert summary.palette_color_count == 3
    assert summary.used_palette_color_count == 2
    assert summary.utilization_fraction == pytest.approx(
        2.0 / 3.0,
    )
    assert summary.distinct_source_color_count == 3
    assert summary.pixel_count == 6


def test_build_palette_source_color_spreads_measures_distinct_sources() -> None:
    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        20,
    )
    third_source = _rgb(
        30,
    )
    fourth_source = _rgb(
        40,
    )

    broad_palette_color = _palette_color(
        number=1,
        name="Broad",
        lightness=20.0,
    )
    narrow_palette_color = _palette_color(
        number=2,
        name="Narrow",
        lightness=40.0,
    )

    image = InputImage.from_rows(
        (
            (
                first_source,
                first_source,
                second_source,
                third_source,
                fourth_source,
            ),
        )
    )

    spreads = build_palette_source_color_spreads(
        image=image,
        color_matches={
            first_source: broad_palette_color,
            second_source: broad_palette_color,
            third_source: broad_palette_color,
            fourth_source: narrow_palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    assert tuple(spread.color.number for spread in spreads) == (
        1,
        2,
    )

    broad_spread = spreads[0]

    assert broad_spread.source_color_count == 3
    assert broad_spread.pixel_count == 4
    assert broad_spread.source_distance_min == pytest.approx(
        0.0,
    )
    assert broad_spread.source_distance_max == pytest.approx(
        10.0,
    )
    assert broad_spread.source_distance_mean == pytest.approx(
        20.0 / 3.0,
    )

    narrow_spread = spreads[1]

    assert narrow_spread.source_color_count == 1
    assert narrow_spread.pixel_count == 1
    assert narrow_spread.source_distance_min == pytest.approx(
        0.0,
    )
    assert narrow_spread.source_distance_max == pytest.approx(
        0.0,
    )
    assert narrow_spread.source_distance_mean == pytest.approx(
        0.0,
    )


def test_palette_source_color_spreads_rank_source_color_count_first() -> None:
    first_palette_color = _palette_color(
        number=1,
        name="More Sources",
        lightness=15.0,
    )
    second_palette_color = _palette_color(
        number=2,
        name="Larger Distance",
        lightness=100.0,
    )

    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        20,
    )
    third_source = _rgb(
        0,
    )

    image = InputImage.from_rows(
        (
            (
                first_source,
                second_source,
                third_source,
            ),
        )
    )

    spreads = build_palette_source_color_spreads(
        image=image,
        color_matches={
            first_source: first_palette_color,
            second_source: first_palette_color,
            third_source: second_palette_color,
        },
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    assert tuple(spread.color.number for spread in spreads) == (
        1,
        2,
    )


def test_format_palette_source_color_spread_reports_distances() -> None:
    palette_color = _palette_color(
        number=7,
        name="Measured",
        lightness=20.0,
    )

    source_colors = (
        _rgb(
            10,
        ),
        _rgb(
            20,
        ),
        _rgb(
            30,
        ),
    )

    image = InputImage.from_rows((source_colors,))

    spread = build_palette_source_color_spreads(
        image=image,
        color_matches={source: palette_color for source in source_colors},
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )[0]

    assert format_palette_source_color_spread(
        spread,
    ) == (
        "palette_source_spread="
        "number=7, "
        "name=Measured, "
        "source_colors=3, "
        "pixels=3, "
        "source_delta_e_min=0.000000, "
        "source_delta_e_max=10.000000, "
        "source_delta_e_mean=6.666667"
    )


def test_find_collapsed_boundaries_counts_lost_local_boundaries() -> None:
    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        20,
    )
    third_source = _rgb(
        30,
    )

    shared_palette_color = _palette_color(
        number=1,
        name="Shared",
        lightness=10.0,
    )
    separate_palette_color = _palette_color(
        number=2,
        name="Separate",
        lightness=20.0,
    )

    image = InputImage.from_rows(
        (
            (
                first_source,
                second_source,
                third_source,
            ),
            (
                first_source,
                second_source,
                third_source,
            ),
        )
    )

    collisions = find_collapsed_boundaries(
        image=image,
        color_matches={
            first_source: shared_palette_color,
            second_source: shared_palette_color,
            third_source: separate_palette_color,
        },
    )

    assert (
        len(
            collisions,
        )
        == 1
    )

    collision = collisions[0]

    assert collision.first_source == first_source
    assert collision.second_source == second_source
    assert collision.palette_color == shared_palette_color
    assert collision.boundary_length_px == 2
    assert collision.source_pixel_count == 4


def test_find_collapsed_boundaries_ignores_preserved_boundaries() -> None:
    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        20,
    )

    first_palette_color = _palette_color(
        number=1,
        name="First",
        lightness=10.0,
    )
    second_palette_color = _palette_color(
        number=2,
        name="Second",
        lightness=20.0,
    )

    image = InputImage.from_rows(
        (
            (
                first_source,
                second_source,
            ),
        )
    )

    collisions = find_collapsed_boundaries(
        image=image,
        color_matches={
            first_source: first_palette_color,
            second_source: second_palette_color,
        },
    )

    assert collisions == ()


def test_find_collapsed_boundaries_orders_highest_impact_first() -> None:
    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        20,
    )
    third_source = _rgb(
        30,
    )

    shared_palette_color = _palette_color(
        number=1,
        name="Shared",
        lightness=10.0,
    )

    image = InputImage.from_rows(
        (
            (
                first_source,
                second_source,
                first_source,
                second_source,
            ),
            (
                third_source,
                third_source,
                first_source,
                second_source,
            ),
        )
    )

    collisions = find_collapsed_boundaries(
        image=image,
        color_matches={
            first_source: shared_palette_color,
            second_source: shared_palette_color,
            third_source: shared_palette_color,
        },
    )

    assert collisions[0].boundary_length_px >= collisions[1].boundary_length_px
