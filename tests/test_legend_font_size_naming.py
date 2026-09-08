# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from pbn.application.generator_config_validator import (
    GeneratorConfigValidator,
)
from pbn.cli.main import build_parser
from pbn.config import GeneratorConfig, PdfLegendConfig
from pbn.exceptions import ConfigurationError
from pbn.infrastructure import load_config


def test_pdf_legend_config_uses_point_suffix_for_entry_font_size() -> None:
    field_names = {field.name for field in fields(PdfLegendConfig)}

    assert "entry_font_size_pt" in field_names
    assert "entry_font_size" not in field_names


def test_generate_accepts_legend_entry_font_size_pt() -> None:
    args = build_parser().parse_args(
        [
            "generate",
            "--legend-entry-font-size-pt",
            "11",
        ],
    )

    assert args.legend_entry_font_size_pt == 11


def test_generate_rejects_old_legend_entry_font_size_parameter() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "generate",
                "--legend-entry-font-size",
                "11",
            ],
        )


def test_loads_entry_font_size_pt_from_toml(
    tmp_path: Path,
) -> None:
    config = load_new_named_config(
        tmp_path,
    )

    assert config.pdf_legend.entry_font_size_pt == 11


def test_validator_reports_entry_font_size_pt(
    tmp_path: Path,
) -> None:
    config = load_new_named_config(
        tmp_path,
    )

    invalid_legend = replace(
        config.pdf_legend,
        entry_font_size_pt=0,
    )
    invalid_config = replace(
        config,
        pdf_legend=invalid_legend,
    )

    with pytest.raises(
        ConfigurationError,
        match=(r"pdf_legend\.entry_font_size_pt " r"must be greater than zero"),
    ):
        GeneratorConfigValidator().validate(
            invalid_config,
        )


def load_new_named_config(
    tmp_path: Path,
) -> GeneratorConfig:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
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
version_y_mm = 278.0
table_y_mm = 265.0
column_width_pt = 118.0
name_offset_pt = 30.0
row_height_pt = 42.5
entry_font_name = "Helvetica"
entry_number_font_name = "Helvetica-Bold"
entry_font_size_pt = 11
entry_line_height_pt = 9.0
""",
        encoding="utf-8",
    )

    return load_config(
        config_file,
    )
