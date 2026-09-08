# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import RGB, Lab, PaletteColor
from tools.evaluate_quantization_collisions import (
    CollapsedBoundary,
    PaletteCandidate,
    QuantizationRescueDiagnostic,
    SourceColorEvaluation,
    build_quantization_rescue_diagnostics,
    rank_quantization_rescue_diagnostics,
    summarize_quantization_rescue_diagnostics,
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
            l=float(rgb.red),
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


def _candidate(
    *,
    color: PaletteColor,
    distance: float,
    additional_distance: float,
) -> PaletteCandidate:
    return PaletteCandidate(
        color=color,
        distance=distance,
        additional_distance=additional_distance,
    )


def test_build_quantization_rescue_diagnostics_reports_source_distance() -> None:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        30,
    )

    collision = CollapsedBoundary(
        first_source=first_source,
        second_source=second_source,
        palette_color=current,
        boundary_length_px=8,
        source_pixel_count=20,
    )

    evaluations = {
        first_source: SourceColorEvaluation(
            source=first_source,
            pixel_count=12,
            candidates=(
                _candidate(
                    color=current,
                    distance=1.0,
                    additional_distance=0.0,
                ),
                _candidate(
                    color=alternative,
                    distance=2.0,
                    additional_distance=1.0,
                ),
            ),
        ),
        second_source: SourceColorEvaluation(
            source=second_source,
            pixel_count=8,
            candidates=(
                _candidate(
                    color=current,
                    distance=1.5,
                    additional_distance=0.0,
                ),
                _candidate(
                    color=alternative,
                    distance=3.0,
                    additional_distance=1.5,
                ),
            ),
        ),
    }

    diagnostics = build_quantization_rescue_diagnostics(
        collisions=(collision,),
        evaluations_by_source=evaluations,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    assert diagnostics[0].source_distance == 20.0


def test_build_quantization_rescue_diagnostics_reports_best_alternatives() -> None:
    current = _palette_color(
        100,
        10,
    )
    first_alternative = _palette_color(
        101,
        20,
    )
    second_alternative = _palette_color(
        102,
        30,
    )

    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        30,
    )

    collision = CollapsedBoundary(
        first_source=first_source,
        second_source=second_source,
        palette_color=current,
        boundary_length_px=8,
        source_pixel_count=20,
    )

    first_candidate = _candidate(
        color=first_alternative,
        distance=1.8,
        additional_distance=0.8,
    )
    second_candidate = _candidate(
        color=second_alternative,
        distance=2.4,
        additional_distance=0.4,
    )

    evaluations = {
        first_source: SourceColorEvaluation(
            source=first_source,
            pixel_count=12,
            candidates=(
                _candidate(
                    color=current,
                    distance=1.0,
                    additional_distance=0.0,
                ),
                first_candidate,
            ),
        ),
        second_source: SourceColorEvaluation(
            source=second_source,
            pixel_count=8,
            candidates=(
                _candidate(
                    color=current,
                    distance=2.0,
                    additional_distance=0.0,
                ),
                second_candidate,
            ),
        ),
    }

    diagnostics = build_quantization_rescue_diagnostics(
        collisions=(collision,),
        evaluations_by_source=evaluations,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    diagnostic = diagnostics[0]

    assert diagnostic.first_alternative == first_candidate
    assert diagnostic.second_alternative == second_candidate
    assert diagnostic.minimum_rescue_cost == 0.4


def test_build_quantization_rescue_diagnostics_ignores_current_palette_color() -> None:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        30,
    )

    collision = CollapsedBoundary(
        first_source=first_source,
        second_source=second_source,
        palette_color=current,
        boundary_length_px=8,
        source_pixel_count=20,
    )

    alternative_candidate = _candidate(
        color=alternative,
        distance=2.0,
        additional_distance=1.0,
    )

    evaluations = {
        first_source: SourceColorEvaluation(
            source=first_source,
            pixel_count=12,
            candidates=(
                _candidate(
                    color=current,
                    distance=1.0,
                    additional_distance=0.0,
                ),
                _candidate(
                    color=current,
                    distance=1.1,
                    additional_distance=0.1,
                ),
                alternative_candidate,
            ),
        ),
        second_source: SourceColorEvaluation(
            source=second_source,
            pixel_count=8,
            candidates=(
                _candidate(
                    color=current,
                    distance=1.0,
                    additional_distance=0.0,
                ),
                alternative_candidate,
            ),
        ),
    }

    diagnostics = build_quantization_rescue_diagnostics(
        collisions=(collision,),
        evaluations_by_source=evaluations,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    assert diagnostics[0].first_alternative == alternative_candidate


def test_build_quantization_rescue_diagnostics_handles_missing_alternative() -> None:
    current = _palette_color(
        100,
        10,
    )

    first_source = _rgb(
        10,
    )
    second_source = _rgb(
        30,
    )

    collision = CollapsedBoundary(
        first_source=first_source,
        second_source=second_source,
        palette_color=current,
        boundary_length_px=8,
        source_pixel_count=20,
    )

    evaluations = {
        first_source: SourceColorEvaluation(
            source=first_source,
            pixel_count=12,
            candidates=(
                _candidate(
                    color=current,
                    distance=1.0,
                    additional_distance=0.0,
                ),
            ),
        ),
        second_source: SourceColorEvaluation(
            source=second_source,
            pixel_count=8,
            candidates=(
                _candidate(
                    color=current,
                    distance=2.0,
                    additional_distance=0.0,
                ),
            ),
        ),
    }

    diagnostics = build_quantization_rescue_diagnostics(
        collisions=(collision,),
        evaluations_by_source=evaluations,
        converter=RedChannelConverter(),
        color_distance=LightnessDistance(),
    )

    diagnostic = diagnostics[0]

    assert diagnostic.first_alternative is None
    assert diagnostic.second_alternative is None
    assert diagnostic.minimum_rescue_cost is None


def test_rank_quantization_rescue_diagnostics_excludes_small_source_distance() -> None:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    diagnostics = (
        QuantizationRescueDiagnostic(
            collision=CollapsedBoundary(
                first_source=_rgb(10),
                second_source=_rgb(14),
                palette_color=current,
                boundary_length_px=100,
                source_pixel_count=200,
            ),
            source_distance=4.0,
            first_alternative=_candidate(
                color=alternative,
                distance=2.0,
                additional_distance=1.0,
            ),
            second_alternative=None,
            minimum_rescue_cost=1.0,
        ),
        QuantizationRescueDiagnostic(
            collision=CollapsedBoundary(
                first_source=_rgb(10),
                second_source=_rgb(20),
                palette_color=current,
                boundary_length_px=10,
                source_pixel_count=20,
            ),
            source_distance=10.0,
            first_alternative=_candidate(
                color=alternative,
                distance=2.0,
                additional_distance=1.0,
            ),
            second_alternative=None,
            minimum_rescue_cost=1.0,
        ),
    )

    ranked = rank_quantization_rescue_diagnostics(
        diagnostics=diagnostics,
        source_distance_threshold=5.0,
    )

    assert (
        len(
            ranked,
        )
        == 1
    )
    assert ranked[0].source_distance == 10.0


def test_rank_quantization_rescue_diagnostics_prefers_cheaper_rescue() -> None:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    expensive = QuantizationRescueDiagnostic(
        collision=CollapsedBoundary(
            first_source=_rgb(10),
            second_source=_rgb(30),
            palette_color=current,
            boundary_length_px=100,
            source_pixel_count=200,
        ),
        source_distance=20.0,
        first_alternative=_candidate(
            color=alternative,
            distance=5.0,
            additional_distance=4.0,
        ),
        second_alternative=None,
        minimum_rescue_cost=4.0,
    )

    cheap = QuantizationRescueDiagnostic(
        collision=CollapsedBoundary(
            first_source=_rgb(40),
            second_source=_rgb(50),
            palette_color=current,
            boundary_length_px=20,
            source_pixel_count=40,
        ),
        source_distance=10.0,
        first_alternative=_candidate(
            color=alternative,
            distance=2.0,
            additional_distance=0.5,
        ),
        second_alternative=None,
        minimum_rescue_cost=0.5,
    )

    ranked = rank_quantization_rescue_diagnostics(
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


def test_rank_quantization_rescue_diagnostics_prefers_longer_boundary_on_tie() -> None:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    short = QuantizationRescueDiagnostic(
        collision=CollapsedBoundary(
            first_source=_rgb(10),
            second_source=_rgb(20),
            palette_color=current,
            boundary_length_px=10,
            source_pixel_count=20,
        ),
        source_distance=10.0,
        first_alternative=_candidate(
            color=alternative,
            distance=2.0,
            additional_distance=1.0,
        ),
        second_alternative=None,
        minimum_rescue_cost=1.0,
    )

    long = QuantizationRescueDiagnostic(
        collision=CollapsedBoundary(
            first_source=_rgb(30),
            second_source=_rgb(40),
            palette_color=current,
            boundary_length_px=100,
            source_pixel_count=200,
        ),
        source_distance=10.0,
        first_alternative=_candidate(
            color=alternative,
            distance=2.0,
            additional_distance=1.0,
        ),
        second_alternative=None,
        minimum_rescue_cost=1.0,
    )

    ranked = rank_quantization_rescue_diagnostics(
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


def test_summarize_quantization_rescue_diagnostics_reports_thresholds() -> None:
    current = _palette_color(
        100,
        10,
    )
    alternative = _palette_color(
        101,
        20,
    )

    def diagnostic(
        *,
        source_distance: float,
        rescue_cost: float | None,
    ) -> QuantizationRescueDiagnostic:
        alternative_candidate = (
            _candidate(
                color=alternative,
                distance=2.0,
                additional_distance=rescue_cost,
            )
            if rescue_cost is not None
            else None
        )

        return QuantizationRescueDiagnostic(
            collision=CollapsedBoundary(
                first_source=_rgb(10),
                second_source=_rgb(20),
                palette_color=current,
                boundary_length_px=10,
                source_pixel_count=20,
            ),
            source_distance=source_distance,
            first_alternative=alternative_candidate,
            second_alternative=None,
            minimum_rescue_cost=rescue_cost,
        )

    summary = summarize_quantization_rescue_diagnostics(
        diagnostics=(
            diagnostic(
                source_distance=3.0,
                rescue_cost=0.2,
            ),
            diagnostic(
                source_distance=10.0,
                rescue_cost=0.5,
            ),
            diagnostic(
                source_distance=12.0,
                rescue_cost=1.5,
            ),
            diagnostic(
                source_distance=15.0,
                rescue_cost=4.0,
            ),
            diagnostic(
                source_distance=20.0,
                rescue_cost=8.0,
            ),
            diagnostic(
                source_distance=25.0,
                rescue_cost=None,
            ),
        ),
        source_distance_threshold=5.0,
    )

    assert summary.collision_count == 6
    assert summary.low_source_distance_count == 1
    assert summary.meaningful_collision_count == 5
    assert summary.rescue_cost_le_1_count == 1
    assert summary.rescue_cost_le_2_count == 2
    assert summary.rescue_cost_le_5_count == 3
    assert summary.expensive_rescue_count == 1
    assert summary.unavailable_rescue_count == 1
