# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from pbn.application.generator_config_builder import build_config
from pbn.config import GeneratorConfig
from pbn.exceptions import ConfigurationError

_TOML_VALUE_PATHS = {
    "input_image": ("input", "input_image"),
    "output_pdf": ("output", "output_pdf"),
    "page": ("output", "page"),
    "orientation": ("output", "orientation"),
    "placement": ("output", "placement"),
    "margin_mm": ("output", "margin_mm"),
    "palette": ("input", "palette"),
    "palette_version": ("input", "palette_version"),
    "region_complexity_reduction_enabled": (
        "generation",
        "region_complexity_reduction_enabled",
    ),
    "max_regions": (
        "generation",
        "max_regions",
    ),
    "maximum_merge_cost": (
        "generation",
        "maximum_merge_cost",
    ),
    "merge_cost_color_weight": (
        "generation",
        "merge_cost_color_weight",
    ),
    "merge_cost_affected_area_weight": (
        "generation",
        "merge_cost_affected_area_weight",
    ),
    "merge_cost_border_weight": (
        "generation",
        "merge_cost_border_weight",
    ),
    "merge_cost_geometry_weight": (
        "generation",
        "merge_cost_geometry_weight",
    ),
    "merge_cost_enclosure_strength": (
        "generation",
        "merge_cost_enclosure_strength",
    ),
    "merge_cost_compactness_strength": (
        "generation",
        "merge_cost_compactness_strength",
    ),
    "maximum_input_pixel_count": (
        "input_limits",
        "maximum_pixel_count",
    ),
    "maximum_input_width": (
        "input_limits",
        "maximum_width",
    ),
    "maximum_input_height": (
        "input_limits",
        "maximum_height",
    ),
    "processing_pixel_count": (
        "input_limits",
        "processing_pixel_count",
    ),
    "minimum_region_size_mm": (
        "generation",
        "minimum_region_size_mm",
    ),
    "color_distance": (
        "generation",
        "color_distance",
    ),
    "parallel_quantization_enabled": (
        "generation",
        "parallel_quantization_enabled",
    ),
    "parallel_quantization_break_even_workload": (
        "generation",
        "parallel_quantization_break_even_workload",
    ),
    "parallel_quantization_max_workers": (
        "generation",
        "parallel_quantization_max_workers",
    ),
    "outline_simplification_enabled": (
        "generation",
        "outline_simplification_enabled",
    ),
    "outline_simplification_tolerance_px": (
        "generation",
        "outline_simplification_tolerance_px",
    ),
    "font_size_pt": ("output", "font_size_pt"),
    "line_width_pt": ("output", "line_width_pt"),
    "line_color": ("output", "line_color"),
    "number_color": ("output", "number_color"),
    "legend_pixels_per_inch": (
        "pdf_legend",
        "pixels_per_inch",
    ),
    "legend_points_per_inch": (
        "pdf_legend",
        "points_per_inch",
    ),
    "legend_color_field_px": (
        "pdf_legend",
        "color_field_px",
    ),
    "legend_column_count": (
        "pdf_legend",
        "column_count",
    ),
    "legend_rows_per_page": (
        "pdf_legend",
        "rows_per_page",
    ),
    "legend_start_x_mm": (
        "pdf_legend",
        "start_x_mm",
    ),
    "legend_header_y_mm": (
        "pdf_legend",
        "header_y_mm",
    ),
    "legend_version_y_mm": (
        "pdf_legend",
        "version_y_mm",
    ),
    "legend_table_y_mm": (
        "pdf_legend",
        "table_y_mm",
    ),
    "legend_column_width_pt": (
        "pdf_legend",
        "column_width_pt",
    ),
    "legend_name_offset_pt": (
        "pdf_legend",
        "name_offset_pt",
    ),
    "legend_row_height_pt": (
        "pdf_legend",
        "row_height_pt",
    ),
    "legend_entry_font_name": (
        "pdf_legend",
        "entry_font_name",
    ),
    "legend_entry_number_font_name": (
        "pdf_legend",
        "entry_number_font_name",
    ),
    "legend_entry_font_size_pt": (
        "pdf_legend",
        "entry_font_size_pt",
    ),
    "legend_entry_line_height_pt": (
        "pdf_legend",
        "entry_line_height_pt",
    ),
    "legend_page": (
        "pdf_legend",
        "page",
    ),
    "legend_orientation": (
        "pdf_legend",
        "orientation",
    ),
    "legend_margin_mm": (
        "pdf_legend",
        "margin_mm",
    ),
}


def load_config(config_file: Path) -> GeneratorConfig:
    """
    Load and validate application configuration from TOML.
    """

    data = _load_toml(
        config_file,
    )

    input_data = _read_table(
        data,
        "input",
    )
    generation_data = _read_table(
        data,
        "generation",
    )
    output_data = _read_table(
        data,
        "output",
    )
    pdf_legend_data = _read_table(
        data,
        "pdf_legend",
    )
    input_limits_data = _read_table(
        data,
        "input_limits",
    )

    values: dict[str, object] = {
        "input_image": _read_string(
            input_data,
            "input",
            "input_image",
        ),
        "output_pdf": _read_string(
            output_data,
            "output",
            "output_pdf",
        ),
        "page": _read_string(
            output_data,
            "output",
            "page",
        ),
        "orientation": _read_string(
            output_data,
            "output",
            "orientation",
        ),
        "placement": _read_string(
            output_data,
            "output",
            "placement",
        ),
        "margin_mm": _read_number(
            output_data,
            "output",
            "margin_mm",
        ),
        "palette": _read_string(
            input_data,
            "input",
            "palette",
        ),
        "palette_version": _read_integer(
            input_data,
            "input",
            "palette_version",
        ),
        "region_complexity_reduction_enabled": _read_boolean(
            generation_data,
            "generation",
            "region_complexity_reduction_enabled",
        ),
        "max_regions": _read_integer(
            generation_data,
            "generation",
            "max_regions",
        ),
        "maximum_merge_cost": _read_number(
            generation_data,
            "generation",
            "maximum_merge_cost",
        ),
        "merge_cost_color_weight": _read_number(
            generation_data,
            "generation",
            "merge_cost_color_weight",
        ),
        "merge_cost_affected_area_weight": _read_number(
            generation_data,
            "generation",
            "merge_cost_affected_area_weight",
        ),
        "merge_cost_border_weight": _read_number(
            generation_data,
            "generation",
            "merge_cost_border_weight",
        ),
        "merge_cost_geometry_weight": _read_number(
            generation_data,
            "generation",
            "merge_cost_geometry_weight",
        ),
        "merge_cost_enclosure_strength": _read_number(
            generation_data,
            "generation",
            "merge_cost_enclosure_strength",
        ),
        "merge_cost_compactness_strength": _read_number(
            generation_data,
            "generation",
            "merge_cost_compactness_strength",
        ),
        "minimum_region_size_mm": _read_number(
            generation_data,
            "generation",
            "minimum_region_size_mm",
        ),
        "color_distance": _read_string(
            generation_data,
            "generation",
            "color_distance",
        ),
        "parallel_quantization_enabled": _read_boolean(
            generation_data,
            "generation",
            "parallel_quantization_enabled",
        ),
        "parallel_quantization_break_even_workload": _read_integer(
            generation_data,
            "generation",
            "parallel_quantization_break_even_workload",
        ),
        "parallel_quantization_max_workers": _read_integer(
            generation_data,
            "generation",
            "parallel_quantization_max_workers",
        ),
        "outline_simplification_enabled": _read_boolean(
            generation_data,
            "generation",
            "outline_simplification_enabled",
        ),
        "outline_simplification_tolerance_px": _read_number(
            generation_data,
            "generation",
            "outline_simplification_tolerance_px",
        ),
        "maximum_input_pixel_count": _read_integer(
            input_limits_data,
            "input_limits",
            "maximum_pixel_count",
        ),
        "maximum_input_width": _read_integer(
            input_limits_data,
            "input_limits",
            "maximum_width",
        ),
        "maximum_input_height": _read_integer(
            input_limits_data,
            "input_limits",
            "maximum_height",
        ),
        "processing_pixel_count": _read_integer(
            input_limits_data,
            "input_limits",
            "processing_pixel_count",
        ),
        "font_size_pt": _read_integer(
            output_data,
            "output",
            "font_size_pt",
        ),
        "line_width_pt": _read_number(
            output_data,
            "output",
            "line_width_pt",
        ),
        "line_color": _read_string(
            output_data,
            "output",
            "line_color",
        ),
        "number_color": _read_string(
            output_data,
            "output",
            "number_color",
        ),
        "legend_pixels_per_inch": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "pixels_per_inch",
        ),
        "legend_points_per_inch": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "points_per_inch",
        ),
        "legend_color_field_px": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "color_field_px",
        ),
        "legend_column_count": _read_integer(
            pdf_legend_data,
            "pdf_legend",
            "column_count",
        ),
        "legend_rows_per_page": _read_integer(
            pdf_legend_data,
            "pdf_legend",
            "rows_per_page",
        ),
        "legend_start_x_mm": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "start_x_mm",
        ),
        "legend_header_y_mm": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "header_y_mm",
        ),
        "legend_version_y_mm": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "version_y_mm",
        ),
        "legend_table_y_mm": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "table_y_mm",
        ),
        "legend_column_width_pt": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "column_width_pt",
        ),
        "legend_name_offset_pt": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "name_offset_pt",
        ),
        "legend_row_height_pt": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "row_height_pt",
        ),
        "legend_entry_font_name": _read_string(
            pdf_legend_data,
            "pdf_legend",
            "entry_font_name",
        ),
        "legend_entry_number_font_name": _read_string(
            pdf_legend_data,
            "pdf_legend",
            "entry_number_font_name",
        ),
        "legend_entry_font_size_pt": _read_integer(
            pdf_legend_data,
            "pdf_legend",
            "entry_font_size_pt",
        ),
        "legend_entry_line_height_pt": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "entry_line_height_pt",
        ),
        "legend_page": _read_string(
            pdf_legend_data,
            "pdf_legend",
            "page",
        ),
        "legend_orientation": _read_string(
            pdf_legend_data,
            "pdf_legend",
            "orientation",
        ),
        "legend_margin_mm": _read_number(
            pdf_legend_data,
            "pdf_legend",
            "margin_mm",
        ),
    }

    return build_config(
        values,
    )


def load_config_values(
    config_file: Path,
    value_names: Iterable[str],
) -> dict[str, object]:
    """
    Load only requested configuration values from TOML.

    Values not requested by the caller are ignored. This allows explicit
    command-line values to take precedence before TOML values are validated.
    """

    data = _load_toml(
        config_file,
    )

    values: dict[str, object] = {}

    for value_name in value_names:
        try:
            section, key = _TOML_VALUE_PATHS[value_name]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported configuration value: {value_name}",
            ) from exc

        section_value = data.get(
            section,
        )

        if section_value is None:
            continue

        if not isinstance(
            section_value,
            dict,
        ):
            raise ConfigurationError(
                f"Configuration section {section} must be a table.",
            )

        section_data = cast(
            dict[str, Any],
            section_value,
        )

        if key not in section_data:
            continue

        values[value_name] = section_data[key]

    return values


def _load_toml(
    config_file: Path,
) -> dict[str, Any]:
    try:
        with config_file.open("rb") as fp:
            data = tomllib.load(fp)
    except OSError as exc:
        raise ConfigurationError(
            f"Could not read configuration file: {config_file}",
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(
            f"Configuration file contains invalid TOML: {config_file}",
        ) from exc

    return data


def _read_table(
    data: dict[str, Any],
    section: str,
) -> dict[str, Any]:
    value = _read_required_value(
        data,
        section,
    )

    if not isinstance(value, dict):
        raise ConfigurationError(
            f"Configuration section {section} must be a table.",
        )

    return cast(
        dict[str, Any],
        value,
    )


def _read_string(
    data: dict[str, Any],
    section: str,
    key: str,
) -> str:
    value = _read_required_value(
        data,
        key,
    )

    if not isinstance(value, str):
        raise ConfigurationError(
            f"Configuration value {section}.{key} must be a string.",
        )

    return value


def _read_boolean(
    data: dict[str, Any],
    section: str,
    key: str,
) -> bool:
    value = _read_required_value(
        data,
        key,
    )

    if not isinstance(
        value,
        bool,
    ):
        raise ConfigurationError(
            f"Configuration value {section}.{key} must be a boolean.",
        )

    return value


def _read_integer(
    data: dict[str, Any],
    section: str,
    key: str,
) -> int:
    value = _read_required_value(
        data,
        key,
    )

    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"Configuration value {section}.{key} must be an integer.",
        )

    return value


def _read_number(
    data: dict[str, Any],
    section: str,
    key: str,
) -> float:
    value = _read_required_value(
        data,
        key,
    )

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ConfigurationError(
            f"Configuration value {section}.{key} must be a number.",
        )

    return float(value)


def _read_required_value(
    data: dict[str, Any],
    key: str,
) -> Any:
    try:
        return data[key]
    except KeyError as exc:
        raise ConfigurationError(
            f"Missing required configuration value: {key}",
        ) from exc
