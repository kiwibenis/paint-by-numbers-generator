# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeCandidate,
    RegionMergeCost,
    RegionMergeMetrics,
    RegionMergeStep,
)
from pbn.models.pixel_index import pack_pixels
from tools.evaluate_region_neighbor_contrast import (
    build_neighbor_contrast_diagnostics,
    format_neighbor_contrast_diagnostic,
)


class AbsoluteLightnessDistance(ColorDistance):
    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return abs(first.l - second.l)


def _color(
    number: int,
    *,
    lightness: float,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=RGB(
            red=number,
            green=number,
            blue=number,
        ),
        lab=Lab(
            l=lightness,
            a=0.0,
            b=0.0,
        ),
    )


def _region(
    region_id: int,
    *,
    lightness: float,
    pixels: frozenset[tuple[int, int]],
) -> Region:
    return Region(
        id=region_id,
        color=_color(
            region_id,
            lightness=lightness,
        ),
        pixels=pack_pixels(
            pixels,
        ),
    )


def _merge_step(
    *,
    source_id: int,
    target_id: int,
    color_difference: float,
    source_area: int,
    target_area: int,
    merged_area: int,
    shared_border_length: int,
    source_perimeter: int,
    target_perimeter: int,
    merged_perimeter: int,
    cost: float,
) -> RegionMergeStep:
    metrics = RegionMergeMetrics(
        color_difference=color_difference,
        source_area=source_area,
        target_area=target_area,
        merged_area=merged_area,
        affected_area_ratio=(source_area / merged_area),
        shared_border_length=shared_border_length,
        source_perimeter=source_perimeter,
        target_perimeter=target_perimeter,
        merged_perimeter=merged_perimeter,
    )

    return RegionMergeStep(
        candidate=RegionMergeCandidate(
            source_id=source_id,
            target_id=target_id,
        ),
        metrics=metrics,
        cost=RegionMergeCost(
            color_penalty=0.5,
            affected_area_penalty=(metrics.affected_area_ratio),
            border_penalty=0.5,
            geometry_penalty=0.0,
            value=cost,
        ),
    )


def _regions() -> tuple[Region, ...]:
    return (
        _region(
            1,
            lightness=10.0,
            pixels=frozenset(
                {
                    (1, 0),
                    (1, 1),
                },
            ),
        ),
        _region(
            2,
            lightness=20.0,
            pixels=frozenset(
                {
                    (0, 0),
                    (0, 1),
                },
            ),
        ),
        _region(
            3,
            lightness=40.0,
            pixels=frozenset(
                {
                    (2, 0),
                    (2, 1),
                },
            ),
        ),
    )


def _merge_steps() -> tuple[RegionMergeStep, ...]:
    return (
        _merge_step(
            source_id=1,
            target_id=2,
            color_difference=10.0,
            source_area=2,
            target_area=2,
            merged_area=4,
            shared_border_length=2,
            source_perimeter=6,
            target_perimeter=6,
            merged_perimeter=8,
            cost=0.4,
        ),
        _merge_step(
            source_id=2,
            target_id=3,
            color_difference=20.0,
            source_area=4,
            target_area=2,
            merged_area=6,
            shared_border_length=2,
            source_perimeter=8,
            target_perimeter=6,
            merged_perimeter=10,
            cost=0.45,
        ),
    )


def test_neighbor_contrast_uses_all_source_neighbors() -> None:
    diagnostics = build_neighbor_contrast_diagnostics(
        regions=_regions(),
        merge_steps=_merge_steps(),
        color_distance=AbsoluteLightnessDistance(),
    )

    first = diagnostics[0]

    assert first.neighbor_count == 2
    assert first.total_shared_border_length == 4

    assert first.neighbor_boundary_coverage == pytest.approx(
        4 / 6,
    )

    assert first.target_neighbor_border_fraction == pytest.approx(
        0.5,
    )

    assert first.dominant_neighbor_border_fraction == pytest.approx(
        0.5,
    )

    assert first.min_neighbor_color_difference == 10.0
    assert first.max_neighbor_color_difference == 30.0
    assert first.mean_neighbor_color_difference == 20.0

    assert first.boundary_weighted_neighbor_color_difference == pytest.approx(
        20.0,
    )

    assert first.boundary_weighted_neighbor_color_penalty == pytest.approx(
        0.625,
    )


def test_neighbor_contrast_replays_dynamic_region_state() -> None:
    diagnostics = build_neighbor_contrast_diagnostics(
        regions=_regions(),
        merge_steps=_merge_steps(),
        color_distance=AbsoluteLightnessDistance(),
    )

    second = diagnostics[1]

    assert second.diagnostic.candidate.source_id == 2
    assert second.diagnostic.candidate.target_id == 3

    assert second.neighbor_count == 1
    assert second.total_shared_border_length == 2

    assert second.neighbor_boundary_coverage == pytest.approx(
        0.25,
    )

    assert second.target_neighbor_border_fraction == 1.0
    assert second.dominant_neighbor_border_fraction == 1.0

    assert second.min_neighbor_color_difference == 20.0
    assert second.max_neighbor_color_difference == 20.0
    assert second.mean_neighbor_color_difference == 20.0

    assert second.boundary_weighted_neighbor_color_difference == pytest.approx(
        20.0,
    )

    assert second.boundary_weighted_neighbor_color_penalty == pytest.approx(
        2 / 3,
    )


def test_format_neighbor_contrast_reports_correlated_metrics() -> None:
    diagnostic = build_neighbor_contrast_diagnostics(
        regions=_regions(),
        merge_steps=_merge_steps(),
        color_distance=AbsoluteLightnessDistance(),
    )[0]

    formatted = format_neighbor_contrast_diagnostic(
        diagnostic,
        step_number=1,
    )

    assert "step=1" in formatted
    assert "source_id=1" in formatted
    assert "target_id=2" in formatted
    assert "neighbor_count=2" in formatted
    assert "neighbor_boundary_coverage=0.666667" in formatted
    assert "target_neighbor_border_fraction=0.500000" in formatted
    assert "dominant_neighbor_border_fraction=0.500000" in formatted
    assert "min_neighbor_color_difference=10.000000" in formatted
    assert "max_neighbor_color_difference=30.000000" in formatted
    assert "mean_neighbor_color_difference=20.000000" in formatted
    assert "boundary_weighted_neighbor_color_difference=20.000000" in formatted
    assert "boundary_weighted_neighbor_color_penalty=0.625000" in formatted
    assert "source_non_compactness=" in formatted
