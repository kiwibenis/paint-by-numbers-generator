# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import RGB, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    CollapsedBoundary,
    PaletteCandidate,
    QuantizationRescueDiagnostic,
    rank_quantization_rescue_diagnostics_by_boundary_impact,
    summarize_quantization_rescue_diagnostics,
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


def _candidate(
    *,
    color: PaletteColor,
    additional_distance: float,
) -> PaletteCandidate:
    return PaletteCandidate(
        color=color,
        distance=additional_distance + 1.0,
        additional_distance=additional_distance,
    )


def _diagnostic(
    *,
    identifier: int,
    source_distance: float,
    rescue_cost: float | None,
    boundary_length_px: int,
) -> QuantizationRescueDiagnostic:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    candidate = (
        _candidate(
            color=alternative,
            additional_distance=rescue_cost,
        )
        if rescue_cost is not None
        else None
    )

    return QuantizationRescueDiagnostic(
        collision=CollapsedBoundary(
            first_source=_rgb(
                identifier,
            ),
            second_source=_rgb(
                identifier + 1,
            ),
            palette_color=current,
            boundary_length_px=boundary_length_px,
            source_pixel_count=20,
        ),
        source_distance=source_distance,
        first_alternative=candidate,
        second_alternative=None,
        minimum_rescue_cost=rescue_cost,
    )


def test_rescue_summary_reports_total_boundary_length() -> None:
    summary = summarize_quantization_rescue_diagnostics(
        diagnostics=(
            _diagnostic(
                identifier=10,
                source_distance=2.0,
                rescue_cost=0.5,
                boundary_length_px=100,
            ),
            _diagnostic(
                identifier=20,
                source_distance=10.0,
                rescue_cost=1.0,
                boundary_length_px=40,
            ),
            _diagnostic(
                identifier=30,
                source_distance=15.0,
                rescue_cost=8.0,
                boundary_length_px=10,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert summary.collision_boundary_length_px == 150


def test_rescue_summary_reports_low_source_distance_boundary_length() -> None:
    summary = summarize_quantization_rescue_diagnostics(
        diagnostics=(
            _diagnostic(
                identifier=10,
                source_distance=2.0,
                rescue_cost=0.5,
                boundary_length_px=100,
            ),
            _diagnostic(
                identifier=20,
                source_distance=5.0,
                rescue_cost=0.5,
                boundary_length_px=50,
            ),
            _diagnostic(
                identifier=30,
                source_distance=6.0,
                rescue_cost=0.5,
                boundary_length_px=25,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert summary.low_source_distance_boundary_length_px == 150
    assert summary.meaningful_boundary_length_px == 25


def test_rescue_summary_reports_cumulative_rescue_boundary_lengths() -> None:
    summary = summarize_quantization_rescue_diagnostics(
        diagnostics=(
            _diagnostic(
                identifier=10,
                source_distance=10.0,
                rescue_cost=0.5,
                boundary_length_px=100,
            ),
            _diagnostic(
                identifier=20,
                source_distance=10.0,
                rescue_cost=1.5,
                boundary_length_px=50,
            ),
            _diagnostic(
                identifier=30,
                source_distance=10.0,
                rescue_cost=4.0,
                boundary_length_px=25,
            ),
            _diagnostic(
                identifier=40,
                source_distance=10.0,
                rescue_cost=8.0,
                boundary_length_px=10,
            ),
            _diagnostic(
                identifier=50,
                source_distance=10.0,
                rescue_cost=None,
                boundary_length_px=5,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert summary.meaningful_boundary_length_px == 190

    assert summary.rescue_cost_le_1_boundary_length_px == 100
    assert summary.rescue_cost_le_2_boundary_length_px == 150
    assert summary.rescue_cost_le_5_boundary_length_px == 175

    assert summary.expensive_rescue_boundary_length_px == 10
    assert summary.unavailable_rescue_boundary_length_px == 5


def test_boundary_impact_ranking_excludes_low_source_distance() -> None:
    low_distance = _diagnostic(
        identifier=10,
        source_distance=4.0,
        rescue_cost=0.1,
        boundary_length_px=1000,
    )

    meaningful = _diagnostic(
        identifier=20,
        source_distance=10.0,
        rescue_cost=2.0,
        boundary_length_px=10,
    )

    ranked = rank_quantization_rescue_diagnostics_by_boundary_impact(
        diagnostics=(
            low_distance,
            meaningful,
        ),
        source_distance_threshold=5.0,
    )

    assert ranked == (meaningful,)


def test_boundary_impact_ranking_prefers_longer_boundary() -> None:
    short = _diagnostic(
        identifier=10,
        source_distance=20.0,
        rescue_cost=0.1,
        boundary_length_px=5,
    )

    long = _diagnostic(
        identifier=20,
        source_distance=10.0,
        rescue_cost=4.0,
        boundary_length_px=100,
    )

    ranked = rank_quantization_rescue_diagnostics_by_boundary_impact(
        diagnostics=(
            short,
            long,
        ),
        source_distance_threshold=5.0,
    )

    assert ranked == (
        long,
        short,
    )


def test_boundary_impact_ranking_prefers_lower_rescue_cost_on_tie() -> None:
    expensive = _diagnostic(
        identifier=10,
        source_distance=10.0,
        rescue_cost=4.0,
        boundary_length_px=100,
    )

    cheap = _diagnostic(
        identifier=20,
        source_distance=10.0,
        rescue_cost=1.0,
        boundary_length_px=100,
    )

    ranked = rank_quantization_rescue_diagnostics_by_boundary_impact(
        diagnostics=(
            expensive,
            cheap,
        ),
        source_distance_threshold=5.0,
    )

    assert ranked == (
        cheap,
        expensive,
    )


def test_boundary_impact_ranking_prefers_stronger_source_contrast_after_cost() -> None:
    weaker = _diagnostic(
        identifier=10,
        source_distance=8.0,
        rescue_cost=1.0,
        boundary_length_px=100,
    )

    stronger = _diagnostic(
        identifier=20,
        source_distance=20.0,
        rescue_cost=1.0,
        boundary_length_px=100,
    )

    ranked = rank_quantization_rescue_diagnostics_by_boundary_impact(
        diagnostics=(
            weaker,
            stronger,
        ),
        source_distance_threshold=5.0,
    )

    assert ranked == (
        stronger,
        weaker,
    )


def test_boundary_impact_ranking_places_unavailable_rescue_last_on_tie() -> None:
    unavailable = _diagnostic(
        identifier=10,
        source_distance=20.0,
        rescue_cost=None,
        boundary_length_px=100,
    )

    available = _diagnostic(
        identifier=20,
        source_distance=10.0,
        rescue_cost=5.0,
        boundary_length_px=100,
    )

    ranked = rank_quantization_rescue_diagnostics_by_boundary_impact(
        diagnostics=(
            unavailable,
            available,
        ),
        source_distance_threshold=5.0,
    )

    assert ranked == (
        available,
        unavailable,
    )
