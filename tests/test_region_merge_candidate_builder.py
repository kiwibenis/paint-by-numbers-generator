# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from unittest.mock import patch

from pbn.models import (
    RGB,
    Lab,
    PaletteColor,
    Region,
    RegionMergeCandidate,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions import (
    RegionAdjacency,
    RegionMergeCandidateBuilder,
)


class ConstantColorDistance:
    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return 5.0


def _color(
    number: int,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=float(number),
            a=0.0,
            b=0.0,
        ),
    )


def _region(
    region_id: int,
    pixels: set[tuple[int, int]],
) -> Region:
    return Region(
        id=region_id,
        color=_color(region_id),
        pixels=pack_pixels(
            pixels,
        ),
    )


def test_build_only_directed_candidates_between_adjacent_regions() -> None:
    center = _region(
        region_id=1,
        pixels={
            (1, 0),
        },
    )
    right = _region(
        region_id=2,
        pixels={
            (2, 0),
        },
    )
    left = _region(
        region_id=3,
        pixels={
            (0, 0),
        },
    )
    isolated = _region(
        region_id=4,
        pixels={
            (10, 10),
        },
    )

    evaluations = RegionMergeCandidateBuilder(
        color_distance=ConstantColorDistance(),
    ).build(
        (
            right,
            isolated,
            left,
            center,
        ),
    )

    candidates = tuple(candidate for candidate, _ in evaluations)

    assert candidates == (
        RegionMergeCandidate(
            source_id=1,
            target_id=2,
        ),
        RegionMergeCandidate(
            source_id=1,
            target_id=3,
        ),
        RegionMergeCandidate(
            source_id=2,
            target_id=1,
        ),
        RegionMergeCandidate(
            source_id=3,
            target_id=1,
        ),
    )


def test_candidate_order_is_independent_from_region_order() -> None:
    first = _region(
        region_id=1,
        pixels={
            (0, 0),
        },
    )
    second = _region(
        region_id=2,
        pixels={
            (1, 0),
        },
    )
    third = _region(
        region_id=3,
        pixels={
            (2, 0),
        },
    )

    builder = RegionMergeCandidateBuilder(
        color_distance=ConstantColorDistance(),
    )

    first_result = builder.build(
        (
            first,
            second,
            third,
        ),
    )
    second_result = builder.build(
        (
            third,
            first,
            second,
        ),
    )

    assert first_result == second_result


def test_build_calculates_raw_metrics_for_every_candidate() -> None:
    source = _region(
        region_id=1,
        pixels={
            (0, 0),
        },
    )
    target = _region(
        region_id=2,
        pixels={
            (1, 0),
            (2, 0),
        },
    )

    evaluations = RegionMergeCandidateBuilder(
        color_distance=ConstantColorDistance(),
    ).build(
        (
            source,
            target,
        ),
    )

    assert len(evaluations) == 2

    forward_candidate, forward_metrics = evaluations[0]
    reverse_candidate, reverse_metrics = evaluations[1]

    assert forward_candidate == RegionMergeCandidate(
        source_id=1,
        target_id=2,
    )
    assert forward_metrics.source_area == 1
    assert forward_metrics.target_area == 2
    assert forward_metrics.merged_area == 3
    assert forward_metrics.shared_border_length == 1

    assert reverse_candidate == RegionMergeCandidate(
        source_id=2,
        target_id=1,
    )
    assert reverse_metrics.source_area == 2
    assert reverse_metrics.target_area == 1
    assert reverse_metrics.merged_area == 3
    assert reverse_metrics.shared_border_length == 1


def test_build_reuses_single_region_adjacency_result() -> None:
    source = _region(
        region_id=1,
        pixels={
            (0, 0),
        },
    )
    target = _region(
        region_id=2,
        pixels={
            (10, 10),
        },
    )

    shared_borders = {
        source.id: {
            target.id: 1,
        },
        target.id: {
            source.id: 1,
        },
    }

    with patch.object(
        RegionAdjacency,
        "shared_borders",
        autospec=True,
        return_value=shared_borders,
    ) as calculate_shared_borders:
        evaluations = RegionMergeCandidateBuilder(
            color_distance=ConstantColorDistance(),
        ).build(
            (
                source,
                target,
            ),
        )

    assert calculate_shared_borders.call_count == 1

    assert tuple(metrics.shared_border_length for _, metrics in evaluations) == (
        1,
        1,
    )
