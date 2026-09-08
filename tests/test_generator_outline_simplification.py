# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.color import DeltaE2000
from pbn.label import LabelPlacer
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Outline,
    Palette,
    PaletteColor,
    Region,
    VectorDocument,
)
from pbn.models.pixel_index import pack_pixels
from pbn.outline import OutlineTracer
from pbn.outline.topology_simplifier import OutlineTopologySimplifier
from pbn.pipeline import PaintByNumbersGenerator, RegionGenerator


def _outline_segments(
    outline: Outline,
) -> set[frozenset[tuple[int, int]]]:
    points = outline.points

    return {
        frozenset(
            (
                points[index],
                points[(index + 1) % len(points)],
            )
        )
        for index in range(len(points))
    }


def create_image() -> InputImage:
    return InputImage.from_rows(
        (
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
            ),
        )
    )


def create_palette() -> Palette:
    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(),
    )


def test_generator_applies_outline_simplification_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    traced_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 1),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    simplified_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    captured: dict[str, object] = {}

    def fake_generate_regions(
        self: RegionGenerator,
        image: object,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> tuple[object, ...]:
        return (object(),)

    def fake_trace(
        self: OutlineTracer,
        region: object,
    ) -> Outline:
        return traced_outline

    def fake_simplify(
        self: OutlineTopologySimplifier,
        regions: tuple[object, ...],
        *,
        tolerance: float,
    ) -> tuple[Outline, ...]:
        captured["regions"] = regions
        captured["tolerance"] = tolerance

        return (simplified_outline,)

    def fake_place(
        self: LabelPlacer,
        regions: tuple[object, ...],
    ) -> tuple[()]:
        return ()

    monkeypatch.setattr(
        RegionGenerator,
        "generate",
        fake_generate_regions,
    )
    monkeypatch.setattr(
        OutlineTracer,
        "trace",
        fake_trace,
    )
    monkeypatch.setattr(
        OutlineTopologySimplifier,
        "simplify",
        fake_simplify,
    )
    monkeypatch.setattr(
        LabelPlacer,
        "place",
        fake_place,
    )

    generator = PaintByNumbersGenerator(
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.5,
        color_distance=DeltaE2000(),
    )

    document = generator.generate(
        image=create_image(),
        palette=create_palette(),
        minimum_circle_diameter_px=2,
    )

    assert isinstance(
        document,
        VectorDocument,
    )
    assert document.outlines == (simplified_outline,)
    assert captured["tolerance"] == 1.5


def test_generator_preserves_traced_outline_when_simplification_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    traced_outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (2, 1),
            (4, 0),
            (4, 4),
            (0, 4),
        ),
    )

    def fake_generate_regions(
        self: RegionGenerator,
        image: object,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> tuple[object, ...]:
        return (object(),)

    def fake_trace(
        self: OutlineTracer,
        region: object,
    ) -> Outline:
        return traced_outline

    def fail_simplify(
        self: OutlineTopologySimplifier,
        regions: tuple[object, ...],
        *,
        tolerance: float,
    ) -> tuple[Outline, ...]:
        raise AssertionError(
            "Topology simplifier must not run when disabled.",
        )

    def fake_place(
        self: LabelPlacer,
        regions: tuple[object, ...],
    ) -> tuple[()]:
        return ()

    monkeypatch.setattr(
        RegionGenerator,
        "generate",
        fake_generate_regions,
    )
    monkeypatch.setattr(
        OutlineTracer,
        "trace",
        fake_trace,
    )
    monkeypatch.setattr(
        OutlineTopologySimplifier,
        "simplify",
        fail_simplify,
    )
    monkeypatch.setattr(
        LabelPlacer,
        "place",
        fake_place,
    )

    generator = PaintByNumbersGenerator(
        outline_simplification_enabled=False,
        outline_simplification_tolerance_px=1.5,
        color_distance=DeltaE2000(),
    )

    document = generator.generate(
        image=create_image(),
        palette=create_palette(),
        minimum_circle_diameter_px=2,
    )

    assert document.outlines == (traced_outline,)


def test_generator_preserves_shared_boundary_when_simplifying_adjacent_regions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    color = PaletteColor(
        number=1,
        name="Test",
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
    )

    left = Region(
        id=1,
        color=color,
        pixels=pack_pixels(
            {
                (0, 0),
                (1, 0),
                (0, 1),
                (1, 1),
                (2, 1),
                (0, 2),
                (1, 2),
                (0, 3),
                (1, 3),
                (2, 3),
                (0, 4),
                (1, 4),
            },
        ),
    )

    right = Region(
        id=2,
        color=color,
        pixels=pack_pixels(
            {
                (2, 0),
                (3, 0),
                (4, 0),
                (5, 0),
                (3, 1),
                (4, 1),
                (5, 1),
                (2, 2),
                (3, 2),
                (4, 2),
                (5, 2),
                (3, 3),
                (4, 3),
                (5, 3),
                (2, 4),
                (3, 4),
                (4, 4),
                (5, 4),
            },
        ),
    )

    def fake_generate_regions(
        self: RegionGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> tuple[Region, ...]:
        return (
            left,
            right,
        )

    def fake_place(
        self: LabelPlacer,
        regions: tuple[Region, ...],
    ) -> tuple[()]:
        return ()

    monkeypatch.setattr(
        RegionGenerator,
        "generate",
        fake_generate_regions,
    )
    monkeypatch.setattr(
        LabelPlacer,
        "place",
        fake_place,
    )

    generator = PaintByNumbersGenerator(
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.1,
        color_distance=DeltaE2000(),
    )

    document = generator.generate(
        image=create_image(),
        palette=create_palette(),
        minimum_circle_diameter_px=2,
    )

    outlines = {outline.region_id: outline for outline in document.outlines}

    expected_shared_segment = frozenset(
        (
            (2, 0),
            (2, 5),
        )
    )

    assert expected_shared_segment in _outline_segments(
        outlines[1],
    )
    assert expected_shared_segment in _outline_segments(
        outlines[2],
    )
