# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pathlib import Path

import pytest

from pbn.exceptions import ConfigurationError
from pbn.infrastructure import load_config
from pbn.infrastructure.config_loader import load_config_values


def test_load_palette_version() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    assert config.palette_version == 1


def test_load_example_config() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    assert config.region_complexity.reduction_enabled is True
    assert config.region_complexity.max_regions == 350
    assert config.region_complexity.maximum_merge_cost == 0.300
    assert config.region_complexity.merge_cost.color_weight == 0.40
    assert config.region_complexity.merge_cost.affected_area_weight == 0.25
    assert config.region_complexity.merge_cost.border_weight == 0.15
    assert config.region_complexity.merge_cost.geometry_weight == 0.20
    assert config.region_complexity.merge_cost.enclosure_strength == 0.50
    assert config.region_complexity.merge_cost.compactness_strength == 0.15
    assert config.palette == "reference8"
    assert config.input_image == "examples/input/example.png"
    assert config.output_pdf == "examples/output/example.pdf"
    assert config.placement == "fit"
    assert config.margin_mm == 5.0
    assert config.color_distance == "delta_e_2000"
    assert config.parallel_quantization_enabled is True
    assert config.parallel_quantization_break_even_workload == 557_056
    assert config.parallel_quantization_max_workers == 8
    assert config.outline_simplification_enabled is False
    assert config.outline_simplification_tolerance_px == 1.0
    assert config.line_color == "#000000"
    assert config.number_color == "#000000"


def test_load_output_margin_from_toml(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        create_config_text(
            margin_mm=12.5,
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file,
    )

    assert config.margin_mm == 12.5


def test_load_output_margin_selectively() -> None:
    values = load_config_values(
        Path("config/example.toml"),
        ("margin_mm",),
    )

    assert values == {
        "margin_mm": 5.0,
    }


def test_load_pdf_legend_config() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    assert config.pdf_legend.pixels_per_inch == 96.0
    assert config.pdf_legend.points_per_inch == 72.0
    assert config.pdf_legend.color_field_px == 30.0

    assert config.pdf_legend.column_count == 4
    assert config.pdf_legend.rows_per_page == 17

    assert config.pdf_legend.start_x_mm == 20.0
    assert config.pdf_legend.header_y_mm == 284.0
    assert config.pdf_legend.version_y_mm == 284.0
    assert config.pdf_legend.table_y_mm == 265.0

    assert config.pdf_legend.column_width_pt == 118.0
    assert config.pdf_legend.name_offset_pt == 30.0

    assert config.pdf_legend.row_height_pt == 42.5
    assert config.pdf_legend.entry_font_name == "Helvetica"
    assert config.pdf_legend.entry_number_font_name == "Helvetica-Bold"
    assert config.pdf_legend.entry_font_size_pt == 9
    assert config.pdf_legend.entry_line_height_pt == 9.0
    assert config.pdf_legend.margin_mm == 5.0


def test_load_pdf_legend_page_and_orientation_from_toml(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        create_config_text(
            legend_page="A3",
            legend_orientation="portrait",
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file,
    )

    assert config.pdf_legend.page == "A3"
    assert config.pdf_legend.orientation == "portrait"


def test_load_missing_config_file_reports_configuration_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "missing.toml"

    with pytest.raises(
        ConfigurationError,
        match="Could not read configuration file",
    ):
        load_config(
            config_file,
        )


def test_load_invalid_toml_reports_configuration_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[input\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError,
        match="Configuration file contains invalid TOML",
    ):
        load_config(
            config_file,
        )


def test_load_missing_required_section_reports_configuration_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"

    config_text = create_config_text().replace(
        "[generation]",
        "[missing_generation]",
        1,
    )

    config_file.write_text(
        config_text,
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError,
        match="Missing required configuration value",
    ):
        load_config(
            config_file,
        )


def test_load_missing_required_key_reports_configuration_error(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"

    config_text = create_config_text().replace(
        'output_pdf = "output.pdf"\n',
        "",
        1,
    )

    config_file.write_text(
        config_text,
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError,
        match="Missing required configuration value",
    ):
        load_config(
            config_file,
        )


@pytest.mark.parametrize(
    ("old_value", "new_value", "expected_error"),
    [
        (
            'page = "A4"',
            'page = "A5"',
            "Unsupported page size: A5",
        ),
        (
            "max_regions = 350",
            "max_regions = 0",
            "region_complexity.max_regions must be greater than zero",
        ),
        (
            "minimum_region_size_mm = 3.0",
            "minimum_region_size_mm = -1.0",
            "minimum_region_size_mm must be greater than zero",
        ),
        (
            'color_distance = "delta_e_76"',
            'color_distance = "unsupported"',
            "Unsupported color distance: unsupported",
        ),
        (
            'orientation = "landscape"',
            'orientation = "diagonal"',
            "Unsupported orientation: diagonal",
        ),
        (
            'placement = "fit"',
            'placement = "stretch"',
            "Unsupported image placement: stretch",
        ),
        (
            "margin_mm = 5.0",
            "margin_mm = 0.0",
            "margin_mm must be greater than zero",
        ),
    ],
)
def test_load_rejects_semantically_invalid_configuration(
    tmp_path: Path,
    old_value: str,
    new_value: str,
    expected_error: str,
) -> None:
    config_file = tmp_path / "config.toml"

    config_text = create_config_text().replace(
        old_value,
        new_value,
        1,
    )

    config_file.write_text(
        config_text,
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError,
        match=expected_error,
    ):
        load_config(
            config_file,
        )


def create_config_text(
    *,
    margin_mm: float = 5.0,
    legend_page: str = "A4",
    legend_orientation: str = "portrait",
    legend_margin_mm: float = 5.0,
) -> str:
    return f"""
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
margin_mm = {margin_mm}
output_pdf = "output.pdf"
font_size_pt = 9
line_width_pt = 0.4
line_color = "#000000"
number_color = "#000000"

[pdf_legend]
page = "{legend_page}"
orientation = "{legend_orientation}"
margin_mm = {legend_margin_mm}
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
entry_font_size_pt = 9
entry_line_height_pt = 9.0
"""
