# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterator

import pytest

import tools.benchmark_region_complexity_geometry_validation as performance
from pbn.models import RGB, Lab, Outline, PaletteColor, Region
from tools.benchmark_region_complexity_geometry_validation import (
    GeometryValidationCall,
    InstrumentedOutlineGeometryValidator,
    OutlineGeometryValidationBenchmark,
    benchmark_outline_geometry_validation,
    format_validation_call,
    format_validation_summary,
)


def _region(
    region_id: int,
) -> Region:
    """
    A minimal region for a benchmark that only counts them.

    The simplifier is faked here and never reads a field, but the
    benchmark's signature says Region. A stand-in that is not one would
    drift away from the real type unnoticed, which is how the collision
    evaluator ended up passing coordinate pairs to a function expecting
    packed indices.
    """
    return Region(
        id=region_id,
        color=PaletteColor(
            number=region_id,
            name=f"Color {region_id}",
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
        pixels=frozenset(
            {
                region_id,
            },
        ),
    )


class SequenceClock:
    """
    Deterministic clock for benchmark unit tests.
    """

    def __init__(
        self,
        *values: float,
    ) -> None:
        self._values: Iterator[float] = iter(
            values,
        )

    def __call__(
        self,
    ) -> float:
        return next(
            self._values,
        )


def _outline(
    region_id: int,
    *,
    offset_x: int,
    offset_y: int,
    size: int = 2,
) -> Outline:
    return Outline(
        region_id=region_id,
        points=(
            (
                offset_x,
                offset_y,
            ),
            (
                offset_x + size,
                offset_y,
            ),
            (
                offset_x + size,
                offset_y + size,
            ),
            (
                offset_x,
                offset_y + size,
            ),
        ),
    )


def test_instrumented_validator_measures_both_validation_paths() -> None:
    validator = InstrumentedOutlineGeometryValidator(
        clock=SequenceClock(
            0.0,
            1.0,
            10.0,
            13.0,
        ),
    )

    result = validator.invalid_region_ids(
        (
            _outline(
                1,
                offset_x=0,
                offset_y=0,
            ),
            _outline(
                2,
                offset_x=10,
                offset_y=10,
            ),
        ),
    )

    assert result == set()

    assert validator.calls == (
        GeometryValidationCall(
            outline_count=2,
            region_filter_count=None,
            invalid_outline_region_count=0,
            overlapping_region_pair_count=0,
            invalid_outline_seconds=1.0,
            overlapping_region_pairs_seconds=3.0,
        ),
    )


def test_instrumented_validator_preserves_overlap_result() -> None:
    validator = InstrumentedOutlineGeometryValidator(
        clock=SequenceClock(
            0.0,
            0.5,
            1.0,
            2.5,
        ),
    )

    result = validator.invalid_region_ids(
        (
            _outline(
                1,
                offset_x=0,
                offset_y=0,
                size=4,
            ),
            _outline(
                2,
                offset_x=2,
                offset_y=2,
                size=4,
            ),
        ),
    )

    assert result == {
        1,
        2,
    }

    call = validator.calls[0]

    assert call.overlapping_region_pair_count == 1
    assert call.invalid_outline_region_count == 0
    assert call.invalid_outline_seconds == pytest.approx(
        0.5,
    )
    assert call.overlapping_region_pairs_seconds == pytest.approx(
        1.5,
    )


def test_instrumented_validator_records_region_filter_size() -> None:
    validator = InstrumentedOutlineGeometryValidator(
        clock=SequenceClock(
            0.0,
            0.1,
            1.0,
            1.2,
        ),
    )

    validator.invalid_region_ids(
        (
            _outline(
                1,
                offset_x=0,
                offset_y=0,
            ),
            _outline(
                2,
                offset_x=10,
                offset_y=10,
            ),
        ),
        region_ids={
            2,
        },
    )

    assert validator.calls[0].region_filter_count == 1


def test_benchmark_outline_geometry_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outlines = (
        _outline(
            1,
            offset_x=0,
            offset_y=0,
        ),
        _outline(
            2,
            offset_x=10,
            offset_y=10,
        ),
    )

    class FakeOutlineTopologySimplifier:
        def __init__(
            self,
        ) -> None:
            self._geometry_validator: InstrumentedOutlineGeometryValidator | None = None

        def simplify(
            self,
            regions: tuple[
                Region,
                ...,
            ],
            *,
            tolerance: float,
        ) -> tuple[
            Outline,
            ...,
        ]:
            assert len(regions) == 2
            assert tolerance == pytest.approx(
                1.5,
            )
            assert self._geometry_validator is not None

            self._geometry_validator.invalid_region_ids(
                outlines,
            )

            return outlines

    monkeypatch.setattr(
        performance,
        "OutlineTopologySimplifier",
        FakeOutlineTopologySimplifier,
    )

    benchmark = benchmark_outline_geometry_validation(
        reduced_regions=(
            _region(1),
            _region(2),
        ),
        tolerance=1.5,
        clock=SequenceClock(
            0.0,
            1.0,
            2.0,
            3.0,
            7.0,
            10.0,
        ),
    )

    assert benchmark.reduced_region_count == 2
    assert benchmark.resulting_outline_count == 2
    assert benchmark.complete_simplification_seconds == pytest.approx(
        10.0,
    )

    assert benchmark.validation_call_count == 1

    assert benchmark.invalid_outline_seconds == pytest.approx(
        1.0,
    )
    assert benchmark.overlapping_region_pairs_seconds == pytest.approx(
        4.0,
    )
    assert benchmark.geometry_validation_seconds == pytest.approx(
        5.0,
    )
    assert benchmark.non_validation_seconds == pytest.approx(
        5.0,
    )
    assert benchmark.overlap_fraction_of_validation == pytest.approx(
        0.8,
    )
    assert benchmark.overlap_fraction_of_complete_simplification == pytest.approx(
        0.4,
    )


def test_benchmark_outline_geometry_validation_rejects_empty_regions() -> None:
    with pytest.raises(
        ValueError,
        match="reduced_regions must not be empty",
    ):
        benchmark_outline_geometry_validation(
            reduced_regions=(),
            tolerance=1.0,
            clock=SequenceClock(),
        )


def test_format_validation_summary() -> None:
    benchmark = OutlineGeometryValidationBenchmark(
        reduced_region_count=100,
        resulting_outline_count=100,
        complete_simplification_seconds=20.0,
        validation_calls=(
            GeometryValidationCall(
                outline_count=100,
                region_filter_count=None,
                invalid_outline_region_count=0,
                overlapping_region_pair_count=0,
                invalid_outline_seconds=2.0,
                overlapping_region_pairs_seconds=12.0,
            ),
        ),
    )

    assert format_validation_summary(
        benchmark,
    ) == (
        "geometry_validation_summary: "
        "reduced_regions=100, "
        "resulting_outlines=100, "
        "validation_calls=1, "
        "complete_simplification=20.000000s, "
        "invalid_outline_validation=2.000000s, "
        "overlapping_region_pairs=12.000000s, "
        "geometry_validation_total=14.000000s, "
        "non_validation=6.000000s, "
        "overlap_of_validation=85.71%, "
        "overlap_of_complete=60.00%"
    )


def test_format_validation_call_with_full_region_set() -> None:
    call = GeometryValidationCall(
        outline_count=100,
        region_filter_count=None,
        invalid_outline_region_count=2,
        overlapping_region_pair_count=3,
        invalid_outline_seconds=1.0,
        overlapping_region_pairs_seconds=4.0,
    )

    assert format_validation_call(
        call,
        call_number=2,
    ) == (
        "geometry_validation_call=2: "
        "outlines=100, "
        "region_filter=all, "
        "invalid_outline_regions=2, "
        "overlap_pairs=3, "
        "invalid_outline_validation=1.000000s, "
        "overlapping_region_pairs=4.000000s, "
        "total=5.000000s"
    )


def test_format_validation_call_with_filtered_regions() -> None:
    call = GeometryValidationCall(
        outline_count=100,
        region_filter_count=7,
        invalid_outline_region_count=0,
        overlapping_region_pair_count=0,
        invalid_outline_seconds=0.25,
        overlapping_region_pairs_seconds=0.75,
    )

    assert format_validation_call(
        call,
        call_number=3,
    ) == (
        "geometry_validation_call=3: "
        "outlines=100, "
        "region_filter=7, "
        "invalid_outline_regions=0, "
        "overlap_pairs=0, "
        "invalid_outline_validation=0.250000s, "
        "overlapping_region_pairs=0.750000s, "
        "total=1.000000s"
    )


def test_parser_defaults_to_reduced_complex_diagnostic() -> None:
    args = performance.build_parser().parse_args(
        [],
    )

    assert args.minimum_region_size_mm is None
    assert args.target_fraction == pytest.approx(
        0.5,
    )


def test_the_paintability_minimum_is_left_to_the_profile() -> None:
    """
    The default was `1.0` while the shipped profile said `2.0`, and it was
    applied to the loaded profile unconditionally, so a run without
    arguments measured half the shipped paintability. This document names
    the tool as the source of its numbers and documents it without
    arguments.

    `None` is the whole rule: the profile answers, unless the caller says
    otherwise in a command that then records what was measured.
    """
    assert (
        performance.build_parser()
        .parse_args(
            [],
        )
        .minimum_region_size_mm
        is None
    )

    assert performance.build_parser().parse_args(
        [
            "--minimum-region-size-mm",
            "1.0",
        ],
    ).minimum_region_size_mm == pytest.approx(
        1.0,
    )
