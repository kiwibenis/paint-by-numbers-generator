# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from pbn.application.generator_config_builder import (
    build_config,
    missing_config_values,
)
from pbn.cli.main import build_parser
from pbn.exceptions import ConfigurationError
from pbn.infrastructure import load_config
from pbn.infrastructure.config_loader import load_config_values

cli_main = importlib.import_module(
    "pbn.cli.main",
)


def create_complete_values(
    *,
    legend_margin_mm: object = 5.0,
) -> dict[str, object]:
    return {
        "input_image": "input.png",
        "output_pdf": "output.pdf",
        "page": "A4",
        "orientation": "landscape",
        "placement": "fit",
        "margin_mm": 5.0,
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
        "color_distance": "delta_e_76",
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
        "legend_margin_mm": legend_margin_mm,
    }


def test_pdf_legend_margin_is_required() -> None:
    values = create_complete_values()

    del values["legend_margin_mm"]

    assert missing_config_values(
        values,
    ) == ("legend_margin_mm",)


def test_build_config_preserves_pdf_legend_margin() -> None:
    config = build_config(
        create_complete_values(
            legend_margin_mm=7.5,
        ),
    )

    assert config.pdf_legend.margin_mm == 7.5


@pytest.mark.parametrize(
    "value",
    (
        0.0,
        -1.0,
    ),
)
def test_build_config_rejects_non_positive_pdf_legend_margin(
    value: float,
) -> None:
    with pytest.raises(
        ConfigurationError,
        match=(r"pdf_legend\.margin_mm " r"must be greater than zero"),
    ):
        build_config(
            create_complete_values(
                legend_margin_mm=value,
            ),
        )


@pytest.mark.parametrize(
    "value",
    (
        float("nan"),
        float("inf"),
        float("-inf"),
    ),
)
def test_build_config_rejects_non_finite_pdf_legend_margin(
    value: float,
) -> None:
    with pytest.raises(
        ConfigurationError,
        match=r"pdf_legend\.margin_mm must be finite",
    ):
        build_config(
            create_complete_values(
                legend_margin_mm=value,
            ),
        )


def test_build_config_rejects_pdf_legend_margin_without_printable_area() -> None:
    with pytest.raises(
        ConfigurationError,
        match=(r"pdf_legend\.margin_mm " r"must leave a positive printable area"),
    ):
        build_config(
            create_complete_values(
                legend_margin_mm=105.0,
            ),
        )


def test_load_example_preserves_pdf_legend_margin() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    assert config.pdf_legend.margin_mm == 5.0


def test_load_pdf_legend_margin_selectively() -> None:
    values = load_config_values(
        Path("config/example.toml"),
        ("legend_margin_mm",),
    )

    assert values == {
        "legend_margin_mm": 5.0,
    }


def test_generate_accepts_pdf_legend_margin() -> None:
    args = build_parser().parse_args(
        [
            "generate",
            "--legend-margin-mm",
            "7.5",
        ],
    )

    assert args.legend_margin_mm == 7.5


def test_generate_maps_pdf_legend_margin_cli_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_missing_config_values(
        values: dict[str, object],
    ) -> tuple[str, ...]:
        return ()

    def fake_build_config(
        values: dict[str, object],
    ) -> None:
        captured.update(
            values,
        )

        raise ConfigurationError(
            "Stop after configuration mapping.",
        )

    monkeypatch.setattr(
        cli_main,
        "missing_config_values",
        fake_missing_config_values,
    )
    monkeypatch.setattr(
        cli_main,
        "build_config",
        fake_build_config,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--legend-margin-mm",
            "7.5",
        ],
    )

    with pytest.raises(
        SystemExit,
    ):
        cli_main.main()

    assert captured["legend_margin_mm"] == 7.5
