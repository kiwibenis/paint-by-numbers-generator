# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import os
from pathlib import Path

from pbn.color import DeltaE76, DeltaE2000
from pbn.config import GeneratorConfig
from pbn.models import (
    ImageSize,
    InputImage,
    Palette,
    VectorDocument,
)
from pbn.pipeline import PaintByNumbersGenerator

from .generator_config_resolver import GeneratorConfigResolver
from .image_loader_port import ImageLoaderPort
from .overlap_detector_port import OverlapDetectorPort
from .parallel_image_quantizer import ParallelImageQuantizer
from .pdf_exporter_port import PdfExporterPort
from .progress_reporter import (
    NullProgressReporter,
    ProgressReporter,
)
from .quantization_executor_port import QuantizationExecutorPort
from .region_complexity_reducer_factory import (
    build_region_complexity_reducer,
)


class GeneratorApplication:
    """
    Application boundary for configured generation.

    Input reaches generation only through the injected image loader, which
    applies the configured limits. Outline overlap validation reaches
    generation only through the injected overlap detector. Both dependencies
    are required so normal Application generation cannot bypass either
    boundary.
    """

    def __init__(
        self,
        progress_reporter: ProgressReporter | None = None,
        quantization_executor: QuantizationExecutorPort | None = None,
        *,
        image_loader: ImageLoaderPort,
        overlap_detector: OverlapDetectorPort,
    ) -> None:
        self._resolver = GeneratorConfigResolver()
        self._image_loader = image_loader
        self._progress_reporter = (
            progress_reporter
            if progress_reporter is not None
            else NullProgressReporter()
        )
        self._quantization_executor = quantization_executor
        self._overlap_detector = overlap_detector

    def generate(
        self,
        image_path: Path,
        palette: Palette,
        config: GeneratorConfig,
    ) -> VectorDocument:
        return self._generate_document(
            self._load(
                image_path,
                config,
            ),
            palette,
            config,
        )

    def _load(
        self,
        image_path: Path,
        config: GeneratorConfig,
    ) -> InputImage:
        """
        Load the input under the configured limits.
        """
        self._progress_reporter.report(
            "Loading input image.",
        )

        return self._image_loader.load(
            image_path,
            config.image_input_limits,
        )

    def _generate_document(
        self,
        image: InputImage,
        palette: Palette,
        config: GeneratorConfig,
    ) -> VectorDocument:
        image_size = ImageSize(
            width=image.width,
            height=image.height,
        )

        minimum_circle_diameter_px = self._resolver.calculate_minimum_circle_diameter(
            config=config,
            image_size=image_size,
        )

        color_distance = self._resolve_color_distance(
            config,
        )

        complexity_reducer = build_region_complexity_reducer(
            config.region_complexity,
            color_distance,
        )

        quantizer = None

        if (
            self._quantization_executor is not None
            and config.parallel_quantization_enabled
            and config.color_distance == "delta_e_2000"
        ):
            worker_count = min(
                os.cpu_count() or 1,
                config.parallel_quantization_max_workers,
            )

            quantizer = ParallelImageQuantizer(
                color_distance=color_distance,
                executor=self._quantization_executor,
                worker_count=worker_count,
                break_even_workload=(config.parallel_quantization_break_even_workload),
            )

        generator = PaintByNumbersGenerator(
            color_distance=color_distance,
            quantizer=quantizer,
            complexity_reducer=complexity_reducer,
            overlap_detector=self._overlap_detector,
            outline_simplification_enabled=(config.outline_simplification_enabled),
            outline_simplification_tolerance_px=(
                config.outline_simplification_tolerance_px
            ),
        )

        self._progress_reporter.report(
            "Generating paint-by-numbers document.",
        )

        return generator.generate(
            image=image,
            palette=palette,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
        )

    def generate_pdf(
        self,
        image_path: Path,
        palette: Palette,
        config: GeneratorConfig,
        pdf_exporter: PdfExporterPort,
    ) -> bytes:
        image = self._load(
            image_path,
            config,
        )

        image_size = ImageSize(
            width=image.width,
            height=image.height,
        )

        geometry = self._resolver.resolve_physical_output_geometry(
            config=config,
        )

        legend_geometry = self._resolver.resolve_palette_legend_geometry(
            config=config,
        )

        placement = self._resolver.calculate_image_placement_geometry(
            config=config,
            image_size=image_size,
        )

        document = self._generate_document(
            image,
            palette,
            config,
        )

        self._progress_reporter.report(
            "Exporting PDF document.",
        )

        return pdf_exporter.write(
            document=document,
            geometry=geometry,
            legend_geometry=legend_geometry,
            placement=placement,
            palette=palette,
            legend_config=config.pdf_legend,
            margin_mm=config.margin_mm,
            font_size_pt=config.font_size_pt,
            line_width_pt=config.line_width_pt,
            line_color=config.line_color,
            number_color=config.number_color,
        )

    @staticmethod
    def _resolve_color_distance(
        config: GeneratorConfig,
    ) -> DeltaE76 | DeltaE2000:
        if config.color_distance == "delta_e_76":
            return DeltaE76()

        if config.color_distance == "delta_e_2000":
            return DeltaE2000()

        raise ValueError(
            "Unsupported color distance: " f"{config.color_distance}",
        )
