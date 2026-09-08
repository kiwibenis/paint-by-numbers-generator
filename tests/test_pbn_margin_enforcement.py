# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.application import GeneratorConfigResolver
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.models import ImageSize

POINTS_PER_INCH = 72.0
MILLIMETERS_PER_INCH = 25.4


def create_region_complexity_config() -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=False,
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


def create_config(
    *,
    placement: str,
    margin_mm: float = 10.0,
    line_width_pt: float = 0.4,
) -> GeneratorConfig:
    return GeneratorConfig(
        page="A4",
        orientation="landscape",
        placement=placement,
        margin_mm=margin_mm,
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
        color_distance="delta_e_76",
        parallel_quantization_enabled=True,
        parallel_quantization_break_even_workload=360_448,
        parallel_quantization_max_workers=8,
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.0,
        font_size_pt=9,
        line_width_pt=line_width_pt,
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


def half_line_width_mm(
    line_width_pt: float,
) -> float:
    return line_width_pt * MILLIMETERS_PER_INCH / POINTS_PER_INCH / 2.0


def test_fit_keeps_outline_stroke_outside_printer_margin() -> None:
    config = create_config(
        placement="fit",
    )

    placement = GeneratorConfigResolver().calculate_image_placement_geometry(
        config=config,
        image_size=ImageSize(
            width=4032,
            height=3024,
        ),
    )

    stroke_radius_mm = half_line_width_mm(
        config.line_width_pt,
    )

    assert (placement.output_offset_y_mm - stroke_radius_mm) == pytest.approx(
        config.margin_mm,
    )


def test_crop_keeps_outline_stroke_outside_printer_margin() -> None:
    config = create_config(
        placement="crop",
    )

    placement = GeneratorConfigResolver().calculate_image_placement_geometry(
        config=config,
        image_size=ImageSize(
            width=4032,
            height=3024,
        ),
    )

    stroke_radius_mm = half_line_width_mm(
        config.line_width_pt,
    )

    assert (placement.output_offset_x_mm - stroke_radius_mm) == pytest.approx(
        config.margin_mm,
    )

    assert (placement.output_offset_y_mm - stroke_radius_mm) == pytest.approx(
        config.margin_mm,
    )
