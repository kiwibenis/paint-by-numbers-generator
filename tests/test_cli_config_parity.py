# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from dataclasses import fields
from pathlib import Path

import pytest

from pbn.cli.main import build_parser
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from tests.fake_image_loader import loader_class_for

cli_main = importlib.import_module(
    "pbn.cli.main",
)

_REGION_COMPLEXITY_CLI_DESTINATIONS = (
    "region_complexity_reduction_enabled",
    "max_regions",
    "maximum_merge_cost",
    "merge_cost_color_weight",
    "merge_cost_affected_area_weight",
    "merge_cost_border_weight",
    "merge_cost_geometry_weight",
    "merge_cost_enclosure_strength",
    "merge_cost_compactness_strength",
)

_IMAGE_INPUT_LIMITS_CLI_DESTINATIONS = (
    "maximum_input_pixel_count",
    "maximum_input_width",
    "maximum_input_height",
    "processing_pixel_count",
)


def create_pdf_legend_config() -> PdfLegendConfig:
    return PdfLegendConfig(
        pixels_per_inch=96.0,
        points_per_inch=72.0,
        color_field_px=30.0,
        column_count=4,
        rows_per_page=17,
        start_x_mm=20.0,
        header_y_mm=285.0,
        version_y_mm=285.0,
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
    )


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


def create_config(
    tmp_path: Path,
) -> GeneratorConfig:
    return GeneratorConfig(
        page="A4",
        orientation="landscape",
        placement="fit",
        margin_mm=10.0,
        palette="reference8",
        palette_version=1,
        input_image="input.png",
        output_pdf=str(tmp_path / "output.pdf"),
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
        pdf_legend=create_pdf_legend_config(),
    )


def test_cli_exposes_every_configurable_value() -> None:
    args = build_parser().parse_args(
        ["generate"],
    )

    namespace = vars(args)

    generator_destinations = {
        "input_image": "input",
        "output_pdf": "output",
    }

    for field in fields(GeneratorConfig):
        if field.name in {
            "pdf_legend",
            "region_complexity",
            "image_input_limits",
        }:
            continue

        destination = generator_destinations.get(
            field.name,
            field.name,
        )

        assert destination in namespace

    for destination in _REGION_COMPLEXITY_CLI_DESTINATIONS:
        assert destination in namespace

    for destination in _IMAGE_INPUT_LIMITS_CLI_DESTINATIONS:
        assert destination in namespace

    for field in fields(PdfLegendConfig):
        destination = f"legend_{field.name}"

        assert destination in namespace

    assert "regions" not in namespace


def test_generate_accepts_all_legend_parameters() -> None:
    args = build_parser().parse_args(
        [
            "generate",
            "--legend-pixels-per-inch",
            "120",
            "--legend-points-per-inch",
            "72",
            "--legend-color-field-px",
            "40",
            "--legend-column-count",
            "5",
            "--legend-rows-per-page",
            "20",
            "--legend-start-x-mm",
            "15",
            "--legend-header-y-mm",
            "400",
            "--legend-version-y-mm",
            "390",
            "--legend-table-y-mm",
            "370",
            "--legend-column-width-pt",
            "130",
            "--legend-name-offset-pt",
            "35",
            "--legend-row-height-pt",
            "45",
            "--legend-entry-font-name",
            "Courier",
            "--legend-entry-number-font-name",
            "Courier-Bold",
            "--legend-entry-font-size-pt",
            "11",
            "--legend-entry-line-height-pt",
            "12",
            "--legend-page",
            "A3",
            "--legend-orientation",
            "landscape",
            "--legend-margin-mm",
            "7.5",
        ],
    )

    assert args.legend_pixels_per_inch == 120.0
    assert args.legend_points_per_inch == 72.0
    assert args.legend_color_field_px == 40.0
    assert args.legend_column_count == 5
    assert args.legend_rows_per_page == 20
    assert args.legend_start_x_mm == 15.0
    assert args.legend_header_y_mm == 400.0
    assert args.legend_version_y_mm == 390.0
    assert args.legend_table_y_mm == 370.0
    assert args.legend_column_width_pt == 130.0
    assert args.legend_name_offset_pt == 35.0
    assert args.legend_row_height_pt == 45.0
    assert args.legend_entry_font_name == "Courier"
    assert args.legend_entry_number_font_name == "Courier-Bold"
    assert args.legend_entry_font_size_pt == 11
    assert args.legend_entry_line_height_pt == 12.0
    assert args.legend_page == "A3"
    assert args.legend_orientation == "landscape"
    assert args.legend_margin_mm == 7.5


def test_generate_passes_all_legend_values_to_effective_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path,
    )

    complexity = config.region_complexity
    merge_cost = complexity.merge_cost
    limits = config.image_input_limits

    captured: dict[str, object] = {}

    fallback_values: dict[str, object] = {
        "input_image": config.input_image,
        "output_pdf": config.output_pdf,
        "page": config.page,
        "orientation": config.orientation,
        "placement": config.placement,
        "margin_mm": config.margin_mm,
        "palette": config.palette,
        "palette_version": config.palette_version,
        "region_complexity_reduction_enabled": (complexity.reduction_enabled),
        "max_regions": complexity.max_regions,
        "maximum_merge_cost": complexity.maximum_merge_cost,
        "merge_cost_color_weight": merge_cost.color_weight,
        "merge_cost_affected_area_weight": (merge_cost.affected_area_weight),
        "merge_cost_border_weight": merge_cost.border_weight,
        "merge_cost_geometry_weight": merge_cost.geometry_weight,
        "merge_cost_enclosure_strength": (merge_cost.enclosure_strength),
        "merge_cost_compactness_strength": (merge_cost.compactness_strength),
        "minimum_region_size_mm": config.minimum_region_size_mm,
        "color_distance": config.color_distance,
        "parallel_quantization_enabled": (config.parallel_quantization_enabled),
        "parallel_quantization_break_even_workload": (
            config.parallel_quantization_break_even_workload
        ),
        "parallel_quantization_max_workers": (config.parallel_quantization_max_workers),
        "outline_simplification_enabled": (config.outline_simplification_enabled),
        "outline_simplification_tolerance_px": (
            config.outline_simplification_tolerance_px
        ),
        "maximum_input_pixel_count": (limits.maximum_pixel_count),
        "maximum_input_width": limits.maximum_width,
        "maximum_input_height": limits.maximum_height,
        "processing_pixel_count": (limits.processing_pixel_count),
        "font_size_pt": config.font_size_pt,
        "line_width_pt": config.line_width_pt,
        "line_color": config.line_color,
        "number_color": config.number_color,
    }

    def fake_load_config_values(
        config_file: Path,
        value_names: tuple[str, ...],
    ) -> dict[str, object]:
        assert config_file == Path(
            "config/example.toml",
        )

        return {name: fallback_values[name] for name in value_names}

    def fake_build_config(
        values: dict[str, object],
    ) -> GeneratorConfig:
        captured.update(
            values,
        )
        return config

    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        return object()

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return object()

    class FakeGeneratorApplication:
        def __init__(
            self,
            progress_reporter: object,
            quantization_executor: object | None = None,
            overlap_detector: object | None = None,
            image_loader: object | None = None,
        ) -> None:
            pass

        def generate_pdf(
            self,
            image_path: object,
            palette: object,
            config: GeneratorConfig,
            pdf_exporter: object,
        ) -> bytes:
            return b"%PDF-test"

    monkeypatch.setattr(
        cli_main,
        "load_config_values",
        fake_load_config_values,
    )
    monkeypatch.setattr(
        cli_main,
        "build_config",
        fake_build_config,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )
    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "GeneratorApplication",
        FakeGeneratorApplication,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            "config/example.toml",
            "--legend-pixels-per-inch",
            "120",
            "--legend-points-per-inch",
            "72",
            "--legend-color-field-px",
            "40",
            "--legend-column-count",
            "5",
            "--legend-rows-per-page",
            "20",
            "--legend-start-x-mm",
            "15",
            "--legend-header-y-mm",
            "400",
            "--legend-version-y-mm",
            "390",
            "--legend-table-y-mm",
            "370",
            "--legend-column-width-pt",
            "130",
            "--legend-name-offset-pt",
            "35",
            "--legend-row-height-pt",
            "45",
            "--legend-entry-font-name",
            "Courier",
            "--legend-entry-number-font-name",
            "Courier-Bold",
            "--legend-entry-font-size-pt",
            "11",
            "--legend-entry-line-height-pt",
            "12",
            "--legend-page",
            "A3",
            "--legend-orientation",
            "landscape",
            "--legend-margin-mm",
            "7.5",
        ],
    )

    cli_main.main()

    assert captured["legend_pixels_per_inch"] == 120.0
    assert captured["legend_points_per_inch"] == 72.0
    assert captured["legend_color_field_px"] == 40.0
    assert captured["legend_column_count"] == 5
    assert captured["legend_rows_per_page"] == 20
    assert captured["legend_start_x_mm"] == 15.0
    assert captured["legend_header_y_mm"] == 400.0
    assert captured["legend_version_y_mm"] == 390.0
    assert captured["legend_table_y_mm"] == 370.0
    assert captured["legend_column_width_pt"] == 130.0
    assert captured["legend_name_offset_pt"] == 35.0
    assert captured["legend_row_height_pt"] == 45.0
    assert captured["legend_entry_font_name"] == "Courier"
    assert captured["legend_entry_number_font_name"] == "Courier-Bold"
    assert captured["legend_entry_font_size_pt"] == 11
    assert captured["legend_entry_line_height_pt"] == 12.0
    assert captured["legend_page"] == "A3"
    assert captured["legend_orientation"] == "landscape"
    assert captured["legend_margin_mm"] == 7.5
