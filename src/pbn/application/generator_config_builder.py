# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.exceptions import ConfigurationError

from .generator_config_validator import GeneratorConfigValidator

MERGE_COST_CONFIG_VALUE_NAMES = (
    "merge_cost_color_weight",
    "merge_cost_affected_area_weight",
    "merge_cost_border_weight",
    "merge_cost_geometry_weight",
    "merge_cost_enclosure_strength",
    "merge_cost_compactness_strength",
)

REGION_COMPLEXITY_CONFIG_VALUE_NAMES = (
    "region_complexity_reduction_enabled",
    "max_regions",
    "maximum_merge_cost",
    *MERGE_COST_CONFIG_VALUE_NAMES,
)

IMAGE_INPUT_LIMITS_CONFIG_VALUE_NAMES = (
    "maximum_input_pixel_count",
    "maximum_input_width",
    "maximum_input_height",
    "processing_pixel_count",
)

CONFIG_VALUE_NAMES = (
    "input_image",
    "output_pdf",
    "page",
    "orientation",
    "placement",
    "margin_mm",
    "palette",
    "palette_version",
    *REGION_COMPLEXITY_CONFIG_VALUE_NAMES,
    *IMAGE_INPUT_LIMITS_CONFIG_VALUE_NAMES,
    "minimum_region_size_mm",
    "color_distance",
    "parallel_quantization_enabled",
    "parallel_quantization_break_even_workload",
    "parallel_quantization_max_workers",
    "outline_simplification_enabled",
    "outline_simplification_tolerance_px",
    "font_size_pt",
    "line_width_pt",
    "line_color",
    "number_color",
    "legend_pixels_per_inch",
    "legend_points_per_inch",
    "legend_color_field_px",
    "legend_column_count",
    "legend_rows_per_page",
    "legend_start_x_mm",
    "legend_header_y_mm",
    "legend_version_y_mm",
    "legend_table_y_mm",
    "legend_column_width_pt",
    "legend_name_offset_pt",
    "legend_row_height_pt",
    "legend_entry_font_name",
    "legend_entry_number_font_name",
    "legend_entry_font_size_pt",
    "legend_entry_line_height_pt",
    "legend_page",
    "legend_orientation",
    "legend_margin_mm",
)


@dataclass(frozen=True, slots=True)
class _PdfLegendConfigCandidate:
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
class _GeneratorConfigCandidate:
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
    pdf_legend: _PdfLegendConfigCandidate


def missing_config_values(
    values: Mapping[str, object],
) -> tuple[str, ...]:
    """
    Return required configuration values not present in the mapping.
    """

    return tuple(name for name in CONFIG_VALUE_NAMES if name not in values)


def build_region_merge_cost_config(
    values: Mapping[str, object],
) -> RegionMergeCostConfig:
    """
    Validate effective merge-cost values and build its configuration.
    """
    missing = tuple(
        name for name in MERGE_COST_CONFIG_VALUE_NAMES if name not in values
    )

    if missing:
        raise ConfigurationError(
            "Missing required merge-cost configuration values: "
            f"{', '.join(missing)}.",
        )

    config = RegionMergeCostConfig(
        color_weight=_require_number(
            values,
            "merge_cost_color_weight",
        ),
        affected_area_weight=_require_number(
            values,
            "merge_cost_affected_area_weight",
        ),
        border_weight=_require_number(
            values,
            "merge_cost_border_weight",
        ),
        geometry_weight=_require_number(
            values,
            "merge_cost_geometry_weight",
        ),
        enclosure_strength=_require_number(
            values,
            "merge_cost_enclosure_strength",
        ),
        compactness_strength=_require_number(
            values,
            "merge_cost_compactness_strength",
        ),
    )

    GeneratorConfigValidator().validate_region_merge_cost(
        config,
    )

    return config


def build_image_input_limits_config(
    values: Mapping[str, object],
) -> ImageInputLimitsConfig:
    """
    Validate effective input-limit values and build their configuration.
    """
    missing = tuple(
        name for name in IMAGE_INPUT_LIMITS_CONFIG_VALUE_NAMES if name not in values
    )

    if missing:
        raise ConfigurationError(
            "Missing required image input limit configuration values: "
            f"{', '.join(missing)}.",
        )

    config = ImageInputLimitsConfig(
        maximum_pixel_count=_require_integer(
            values,
            "maximum_input_pixel_count",
        ),
        maximum_width=_require_integer(
            values,
            "maximum_input_width",
        ),
        maximum_height=_require_integer(
            values,
            "maximum_input_height",
        ),
        processing_pixel_count=_require_integer(
            values,
            "processing_pixel_count",
        ),
    )

    GeneratorConfigValidator().validate_image_input_limits(
        config,
    )

    return config


def build_region_complexity_config(
    values: Mapping[str, object],
) -> RegionComplexityConfig:
    """
    Validate effective region-complexity values and build its configuration.
    """
    missing = tuple(
        name for name in REGION_COMPLEXITY_CONFIG_VALUE_NAMES if name not in values
    )

    if missing:
        raise ConfigurationError(
            "Missing required region-complexity configuration values: "
            f"{', '.join(missing)}.",
        )

    config = RegionComplexityConfig(
        reduction_enabled=_require_boolean(
            values,
            "region_complexity_reduction_enabled",
        ),
        max_regions=_require_integer(
            values,
            "max_regions",
        ),
        maximum_merge_cost=_require_number(
            values,
            "maximum_merge_cost",
        ),
        merge_cost=build_region_merge_cost_config(
            values,
        ),
    )

    GeneratorConfigValidator().validate_region_complexity(
        config,
    )

    return config


def build_config(
    values: Mapping[str, object],
) -> GeneratorConfig:
    """
    Validate effective configuration values and build GeneratorConfig.
    """

    missing = missing_config_values(
        values,
    )

    if missing:
        raise ConfigurationError(
            "Missing required configuration values: " f"{', '.join(missing)}.",
        )

    region_complexity = build_region_complexity_config(
        values,
    )

    image_input_limits = build_image_input_limits_config(
        values,
    )

    legend = _PdfLegendConfigCandidate(
        pixels_per_inch=_require_number(
            values,
            "legend_pixels_per_inch",
        ),
        points_per_inch=_require_number(
            values,
            "legend_points_per_inch",
        ),
        color_field_px=_require_number(
            values,
            "legend_color_field_px",
        ),
        column_count=_require_integer(
            values,
            "legend_column_count",
        ),
        rows_per_page=_require_integer(
            values,
            "legend_rows_per_page",
        ),
        start_x_mm=_require_number(
            values,
            "legend_start_x_mm",
        ),
        header_y_mm=_require_number(
            values,
            "legend_header_y_mm",
        ),
        version_y_mm=_require_number(
            values,
            "legend_version_y_mm",
        ),
        table_y_mm=_require_number(
            values,
            "legend_table_y_mm",
        ),
        column_width_pt=_require_number(
            values,
            "legend_column_width_pt",
        ),
        name_offset_pt=_require_number(
            values,
            "legend_name_offset_pt",
        ),
        row_height_pt=_require_number(
            values,
            "legend_row_height_pt",
        ),
        entry_font_name=_require_string(
            values,
            "legend_entry_font_name",
        ),
        entry_number_font_name=_require_string(
            values,
            "legend_entry_number_font_name",
        ),
        entry_font_size_pt=_require_integer(
            values,
            "legend_entry_font_size_pt",
        ),
        entry_line_height_pt=_require_number(
            values,
            "legend_entry_line_height_pt",
        ),
        page=_require_string(
            values,
            "legend_page",
        ),
        orientation=_require_string(
            values,
            "legend_orientation",
        ),
        margin_mm=_require_number(
            values,
            "legend_margin_mm",
        ),
    )

    candidate = _GeneratorConfigCandidate(
        page=_require_string(
            values,
            "page",
        ),
        orientation=_require_string(
            values,
            "orientation",
        ),
        placement=_require_string(
            values,
            "placement",
        ),
        margin_mm=_require_number(
            values,
            "margin_mm",
        ),
        palette=_require_string(
            values,
            "palette",
        ),
        palette_version=_require_integer(
            values,
            "palette_version",
        ),
        input_image=_require_string(
            values,
            "input_image",
        ),
        output_pdf=_require_string(
            values,
            "output_pdf",
        ),
        region_complexity=region_complexity,
        image_input_limits=image_input_limits,
        minimum_region_size_mm=_require_number(
            values,
            "minimum_region_size_mm",
        ),
        color_distance=_require_string(
            values,
            "color_distance",
        ),
        parallel_quantization_enabled=_require_boolean(
            values,
            "parallel_quantization_enabled",
        ),
        parallel_quantization_break_even_workload=_require_integer(
            values,
            "parallel_quantization_break_even_workload",
        ),
        parallel_quantization_max_workers=_require_integer(
            values,
            "parallel_quantization_max_workers",
        ),
        outline_simplification_enabled=_require_boolean(
            values,
            "outline_simplification_enabled",
        ),
        outline_simplification_tolerance_px=_require_number(
            values,
            "outline_simplification_tolerance_px",
        ),
        font_size_pt=_require_integer(
            values,
            "font_size_pt",
        ),
        line_width_pt=_require_number(
            values,
            "line_width_pt",
        ),
        line_color=_require_string(
            values,
            "line_color",
        ),
        number_color=_require_string(
            values,
            "number_color",
        ),
        pdf_legend=legend,
    )

    GeneratorConfigValidator().validate(
        candidate,
    )

    pdf_legend = PdfLegendConfig(
        pixels_per_inch=legend.pixels_per_inch,
        points_per_inch=legend.points_per_inch,
        color_field_px=legend.color_field_px,
        column_count=legend.column_count,
        rows_per_page=legend.rows_per_page,
        start_x_mm=legend.start_x_mm,
        header_y_mm=legend.header_y_mm,
        version_y_mm=legend.version_y_mm,
        table_y_mm=legend.table_y_mm,
        column_width_pt=legend.column_width_pt,
        name_offset_pt=legend.name_offset_pt,
        row_height_pt=legend.row_height_pt,
        entry_font_name=legend.entry_font_name,
        entry_number_font_name=legend.entry_number_font_name,
        entry_font_size_pt=legend.entry_font_size_pt,
        entry_line_height_pt=legend.entry_line_height_pt,
        page=legend.page,
        orientation=legend.orientation,
        margin_mm=legend.margin_mm,
    )

    return GeneratorConfig(
        page=candidate.page,
        orientation=candidate.orientation,
        placement=candidate.placement,
        margin_mm=candidate.margin_mm,
        palette=candidate.palette,
        palette_version=candidate.palette_version,
        input_image=candidate.input_image,
        output_pdf=candidate.output_pdf,
        region_complexity=candidate.region_complexity,
        image_input_limits=candidate.image_input_limits,
        minimum_region_size_mm=(candidate.minimum_region_size_mm),
        color_distance=candidate.color_distance,
        parallel_quantization_enabled=(candidate.parallel_quantization_enabled),
        parallel_quantization_break_even_workload=(
            candidate.parallel_quantization_break_even_workload
        ),
        parallel_quantization_max_workers=(candidate.parallel_quantization_max_workers),
        outline_simplification_enabled=(candidate.outline_simplification_enabled),
        outline_simplification_tolerance_px=(
            candidate.outline_simplification_tolerance_px
        ),
        font_size_pt=candidate.font_size_pt,
        line_width_pt=candidate.line_width_pt,
        line_color=candidate.line_color,
        number_color=candidate.number_color,
        pdf_legend=pdf_legend,
    )


def _require_string(
    values: Mapping[str, object],
    name: str,
) -> str:
    value = values[name]

    if not isinstance(
        value,
        str,
    ):
        raise ConfigurationError(
            f"Configuration value {name} must be a string.",
        )

    return value


def _require_boolean(
    values: Mapping[str, object],
    name: str,
) -> bool:
    value = values[name]

    if not isinstance(
        value,
        bool,
    ):
        raise ConfigurationError(
            f"Configuration value {name} must be a boolean.",
        )

    return value


def _require_integer(
    values: Mapping[str, object],
    name: str,
) -> int:
    value = values[name]

    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        int,
    ):
        raise ConfigurationError(
            f"Configuration value {name} must be an integer.",
        )

    return value


def _require_number(
    values: Mapping[str, object],
    name: str,
) -> float:
    value = values[name]

    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        (int, float),
    ):
        raise ConfigurationError(
            f"Configuration value {name} must be a number.",
        )

    return float(
        value,
    )
