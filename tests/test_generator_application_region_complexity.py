# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.application import generator_application
from pbn.application.generator_application import GeneratorApplication
from pbn.color.color_distance import ColorDistance
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.models import (
    RGB,
    InputImage,
    Palette,
    VectorDocument,
)
from tests.fake_image_loader import FakeImageLoader
from tests.fake_overlap_detector import FakeOverlapDetector


def create_region_complexity_config() -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=350,
        maximum_merge_cost=0.300,
        merge_cost=RegionMergeCostConfig(
            color_weight=0.40,
            affected_area_weight=0.25,
            border_weight=0.15,
            geometry_weight=0.20,
            enclosure_strength=0.50,
            compactness_strength=0.15,
        ),
    )


def create_config() -> GeneratorConfig:
    return GeneratorConfig(
        page="A4",
        orientation="landscape",
        placement="fit",
        margin_mm=10.0,
        palette="reference8",
        palette_version=1,
        input_image="input.png",
        output_pdf="output.pdf",
        region_complexity=create_region_complexity_config(),
        image_input_limits=ImageInputLimitsConfig(
            maximum_pixel_count=50_000_000,
            maximum_width=20_000,
            maximum_height=20_000,
            processing_pixel_count=1_600_000,
        ),
        minimum_region_size_mm=3.0,
        color_distance="delta_e_2000",
        parallel_quantization_enabled=False,
        parallel_quantization_break_even_workload=360_448,
        parallel_quantization_max_workers=8,
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.0,
        font_size_pt=9,
        line_width_pt=0.4,
        line_color="#000000",
        number_color="#000000",
        pdf_legend=PdfLegendConfig(
            pixels_per_inch=96.0,
            points_per_inch=72.0,
            color_field_px=30.0,
            column_count=4,
            rows_per_page=17,
            start_x_mm=20.0,
            header_y_mm=285.0,
            version_y_mm=278.0,
            table_y_mm=265.0,
            column_width_pt=118.0,
            name_offset_pt=30.0,
            row_height_pt=42.5,
            entry_font_name="Helvetica",
            entry_number_font_name="Helvetica-Bold",
            entry_font_size_pt=9,
            entry_line_height_pt=9.0,
            page="A4",
            orientation="portrait",
            margin_mm=5.0,
        ),
    )


def test_generate_injects_configured_region_complexity_reducer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = create_config()
    image = InputImage.from_rows(
        (
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
            ),
        ),
    )
    palette = Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(),
    )
    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    configured_reducer = object()
    captured: dict[str, object] = {}

    def fake_build_region_complexity_reducer(
        region_complexity: RegionComplexityConfig,
        color_distance: ColorDistance,
    ) -> object:
        captured["region_complexity"] = region_complexity
        captured["factory_color_distance"] = color_distance
        return configured_reducer

    class FakePaintByNumbersGenerator:
        def __init__(
            self,
            color_distance: ColorDistance,
            quantizer: object | None = None,
            complexity_reducer: object | None = None,
            overlap_detector: object | None = None,
            *,
            outline_simplification_enabled: bool,
            outline_simplification_tolerance_px: float,
        ) -> None:
            captured["generator_color_distance"] = color_distance
            captured["complexity_reducer"] = complexity_reducer

        def generate(
            self,
            image: InputImage,
            palette: Palette,
            minimum_circle_diameter_px: int,
        ) -> VectorDocument:
            return expected_document

    monkeypatch.setattr(
        generator_application,
        "build_region_complexity_reducer",
        fake_build_region_complexity_reducer,
    )
    monkeypatch.setattr(
        generator_application,
        "PaintByNumbersGenerator",
        FakePaintByNumbersGenerator,
    )

    result = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    ).generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["region_complexity"] is config.region_complexity
    assert captured["complexity_reducer"] is configured_reducer
    assert captured["factory_color_distance"] is captured["generator_color_distance"]
