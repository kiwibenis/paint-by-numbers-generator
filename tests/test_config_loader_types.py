# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pbn.exceptions import ConfigurationError
from pbn.infrastructure import load_config

_STRING_FIELDS = (
    ("input", "palette"),
    ("input", "input_image"),
    ("generation", "color_distance"),
    ("output", "page"),
    ("output", "orientation"),
    ("output", "placement"),
    ("output", "output_pdf"),
    ("output", "line_color"),
    ("output", "number_color"),
    ("pdf_legend", "entry_font_name"),
    ("pdf_legend", "entry_number_font_name"),
    ("pdf_legend", "page"),
    ("pdf_legend", "orientation"),
)

_BOOLEAN_FIELDS = (
    (
        "generation",
        "region_complexity_reduction_enabled",
    ),
    (
        "generation",
        "parallel_quantization_enabled",
    ),
    (
        "generation",
        "outline_simplification_enabled",
    ),
)

_INTEGER_FIELDS = (
    ("input", "palette_version"),
    ("generation", "max_regions"),
    (
        "generation",
        "parallel_quantization_break_even_workload",
    ),
    (
        "generation",
        "parallel_quantization_max_workers",
    ),
    ("output", "font_size_pt"),
    ("pdf_legend", "column_count"),
    ("pdf_legend", "rows_per_page"),
    ("pdf_legend", "entry_font_size_pt"),
)

_NUMBER_FIELDS = (
    ("generation", "maximum_merge_cost"),
    ("generation", "merge_cost_color_weight"),
    ("generation", "merge_cost_affected_area_weight"),
    ("generation", "merge_cost_border_weight"),
    ("generation", "merge_cost_geometry_weight"),
    ("generation", "merge_cost_enclosure_strength"),
    ("generation", "merge_cost_compactness_strength"),
    ("generation", "minimum_region_size_mm"),
    ("generation", "outline_simplification_tolerance_px"),
    ("output", "margin_mm"),
    ("output", "line_width_pt"),
    ("pdf_legend", "pixels_per_inch"),
    ("pdf_legend", "points_per_inch"),
    ("pdf_legend", "color_field_px"),
    ("pdf_legend", "start_x_mm"),
    ("pdf_legend", "header_y_mm"),
    ("pdf_legend", "version_y_mm"),
    ("pdf_legend", "table_y_mm"),
    ("pdf_legend", "column_width_pt"),
    ("pdf_legend", "name_offset_pt"),
    ("pdf_legend", "row_height_pt"),
    ("pdf_legend", "entry_line_height_pt"),
    ("pdf_legend", "margin_mm"),
)


@pytest.mark.parametrize(
    ("section", "key"),
    _STRING_FIELDS,
)
def test_load_rejects_non_string_configuration_values(
    tmp_path: Path,
    section: str,
    key: str,
) -> None:
    config_file = write_config(
        tmp_path,
        section=section,
        key=key,
        value="123",
    )

    with pytest.raises(
        ConfigurationError,
        match=re.escape(
            f"Configuration value {section}.{key} must be a string.",
        ),
    ):
        load_config(
            config_file,
        )


@pytest.mark.parametrize(
    ("section", "key"),
    _BOOLEAN_FIELDS,
)
def test_load_rejects_non_boolean_configuration_values(
    tmp_path: Path,
    section: str,
    key: str,
) -> None:
    config_file = write_config(
        tmp_path,
        section=section,
        key=key,
        value='"true"',
    )

    with pytest.raises(
        ConfigurationError,
        match=re.escape(
            f"Configuration value {section}.{key} must be a boolean.",
        ),
    ):
        load_config(
            config_file,
        )


@pytest.mark.parametrize(
    ("section", "key"),
    _INTEGER_FIELDS,
)
def test_load_rejects_non_integer_configuration_values(
    tmp_path: Path,
    section: str,
    key: str,
) -> None:
    config_file = write_config(
        tmp_path,
        section=section,
        key=key,
        value='"invalid"',
    )

    with pytest.raises(
        ConfigurationError,
        match=re.escape(
            f"Configuration value {section}.{key} must be an integer.",
        ),
    ):
        load_config(
            config_file,
        )


@pytest.mark.parametrize(
    ("section", "key"),
    _NUMBER_FIELDS,
)
def test_load_rejects_non_numeric_configuration_values(
    tmp_path: Path,
    section: str,
    key: str,
) -> None:
    config_file = write_config(
        tmp_path,
        section=section,
        key=key,
        value='"invalid"',
    )

    with pytest.raises(
        ConfigurationError,
        match=re.escape(
            f"Configuration value {section}.{key} must be a number.",
        ),
    ):
        load_config(
            config_file,
        )


def test_load_rejects_boolean_for_integer_configuration_value(
    tmp_path: Path,
) -> None:
    config_file = write_config(
        tmp_path,
        section="generation",
        key="max_regions",
        value="true",
    )

    with pytest.raises(
        ConfigurationError,
        match=re.escape(
            "Configuration value generation.max_regions must be an integer.",
        ),
    ):
        load_config(
            config_file,
        )


def test_load_rejects_boolean_for_numeric_configuration_value(
    tmp_path: Path,
) -> None:
    config_file = write_config(
        tmp_path,
        section="output",
        key="line_width_pt",
        value="true",
    )

    with pytest.raises(
        ConfigurationError,
        match=re.escape(
            "Configuration value output.line_width_pt must be a number.",
        ),
    ):
        load_config(
            config_file,
        )


def test_load_accepts_integer_for_float_configuration_value(
    tmp_path: Path,
) -> None:
    config_file = write_config(
        tmp_path,
        section="generation",
        key="minimum_region_size_mm",
        value="3",
    )

    config = load_config(
        config_file,
    )

    assert config.minimum_region_size_mm == 3.0
    assert isinstance(
        config.minimum_region_size_mm,
        float,
    )


def write_config(
    tmp_path: Path,
    *,
    section: str,
    key: str,
    value: str,
) -> Path:
    config_file = tmp_path / "config.toml"

    config_text = replace_config_value(
        create_config_text(),
        section=section,
        key=key,
        value=value,
    )

    config_file.write_text(
        config_text,
        encoding="utf-8",
    )

    return config_file


def replace_config_value(
    config_text: str,
    *,
    section: str,
    key: str,
    value: str,
) -> str:
    lines = config_text.splitlines()
    current_section: str | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1]
            continue

        if current_section != section:
            continue

        if stripped.startswith(f"{key} ="):
            lines[index] = f"{key} = {value}"

            return "\n".join(lines) + "\n"

    raise AssertionError(
        f"Configuration value not found: {section}.{key}",
    )


def create_config_text() -> str:
    return """
[input]
palette = "reference8"
palette_version = 1
input_image = "examples/input/example.png"

[generation]
region_complexity_reduction_enabled = true
max_regions = 350
maximum_merge_cost = 0.300
merge_cost_color_weight = 0.40
merge_cost_affected_area_weight = 0.25
merge_cost_border_weight = 0.15
merge_cost_geometry_weight = 0.20
merge_cost_enclosure_strength = 0.50
merge_cost_compactness_strength = 0.15
minimum_region_size_mm = 3.0
color_distance = "delta_e_76"
parallel_quantization_enabled = true
parallel_quantization_break_even_workload = 360448
parallel_quantization_max_workers = 8
outline_simplification_enabled = true
outline_simplification_tolerance_px = 1.0

[input_limits]
maximum_pixel_count = 50000000
maximum_width = 20000
maximum_height = 20000
processing_pixel_count = 1600000

[output]
page = "A4"
orientation = "landscape"
placement = "fit"
margin_mm = 10.0
output_pdf = "output.pdf"
font_size_pt = 9
line_width_pt = 0.4
line_color = "#000000"
number_color = "#000000"

[pdf_legend]
page = "A4"
orientation = "portrait"
margin_mm = 5.0
pixels_per_inch = 96.0
points_per_inch = 72.0
color_field_px = 30.0
column_count = 4
rows_per_page = 17
start_x_mm = 20.0
header_y_mm = 285.0
version_y_mm = 285.0
table_y_mm = 265.0
column_width_pt = 118.0
name_offset_pt = 30.0
row_height_pt = 42.5
entry_font_name = "Helvetica"
entry_number_font_name = "Helvetica-Bold"
entry_font_size_pt = 9
entry_line_height_pt = 9.0
"""
