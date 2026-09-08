# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.application import GeneratorConfigResolver
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.models import (
    A3,
    A4,
    ImagePlacement,
    ImageSize,
    Orientation,
    PhysicalOutputGeometry,
)

POINTS_PER_INCH = 72.0
MILLIMETERS_PER_INCH = 25.4


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


def create_pdf_legend_config(
    *,
    page: str = "A4",
    orientation: str = "landscape",
) -> PdfLegendConfig:
    return PdfLegendConfig(
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
        page=page,
        orientation=orientation,
        margin_mm=5.0,
    )


def create_generator_config(
    *,
    page: str = "A4",
    orientation: str = "landscape",
    placement: str = "fit",
    margin_mm: float = 10.0,
    legend_page: str = "A4",
    legend_orientation: str = "landscape",
) -> GeneratorConfig:
    return GeneratorConfig(
        page=page,
        orientation=orientation,
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
        line_width_pt=0.4,
        line_color="#000000",
        number_color="#000000",
        pdf_legend=create_pdf_legend_config(
            page=legend_page,
            orientation=legend_orientation,
        ),
    )


def half_line_width_mm(
    line_width_pt: float,
) -> float:
    return line_width_pt * MILLIMETERS_PER_INCH / POINTS_PER_INCH / 2.0


def test_calculate_minimum_circle_diameter() -> None:
    config = create_generator_config()

    resolver = GeneratorConfigResolver()

    result = resolver.calculate_minimum_circle_diameter(
        config=config,
        image_size=ImageSize(
            width=4032,
            height=3024,
        ),
    )

    assert result == 48


def test_calculate_image_placement_geometry_uses_configured_margin() -> None:
    config = create_generator_config(
        margin_mm=10.0,
    )

    resolver = GeneratorConfigResolver()

    result = resolver.calculate_image_placement_geometry(
        config=config,
        image_size=ImageSize(
            width=4032,
            height=3024,
        ),
    )

    effective_margin_mm = config.margin_mm + half_line_width_mm(
        config.line_width_pt,
    )

    printable_width_mm = 297.0 - 2.0 * effective_margin_mm
    printable_height_mm = 210.0 - 2.0 * effective_margin_mm

    expected_scale = printable_height_mm / 3024.0
    expected_image_width_mm = 4032 * expected_scale

    assert result.scale == pytest.approx(
        expected_scale,
    )
    assert result.image_width_mm == pytest.approx(
        expected_image_width_mm,
    )
    assert result.image_height_mm == pytest.approx(
        printable_height_mm,
    )
    assert result.crop_left_px == 0
    assert result.crop_top_px == 0
    assert result.crop_width_px == 4032
    assert result.crop_height_px == 3024
    assert result.output_offset_x_mm == pytest.approx(
        effective_margin_mm + (printable_width_mm - expected_image_width_mm) / 2.0,
    )
    assert result.output_offset_y_mm == pytest.approx(
        effective_margin_mm,
    )


def test_rejects_unsupported_page_size() -> None:
    config = create_generator_config(
        page="A5",
        orientation="portrait",
    )

    resolver = GeneratorConfigResolver()

    with pytest.raises(ValueError, match="Unsupported page size"):
        resolver.resolve_physical_output_geometry(config)


def test_rejects_unsupported_image_placement() -> None:
    config = create_generator_config(
        orientation="portrait",
        placement="stretch",
    )

    resolver = GeneratorConfigResolver()

    with pytest.raises(ValueError, match="Unsupported image placement"):
        resolver.resolve_image_placement(config)


def test_resolve_physical_output_geometry() -> None:
    config = create_generator_config()

    resolver = GeneratorConfigResolver()

    result = resolver.resolve_physical_output_geometry(config)

    assert result == PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.LANDSCAPE,
    )


def test_resolve_image_placement() -> None:
    config = create_generator_config(
        orientation="portrait",
        placement="crop",
    )

    resolver = GeneratorConfigResolver()

    result = resolver.resolve_image_placement(config)

    assert result is ImagePlacement.CROP


def test_resolve_palette_legend_geometry_independently() -> None:
    config = create_generator_config(
        page="A4",
        orientation="landscape",
        legend_page="A3",
        legend_orientation="portrait",
    )

    resolver = GeneratorConfigResolver()

    result = resolver.resolve_palette_legend_geometry(config)

    assert result == PhysicalOutputGeometry(
        page_size=A3,
        orientation=Orientation.PORTRAIT,
    )
