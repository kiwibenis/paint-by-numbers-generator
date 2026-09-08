# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdfLegendConfig:
    """
    Immutable PDF palette legend configuration.
    """

    pixels_per_inch: float
    points_per_inch: float
    color_field_px: float

    column_count: int
    rows_per_page: int

    start_x_mm: float
    header_y_mm: float
    version_y_mm: float
    table_y_mm: float

    column_width_pt: float
    name_offset_pt: float

    row_height_pt: float
    entry_font_name: str
    entry_number_font_name: str
    entry_font_size_pt: int
    entry_line_height_pt: float

    page: str
    orientation: str
    margin_mm: float


@dataclass(frozen=True, slots=True)
class RegionMergeCostConfig:
    """
    Immutable region merge-cost policy configuration.
    """

    color_weight: float
    affected_area_weight: float
    border_weight: float
    geometry_weight: float
    enclosure_strength: float
    compactness_strength: float


@dataclass(frozen=True, slots=True)
class RegionComplexityConfig:
    """
    Immutable optional region-complexity policy configuration.
    """

    reduction_enabled: bool
    max_regions: int
    maximum_merge_cost: float
    merge_cost: RegionMergeCostConfig


@dataclass(frozen=True, slots=True)
class ImageInputLimitsConfig:
    """
    Immutable bounds applied to input images before they are decoded.
    """

    maximum_pixel_count: int
    maximum_width: int
    maximum_height: int
    processing_pixel_count: int


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """
    Immutable application configuration.
    """

    page: str

    orientation: str

    placement: str

    margin_mm: float

    palette: str
    palette_version: int

    input_image: str

    output_pdf: str

    region_complexity: RegionComplexityConfig

    image_input_limits: ImageInputLimitsConfig

    minimum_region_size_mm: float

    color_distance: str

    parallel_quantization_enabled: bool
    parallel_quantization_break_even_workload: int
    parallel_quantization_max_workers: int

    outline_simplification_enabled: bool
    outline_simplification_tolerance_px: float

    font_size_pt: int

    line_width_pt: float

    line_color: str
    number_color: str

    pdf_legend: PdfLegendConfig
