# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.application.generator_config_builder import (
    CONFIG_VALUE_NAMES,
    build_config,
)
from pbn.cli.main import build_parser
from pbn.config import (
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.infrastructure import load_config


def create_complete_values() -> dict[str, object]:
    return {
        "input_image": "input.png",
        "output_pdf": "output.pdf",
        "page": "A4",
        "orientation": "landscape",
        "placement": "fit",
        "margin_mm": 10.0,
        "palette": "reference8",
        "palette_version": 1,
        "region_complexity_reduction_enabled": True,
        "max_regions": 350,
        "maximum_merge_cost": 0.300,
        "merge_cost_color_weight": 0.40,
        "merge_cost_affected_area_weight": 0.25,
        "merge_cost_border_weight": 0.15,
        "merge_cost_geometry_weight": 0.20,
        "merge_cost_enclosure_strength": 0.50,
        "merge_cost_compactness_strength": 0.15,
        "minimum_region_size_mm": 3.0,
        "color_distance": "delta_e_2000",
        "parallel_quantization_enabled": True,
        "parallel_quantization_break_even_workload": 360_448,
        "parallel_quantization_max_workers": 8,
        "outline_simplification_enabled": True,
        "outline_simplification_tolerance_px": 1.0,
        "maximum_input_pixel_count": 50_000_000,
        "maximum_input_width": 20_000,
        "maximum_input_height": 20_000,
        "processing_pixel_count": 1_600_000,
        "font_size_pt": 9,
        "line_width_pt": 0.4,
        "line_color": "#000000",
        "number_color": "#000000",
        "legend_pixels_per_inch": 96.0,
        "legend_points_per_inch": 72.0,
        "legend_color_field_px": 30.0,
        "legend_column_count": 4,
        "legend_rows_per_page": 17,
        "legend_start_x_mm": 20.0,
        "legend_header_y_mm": 285.0,
        "legend_version_y_mm": 278.0,
        "legend_table_y_mm": 265.0,
        "legend_column_width_pt": 118.0,
        "legend_name_offset_pt": 30.0,
        "legend_row_height_pt": 42.5,
        "legend_entry_font_name": "Helvetica",
        "legend_entry_number_font_name": "Helvetica-Bold",
        "legend_entry_font_size_pt": 9,
        "legend_entry_line_height_pt": 9.0,
        "legend_page": "A4",
        "legend_orientation": "portrait",
        "legend_margin_mm": 5.0,
    }


def expected_region_complexity_config() -> RegionComplexityConfig:
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


def test_generator_config_requires_complete_region_complexity_policy() -> None:
    assert "regions" not in CONFIG_VALUE_NAMES

    for field_name in (
        "region_complexity_reduction_enabled",
        "max_regions",
        "maximum_merge_cost",
        "merge_cost_color_weight",
        "merge_cost_affected_area_weight",
        "merge_cost_border_weight",
        "merge_cost_geometry_weight",
        "merge_cost_enclosure_strength",
        "merge_cost_compactness_strength",
    ):
        assert field_name in CONFIG_VALUE_NAMES


def test_build_config_embeds_region_complexity_policy() -> None:
    config = build_config(
        create_complete_values(),
    )

    assert config.region_complexity == (expected_region_complexity_config())
    assert not hasattr(
        config,
        "regions",
    )


def test_cli_exposes_region_complexity_policy() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "generate",
            "--region-complexity-reduction-enabled",
            "true",
            "--max-regions",
            "500",
            "--maximum-merge-cost",
            "0.300",
            "--merge-cost-color-weight",
            "0.40",
            "--merge-cost-affected-area-weight",
            "0.25",
            "--merge-cost-border-weight",
            "0.15",
            "--merge-cost-geometry-weight",
            "0.20",
            "--merge-cost-enclosure-strength",
            "0.50",
            "--merge-cost-compactness-strength",
            "0.15",
        ],
    )

    assert args.region_complexity_reduction_enabled is True
    assert args.max_regions == 500
    assert args.maximum_merge_cost == 0.300
    assert args.merge_cost_color_weight == 0.40
    assert args.merge_cost_affected_area_weight == 0.25
    assert args.merge_cost_border_weight == 0.15
    assert args.merge_cost_geometry_weight == 0.20
    assert args.merge_cost_enclosure_strength == 0.50
    assert args.merge_cost_compactness_strength == 0.15
    assert not hasattr(
        args,
        "regions",
    )


def test_cli_rejects_removed_regions_option() -> None:
    parser = build_parser()

    with pytest.raises(
        SystemExit,
    ):
        parser.parse_args(
            [
                "generate",
                "--regions",
                "350",
            ],
        )


def test_example_config_contains_region_complexity_policy() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    assert config.region_complexity == (
        RegionComplexityConfig(
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
    )
