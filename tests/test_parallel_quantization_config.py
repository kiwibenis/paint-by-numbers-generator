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
    parallel_quantization_enabled: object = True,
    parallel_quantization_break_even_workload: object = 360_448,
    parallel_quantization_max_workers: object = 8,
) -> dict[str, object]:
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
        "parallel_quantization_enabled": parallel_quantization_enabled,
        "parallel_quantization_break_even_workload": (
            parallel_quantization_break_even_workload
        ),
        "parallel_quantization_max_workers": (parallel_quantization_max_workers),
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


def test_parallel_quantization_values_are_required() -> None:
    values = create_complete_values()

    del values["parallel_quantization_enabled"]
    del values["parallel_quantization_break_even_workload"]
    del values["parallel_quantization_max_workers"]

    assert missing_config_values(
        values,
    ) == (
        "parallel_quantization_enabled",
        "parallel_quantization_break_even_workload",
        "parallel_quantization_max_workers",
    )


def test_build_config_preserves_parallel_quantization_values() -> None:
    config = build_config(
        create_complete_values(),
    )

    assert config.parallel_quantization_enabled is True
    assert config.parallel_quantization_break_even_workload == 360_448
    assert config.parallel_quantization_max_workers == 8


def test_build_config_accepts_disabled_parallel_quantization() -> None:
    config = build_config(
        create_complete_values(
            parallel_quantization_enabled=False,
        ),
    )

    assert config.parallel_quantization_enabled is False
    assert config.parallel_quantization_break_even_workload == 360_448
    assert config.parallel_quantization_max_workers == 8


def test_build_config_rejects_non_boolean_parallel_quantization_flag() -> None:
    with pytest.raises(
        ConfigurationError,
        match=(
            "Configuration value parallel_quantization_enabled " "must be a boolean."
        ),
    ):
        build_config(
            create_complete_values(
                parallel_quantization_enabled="true",
            ),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "parallel_quantization_break_even_workload",
        "parallel_quantization_max_workers",
    ),
)
def test_build_config_rejects_non_integer_parallel_quantization_value(
    field_name: str,
) -> None:
    values = create_complete_values()
    values[field_name] = "8"

    with pytest.raises(
        ConfigurationError,
        match=(rf"Configuration value {field_name} " r"must be an integer\."),
    ):
        build_config(
            values,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "parallel_quantization_break_even_workload",
        "parallel_quantization_max_workers",
    ),
)
def test_build_config_rejects_boolean_parallel_quantization_integer(
    field_name: str,
) -> None:
    values = create_complete_values()
    values[field_name] = True

    with pytest.raises(
        ConfigurationError,
        match=(rf"Configuration value {field_name} " r"must be an integer\."),
    ):
        build_config(
            values,
        )


@pytest.mark.parametrize(
    "value",
    (
        0,
        -1,
    ),
)
def test_validate_rejects_non_positive_parallel_break_even(
    value: int,
) -> None:
    with pytest.raises(
        ConfigurationError,
        match=(
            "parallel_quantization_break_even_workload " "must be greater than zero"
        ),
    ):
        build_config(
            create_complete_values(
                parallel_quantization_break_even_workload=value,
            ),
        )


@pytest.mark.parametrize(
    "value",
    (
        0,
        -1,
    ),
)
def test_validate_rejects_non_positive_parallel_max_workers(
    value: int,
) -> None:
    with pytest.raises(
        ConfigurationError,
        match=("parallel_quantization_max_workers " "must be greater than zero"),
    ):
        build_config(
            create_complete_values(
                parallel_quantization_max_workers=value,
            ),
        )


def test_disabled_parallel_quantization_still_requires_valid_calibration() -> None:
    with pytest.raises(
        ConfigurationError,
        match=(
            "parallel_quantization_break_even_workload " "must be greater than zero"
        ),
    ):
        build_config(
            create_complete_values(
                parallel_quantization_enabled=False,
                parallel_quantization_break_even_workload=0,
            ),
        )


def test_load_example_parallel_quantization_config() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    assert config.parallel_quantization_enabled is True
    assert config.parallel_quantization_break_even_workload == 557_056
    assert config.parallel_quantization_max_workers == 8


def test_load_parallel_quantization_values_selectively() -> None:
    values = load_config_values(
        Path("config/example.toml"),
        (
            "parallel_quantization_enabled",
            "parallel_quantization_break_even_workload",
            "parallel_quantization_max_workers",
        ),
    )

    assert values == {
        "parallel_quantization_enabled": True,
        "parallel_quantization_break_even_workload": 557_056,
        "parallel_quantization_max_workers": 8,
    }


def test_load_rejects_non_boolean_parallel_quantization_flag(
    tmp_path: Path,
) -> None:
    config_text = Path(
        "config/example.toml",
    ).read_text(
        encoding="utf-8",
    )

    config_text = config_text.replace(
        "parallel_quantization_enabled = true",
        'parallel_quantization_enabled = "true"',
        1,
    )

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        config_text,
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError,
        match=(
            "Configuration value generation."
            "parallel_quantization_enabled must be a boolean."
        ),
    ):
        load_config(
            config_file,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (
            "true",
            True,
        ),
        (
            "false",
            False,
        ),
    ),
)
def test_generate_accepts_parallel_quantization_boolean(
    value: str,
    expected: bool,
) -> None:
    args = build_parser().parse_args(
        [
            "generate",
            "--parallel-quantization-enabled",
            value,
        ],
    )

    assert args.parallel_quantization_enabled is expected


def test_generate_rejects_invalid_parallel_quantization_boolean() -> None:
    with pytest.raises(
        SystemExit,
    ):
        build_parser().parse_args(
            [
                "generate",
                "--parallel-quantization-enabled",
                "yes",
            ],
        )


def test_generate_accepts_parallel_quantization_calibration_values() -> None:
    args = build_parser().parse_args(
        [
            "generate",
            "--parallel-quantization-break-even-workload",
            "360448",
            "--parallel-quantization-max-workers",
            "8",
        ],
    )

    assert args.parallel_quantization_break_even_workload == 360_448
    assert args.parallel_quantization_max_workers == 8


def test_generate_maps_parallel_quantization_cli_values(
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
            "--parallel-quantization-enabled",
            "false",
            "--parallel-quantization-break-even-workload",
            "500000",
            "--parallel-quantization-max-workers",
            "6",
        ],
    )

    with pytest.raises(
        SystemExit,
    ):
        cli_main.main()

    assert captured["parallel_quantization_enabled"] is False
    assert captured["parallel_quantization_break_even_workload"] == 500_000
    assert captured["parallel_quantization_max_workers"] == 6
