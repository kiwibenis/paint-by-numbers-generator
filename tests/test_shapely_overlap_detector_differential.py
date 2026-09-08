# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import random

from pbn.exceptions import InvariantViolationError
from pbn.infrastructure.shapely_overlap_detector import (
    ShapelyOverlapDetector,
)
from pbn.models import RGB, Lab, Outline, PaletteColor, QuantizedImage
from pbn.outline.geometry_validator import (
    OutlineGeometryValidator,
    RegionPair,
)
from pbn.outline.topology_simplifier import OutlineTopologySimplifier
from pbn.outline.tracer import OutlineTracer
from pbn.regions.detector import RegionDetector
from pbn.regions.merger import RegionMerger

_SEED = 20260902
_ITERATIONS = 60


def _color(number: int) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"C{number}",
        rgb=RGB(
            red=number,
            green=number,
            blue=number,
        ),
        lab=Lab(
            l=float(number),
            a=0.0,
            b=0.0,
        ),
    )


def _reference(
    outlines: tuple[Outline, ...],
) -> set[RegionPair]:
    return OutlineGeometryValidator().overlapping_region_pairs(
        outlines,
    )


def _accelerated(
    outlines: tuple[Outline, ...],
) -> set[RegionPair]:
    return OutlineGeometryValidator(
        overlap_detector=ShapelyOverlapDetector(),
    ).overlapping_region_pairs(
        outlines,
    )


def test_accelerated_detection_matches_reference_on_random_inputs() -> None:
    """
    Compare both predicate paths across varied densities and tolerances.
    """
    generator = random.Random(
        _SEED,
    )
    tracer = OutlineTracer()
    comparisons = 0

    for _ in range(_ITERATIONS):
        width = generator.randint(4, 12)
        height = generator.randint(4, 12)
        color_count = generator.randint(2, 5)
        colors = [_color(index) for index in range(color_count)]

        pixels = tuple(
            tuple(colors[generator.randrange(color_count)] for _ in range(width))
            for _ in range(height)
        )

        regions = RegionDetector().detect(
            QuantizedImage.from_rows(pixels),
        )

        regions = RegionMerger().merge(
            regions,
            minimum_circle_diameter_px=generator.randint(1, 4),
        )

        if not regions:
            continue

        raw_outlines = tuple(tracer.trace_raw(region) for region in regions)

        assert _accelerated(raw_outlines) == _reference(raw_outlines)
        comparisons += 1

        for tolerance in (0.0, generator.choice([0.5, 1.0, 2.0, 3.0])):
            try:
                outlines = OutlineTopologySimplifier().simplify(
                    regions,
                    tolerance=tolerance,
                )
            except InvariantViolationError:
                continue

            assert _accelerated(outlines) == _reference(outlines)
            comparisons += 1

    assert comparisons > _ITERATIONS
