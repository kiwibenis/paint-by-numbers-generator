# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from pbn.config import GeneratorConfig
from tests.fake_image_loader import loader_class_for

cli_main = importlib.import_module(
    "pbn.cli.main",
)


def complete_toml(
    output_path: Path,
    *,
    include_output_pdf: bool = True,
    include_line_width_pt: bool = True,
    page_value: str = '"A4"',
    margin_mm: float = 10.0,
) -> str:
    output_pdf_line = ""

    if include_output_pdf:
        output_pdf_line = f'output_pdf = "{output_path.as_posix()}"\n'

    line_width_line = ""

    if include_line_width_pt:
        line_width_line = "line_width_pt = 0.4\n"

    return (
        "[input]\n"
        'palette = "reference8"\n'
        "palette_version = 1\n"
        'input_image = "image.jpg"\n'
        "\n"
        "[generation]\n"
        "region_complexity_reduction_enabled = true\n"
        "max_regions = 350\n"
        "maximum_merge_cost = 0.300\n"
        "merge_cost_color_weight = 0.40\n"
        "merge_cost_affected_area_weight = 0.25\n"
        "merge_cost_border_weight = 0.15\n"
        "merge_cost_geometry_weight = 0.20\n"
        "merge_cost_enclosure_strength = 0.50\n"
        "merge_cost_compactness_strength = 0.15\n"
        "minimum_region_size_mm = 3.0\n"
        'color_distance = "delta_e_76"\n'
        "parallel_quantization_enabled = true\n"
        "parallel_quantization_break_even_workload = 360448\n"
        "parallel_quantization_max_workers = 8\n"
        "outline_simplification_enabled = true\n"
        "outline_simplification_tolerance_px = 1.0\n"
        "\n"
        "[input_limits]\n"
        "maximum_pixel_count = 50000000\n"
        "maximum_width = 20000\n"
        "maximum_height = 20000\n"
        "processing_pixel_count = 1600000\n"
        "\n"
        "[output]\n"
        f"page = {page_value}\n"
        'orientation = "landscape"\n'
        'placement = "fit"\n'
        f"margin_mm = {margin_mm}\n"
        f"{output_pdf_line}"
        "font_size_pt = 9\n"
        f"{line_width_line}"
        'line_color = "#000000"\n'
        'number_color = "#000000"\n'
        "\n"
        "[pdf_legend]\n"
        "pixels_per_inch = 96.0\n"
        "points_per_inch = 72.0\n"
        "color_field_px = 30.0\n"
        "column_count = 4\n"
        "rows_per_page = 17\n"
        "start_x_mm = 20.0\n"
        "header_y_mm = 285.0\n"
        "version_y_mm = 278.0\n"
        "table_y_mm = 265.0\n"
        "column_width_pt = 118.0\n"
        "name_offset_pt = 30.0\n"
        "row_height_pt = 42.5\n"
        'entry_font_name = "Helvetica"\n'
        'entry_number_font_name = "Helvetica-Bold"\n'
        "entry_font_size_pt = 9\n"
        "entry_line_height_pt = 9.0\n"
        'page = "A4"\n'
        'orientation = "portrait"\n'
        "margin_mm = 5.0\n"
    )


def complete_cli_args(
    output_path: Path,
) -> list[str]:
    return [
        "--input",
        "image.jpg",
        "--output",
        str(output_path),
        "--page",
        "A4",
        "--orientation",
        "landscape",
        "--placement",
        "fit",
        "--margin-mm",
        "10.0",
        "--palette",
        "reference8",
        "--palette-version",
        "1",
        "--region-complexity-reduction-enabled",
        "true",
        "--max-regions",
        "350",
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
        "--minimum-region-size-mm",
        "3.0",
        "--color-distance",
        "delta_e_76",
        "--parallel-quantization-enabled",
        "true",
        "--parallel-quantization-break-even-workload",
        "360448",
        "--parallel-quantization-max-workers",
        "8",
        "--outline-simplification-enabled",
        "true",
        "--outline-simplification-tolerance-px",
        "1.0",
        "--maximum-input-pixel-count",
        "50000000",
        "--maximum-input-width",
        "20000",
        "--maximum-input-height",
        "20000",
        "--processing-pixel-count",
        "1600000",
        "--font-size-pt",
        "9",
        "--line-width-pt",
        "0.4",
        "--line-color",
        "#000000",
        "--number-color",
        "#000000",
        "--legend-pixels-per-inch",
        "96",
        "--legend-points-per-inch",
        "72",
        "--legend-color-field-px",
        "30",
        "--legend-column-count",
        "4",
        "--legend-rows-per-page",
        "17",
        "--legend-start-x-mm",
        "20",
        "--legend-header-y-mm",
        "285",
        "--legend-version-y-mm",
        "278",
        "--legend-table-y-mm",
        "265",
        "--legend-column-width-pt",
        "118",
        "--legend-name-offset-pt",
        "30",
        "--legend-row-height-pt",
        "42.5",
        "--legend-entry-font-name",
        "Helvetica",
        "--legend-entry-number-font-name",
        "Helvetica-Bold",
        "--legend-entry-font-size-pt",
        "9",
        "--legend-entry-line-height-pt",
        "9",
        "--legend-page",
        "A4",
        "--legend-orientation",
        "portrait",
        "--legend-margin-mm",
        "5.0",
    ]


def write_config(
    tmp_path: Path,
    content: str,
) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        content,
        encoding="utf-8",
    )
    return config_file


def install_generation_fakes(
    monkeypatch: pytest.MonkeyPatch,
    captured: dict[str, object],
) -> None:
    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        captured["image_path"] = image_path
        return object()

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            captured["palette_id"] = palette_id
            captured["palette_version"] = version
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
            captured["config"] = config
            return b"%PDF-test"

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


def test_generate_accepts_complete_toml_without_cli_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.page == "A4"
    assert config.margin_mm == 10.0
    assert config.line_color == "#000000"
    assert config.number_color == "#000000"
    assert config.pdf_legend.margin_mm == 5.0
    assert config.color_distance == "delta_e_76"
    assert config.region_complexity.reduction_enabled is True
    assert config.region_complexity.max_regions == 350
    assert config.region_complexity.maximum_merge_cost == 0.300
    assert config.region_complexity.merge_cost.color_weight == 0.40
    assert config.region_complexity.merge_cost.affected_area_weight == 0.25
    assert config.region_complexity.merge_cost.border_weight == 0.15
    assert config.region_complexity.merge_cost.geometry_weight == 0.20
    assert config.region_complexity.merge_cost.enclosure_strength == 0.50
    assert config.region_complexity.merge_cost.compactness_strength == 0.15
    assert config.parallel_quantization_enabled is True
    assert config.parallel_quantization_break_even_workload == 360_448
    assert config.parallel_quantization_max_workers == 8
    assert output_path.read_bytes() == b"%PDF-test"


def test_generate_completes_partial_toml_with_cli_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
            include_output_pdf=False,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--output",
            str(output_path),
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.output_pdf == str(output_path)
    assert output_path.read_bytes() == b"%PDF-test"


def test_generate_accepts_complete_cli_without_toml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            *complete_cli_args(
                output_path,
            ),
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.input_image == "image.jpg"
    assert config.output_pdf == str(output_path)
    assert config.page == "A4"
    assert config.margin_mm == 10.0
    assert config.color_distance == "delta_e_76"
    assert config.region_complexity.reduction_enabled is True
    assert config.region_complexity.max_regions == 350
    assert config.region_complexity.maximum_merge_cost == 0.300
    assert config.region_complexity.merge_cost.color_weight == 0.40
    assert config.region_complexity.merge_cost.affected_area_weight == 0.25
    assert config.region_complexity.merge_cost.border_weight == 0.15
    assert config.region_complexity.merge_cost.geometry_weight == 0.20
    assert config.region_complexity.merge_cost.enclosure_strength == 0.50
    assert config.region_complexity.merge_cost.compactness_strength == 0.15
    assert config.parallel_quantization_enabled is True
    assert config.parallel_quantization_break_even_workload == 360_448
    assert config.parallel_quantization_max_workers == 8
    assert config.outline_simplification_enabled is True
    assert config.outline_simplification_tolerance_px == 1.0
    assert config.line_color == "#000000"
    assert config.number_color == "#000000"
    assert config.pdf_legend.entry_font_size_pt == 9
    assert config.pdf_legend.margin_mm == 5.0
    assert output_path.read_bytes() == b"%PDF-test"


def test_generate_rejects_incomplete_combined_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
            include_output_pdf=False,
            include_line_width_pt=False,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0
    assert "config" not in captured

    stderr = capsys.readouterr().err

    assert "ConfigurationError:" in stderr


def test_generate_uses_cli_value_over_toml_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--page",
            "A3",
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.page == "A3"


def test_generate_uses_cli_margin_over_toml_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
            margin_mm=10.0,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--margin-mm",
            "12.5",
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.margin_mm == 12.5


def test_generate_uses_cli_color_distance_over_toml_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--color-distance",
            "delta_e_2000",
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.color_distance == "delta_e_2000"


def test_generate_ignores_invalid_toml_value_overridden_by_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
            page_value="123",
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--page",
            "A3",
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.page == "A3"


def test_generate_rejects_invalid_cli_value_even_when_toml_is_valid(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    config_file = write_config(
        tmp_path,
        complete_toml(
            output_path,
        ),
    )

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(config_file),
            "--page",
            "A5",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0
    assert "config" not in captured

    stderr = capsys.readouterr().err

    assert "Unsupported page size: A5" in stderr


def test_generate_does_not_load_toml_when_cli_is_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    missing_config_file = tmp_path / "missing.toml"

    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            *complete_cli_args(
                output_path,
            ),
            "--config_file",
            str(missing_config_file),
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert config.output_pdf == str(output_path)
    assert output_path.read_bytes() == b"%PDF-test"


def test_generate_rejects_incomplete_cli_without_toml(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--input",
            "image.jpg",
            "--output",
            "output.pdf",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0
    assert "config" not in captured

    stderr = capsys.readouterr().err

    assert "ConfigurationError:" in stderr
