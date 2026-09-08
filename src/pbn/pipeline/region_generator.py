# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import Protocol

from pbn.color import ImageQuantizer
from pbn.color.color_distance import ColorDistance
from pbn.exceptions import InvariantViolationError, RegionPaintabilityError
from pbn.models import (
    InputImage,
    Palette,
    QuantizedImage,
    Region,
)
from pbn.regions import (
    RegionDetector,
    RegionMerger,
)
from pbn.regions.paintability_verifier import RegionPaintabilityVerifier


class Quantizer(Protocol):
    """
    Quantizes normalized input images to palette colors.
    """

    def quantize(
        self,
        image: InputImage,
        palette: Palette,
    ) -> QuantizedImage: ...


class OptionalComplexityReducer(Protocol):
    """
    Applies already-configured optional region-complexity reduction.
    """

    def reduce(
        self,
        regions: tuple[Region, ...],
        *,
        minimum_circle_diameter_px: int,
    ) -> tuple[Region, ...]: ...


class RegionGenerator:
    """
    Generates paintable regions from an image.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
        quantizer: Quantizer | None = None,
        complexity_reducer: OptionalComplexityReducer | None = None,
    ) -> None:
        self._quantizer = (
            quantizer
            if quantizer is not None
            else ImageQuantizer(
                color_distance=color_distance,
            )
        )
        self._detector = RegionDetector()
        self._merger = RegionMerger()
        self._paintability_verifier = RegionPaintabilityVerifier()
        self._complexity_reducer = complexity_reducer

    def generate(
        self,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> tuple[Region, ...]:
        quantized_image = self._quantizer.quantize(
            image,
            palette,
        )

        regions = self._detector.detect(
            quantized_image,
        )

        merged_regions = self._merger.merge(
            regions,
            minimum_circle_diameter_px,
        )

        self._verify_mandatory_paintability(
            merged_regions,
            minimum_circle_diameter_px,
        )

        if self._complexity_reducer is None:
            return merged_regions

        reduced_regions = self._complexity_reducer.reduce(
            merged_regions,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
        )

        self._verify_optional_paintability(
            reduced_regions,
            minimum_circle_diameter_px,
        )

        return reduced_regions

    def _verify_mandatory_paintability(
        self,
        regions: tuple[Region, ...],
        minimum_circle_diameter_px: int,
    ) -> None:
        paintability_status = self._paintability_verifier.evaluate(
            regions,
            minimum_circle_diameter_px,
        )

        if paintability_status.mergeable_undersized_region_ids:
            raise InvariantViolationError(
                "Mandatory paintability merging left mergeable "
                "undersized regions: "
                f"{paintability_status.mergeable_undersized_region_ids}"
            )

        if paintability_status.undersized_region_ids:
            raise RegionPaintabilityError(
                "Mandatory paintability merging could not resolve "
                "isolated undersized regions: "
                f"{paintability_status.undersized_region_ids}"
            )

    def _verify_optional_paintability(
        self,
        regions: tuple[Region, ...],
        minimum_circle_diameter_px: int,
    ) -> None:
        paintability_status = self._paintability_verifier.evaluate(
            regions,
            minimum_circle_diameter_px,
        )

        if paintability_status.mergeable_undersized_region_ids:
            raise InvariantViolationError(
                "Optional region complexity reduction left mergeable "
                "undersized regions: "
                f"{paintability_status.mergeable_undersized_region_ids}"
            )

        if paintability_status.undersized_region_ids:
            raise RegionPaintabilityError(
                "Optional region complexity reduction left isolated "
                "undersized regions: "
                f"{paintability_status.undersized_region_ids}"
            )
