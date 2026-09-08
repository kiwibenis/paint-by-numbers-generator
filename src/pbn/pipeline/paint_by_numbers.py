# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.color.color_distance import ColorDistance
from pbn.label import LabelPlacer
from pbn.models import (
    InputImage,
    Palette,
    VectorDocument,
)
from pbn.outline import OutlineTracer
from pbn.outline.geometry_validator import OverlapDetector
from pbn.outline.topology_simplifier import OutlineTopologySimplifier
from pbn.pipeline.region_generator import (
    OptionalComplexityReducer,
    Quantizer,
    RegionGenerator,
)


class PaintByNumbersGenerator:
    """
    Generates a paint-by-numbers vector document from an image.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
        quantizer: Quantizer | None = None,
        complexity_reducer: OptionalComplexityReducer | None = None,
        overlap_detector: OverlapDetector | None = None,
        *,
        outline_simplification_enabled: bool,
        outline_simplification_tolerance_px: float,
    ) -> None:
        self._region_generator = RegionGenerator(
            color_distance=color_distance,
            quantizer=quantizer,
            complexity_reducer=complexity_reducer,
        )
        self._tracer = OutlineTracer()
        self._topology_simplifier = OutlineTopologySimplifier(
            overlap_detector=overlap_detector,
        )
        self._placer = LabelPlacer()

        self._outline_simplification_enabled = outline_simplification_enabled
        self._outline_simplification_tolerance_px = outline_simplification_tolerance_px

    def generate(
        self,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        regions = self._region_generator.generate(
            image=image,
            palette=palette,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
        )

        if self._outline_simplification_enabled:
            outlines = self._topology_simplifier.simplify(
                regions,
                tolerance=self._outline_simplification_tolerance_px,
            )
        else:
            outlines = tuple(
                self._tracer.trace(
                    region,
                )
                for region in regions
            )

        labels = self._placer.place(
            regions,
        )

        return VectorDocument(
            outlines=outlines,
            labels=labels,
            palette_id=palette.id,
            palette_version=palette.version,
        )
