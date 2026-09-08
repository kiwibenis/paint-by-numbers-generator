# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from collections.abc import Set as AbstractSet
from dataclasses import FrozenInstanceError

import pytest

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeCandidate,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_metrics_calculator import RegionMergeMetricsCalculator


class RecordingColorDistance:
    def __init__(
        self,
        result: float,
    ) -> None:
        self.result = result
        self.calls: list[
            tuple[
                Lab,
                Lab,
            ]
        ] = []

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        self.calls.append(
            (
                first,
                second,
            ),
        )
        return self.result


def _color(
    number: int,
    lab: Lab,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=lab,
    )


def _regions() -> tuple[
    Region,
    Region,
]:
    source = Region(
        id=1,
        color=_color(
            number=1,
            lab=Lab(
                l=20.0,
                a=3.0,
                b=4.0,
            ),
        ),
        pixels=pack_pixels(
            {
                (0, 0),
                (0, 1),
            },
        ),
    )

    target = Region(
        id=2,
        color=_color(
            number=2,
            lab=Lab(
                l=80.0,
                a=-2.0,
                b=1.0,
            ),
        ),
        pixels=pack_pixels(
            {
                (1, 0),
                (1, 1),
                (2, 0),
                (2, 1),
            },
        ),
    )

    return (
        source,
        target,
    )


def test_region_merge_candidate_is_directed_and_immutable() -> None:
    candidate = RegionMergeCandidate(
        source_id=1,
        target_id=2,
    )

    assert candidate.source_id == 1
    assert candidate.target_id == 2
    assert candidate != RegionMergeCandidate(
        source_id=2,
        target_id=1,
    )

    with pytest.raises(FrozenInstanceError):
        # The assignment is the assertion: the model is frozen, so
        # mypy is right that this is a static error and the test
        # exists to prove it is a runtime one too.
        candidate.source_id = 3  # type: ignore[misc]


def test_calculate_directed_region_merge_metrics() -> None:
    source, target = _regions()
    color_distance = RecordingColorDistance(
        result=42.5,
    )

    calculator = RegionMergeMetricsCalculator(
        color_distance=color_distance,
    )

    metrics = calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=source.id,
            target_id=target.id,
        ),
        regions={
            source.id: source,
            target.id: target,
        },
        shared_borders={
            source.id: {
                target.id: 2,
            },
            target.id: {
                source.id: 2,
            },
        },
    )

    assert metrics.color_difference == 42.5
    assert color_distance.calls == [
        (
            source.color.lab,
            target.color.lab,
        ),
    ]

    assert metrics.source_area == 2
    assert metrics.target_area == 4
    assert metrics.merged_area == 6
    assert metrics.affected_area_ratio == pytest.approx(
        2 / 6,
    )

    assert metrics.shared_border_length == 2

    assert metrics.source_perimeter == 6
    assert metrics.target_perimeter == 8
    assert metrics.merged_perimeter == 10

    assert metrics.source_shared_border_ratio == pytest.approx(
        2 / 6,
    )
    assert metrics.target_shared_border_ratio == pytest.approx(
        2 / 8,
    )


def test_reverse_candidate_preserves_directional_metrics() -> None:
    source, target = _regions()
    calculator = RegionMergeMetricsCalculator(
        color_distance=RecordingColorDistance(
            result=10.0,
        ),
    )

    regions = {
        source.id: source,
        target.id: target,
    }
    shared_borders = {
        source.id: {
            target.id: 2,
        },
        target.id: {
            source.id: 2,
        },
    }

    forward = calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=source.id,
            target_id=target.id,
        ),
        regions=regions,
        shared_borders=shared_borders,
    )
    reverse = calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=target.id,
            target_id=source.id,
        ),
        regions=regions,
        shared_borders=shared_borders,
    )

    assert forward.source_area == reverse.target_area
    assert forward.target_area == reverse.source_area
    assert forward.source_perimeter == reverse.target_perimeter
    assert forward.target_perimeter == reverse.source_perimeter

    assert forward.merged_area == reverse.merged_area
    assert forward.merged_perimeter == reverse.merged_perimeter
    assert forward.shared_border_length == reverse.shared_border_length

    assert forward.affected_area_ratio == pytest.approx(
        2 / 6,
    )
    assert reverse.affected_area_ratio == pytest.approx(
        4 / 6,
    )


def test_calculator_uses_supplied_shared_border_information() -> None:
    source, target = _regions()
    calculator = RegionMergeMetricsCalculator(
        color_distance=RecordingColorDistance(
            result=1.0,
        ),
    )

    metrics = calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=source.id,
            target_id=target.id,
        ),
        regions={
            source.id: source,
            target.id: target,
        },
        shared_borders={
            source.id: {
                target.id: 1,
            },
            target.id: {
                source.id: 1,
            },
        },
    )

    assert metrics.shared_border_length == 1
    assert metrics.source_shared_border_ratio == pytest.approx(
        1 / 6,
    )
    assert metrics.target_shared_border_ratio == pytest.approx(
        1 / 8,
    )


def test_reuses_region_perimeters_across_directed_candidates() -> None:
    class CountingMetricsCalculator(RegionMergeMetricsCalculator):
        def __init__(self) -> None:
            super().__init__(
                color_distance=RecordingColorDistance(
                    result=1.0,
                ),
            )
            self.perimeter_calculations = 0

        def _perimeter(
            self,
            pixels: AbstractSet[int],
        ) -> int:
            self.perimeter_calculations += 1
            return super()._perimeter(
                pixels,
            )

    source, target = _regions()
    calculator = CountingMetricsCalculator()

    regions = {
        source.id: source,
        target.id: target,
    }
    shared_borders = {
        source.id: {
            target.id: 2,
        },
        target.id: {
            source.id: 2,
        },
    }

    calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=source.id,
            target_id=target.id,
        ),
        regions=regions,
        shared_borders=shared_borders,
    )
    calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=target.id,
            target_id=source.id,
        ),
        regions=regions,
        shared_borders=shared_borders,
    )

    assert calculator.perimeter_calculations == 2


def test_recalculates_perimeter_when_region_object_changes() -> None:
    source, target = _regions()

    calculator = RegionMergeMetricsCalculator(
        color_distance=RecordingColorDistance(
            result=1.0,
        ),
    )

    shared_borders = {
        source.id: {
            target.id: 2,
        },
        target.id: {
            source.id: 2,
        },
    }

    first = calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=source.id,
            target_id=target.id,
        ),
        regions={
            source.id: source,
            target.id: target,
        },
        shared_borders=shared_borders,
    )

    changed_source = Region(
        id=source.id,
        color=source.color,
        pixels=pack_pixels(
            {
                (0, 0),
                (0, 1),
                (0, 2),
            },
        ),
    )

    changed_shared_borders = {
        changed_source.id: {
            target.id: 1,
        },
        target.id: {
            changed_source.id: 1,
        },
    }

    second = calculator.calculate(
        candidate=RegionMergeCandidate(
            source_id=changed_source.id,
            target_id=target.id,
        ),
        regions={
            changed_source.id: changed_source,
            target.id: target,
        },
        shared_borders=changed_shared_borders,
    )

    assert first.source_perimeter == 6
    assert second.source_perimeter == 8


def test_overlapping_regions_use_exact_union_geometry() -> None:
    color = _color(
        number=1,
        lab=Lab(
            l=50.0,
            a=0.0,
            b=0.0,
        ),
    )

    source = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )
    target = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
            },
        ),
    )

    metrics = RegionMergeMetricsCalculator(
        color_distance=RecordingColorDistance(
            result=0.0,
        ),
    ).calculate(
        candidate=RegionMergeCandidate(
            source_id=source.id,
            target_id=target.id,
        ),
        regions={
            source.id: source,
            target.id: target,
        },
        shared_borders={
            source.id: {
                target.id: 2,
            },
            target.id: {
                source.id: 2,
            },
        },
    )

    assert metrics.source_area == 2
    assert metrics.target_area == 2
    assert metrics.merged_area == 2
    assert metrics.merged_perimeter == 6
