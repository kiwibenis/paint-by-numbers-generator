# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from collections.abc import Mapping
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
from pbn.exceptions import (
    ConfigurationError,
    ImageNotFoundError,
    InvalidPaletteError,
    PaletteNotFoundError,
    UnsupportedImageFormatError,
)
from tests.fake_image_loader import loader_class_for

cli_main = importlib.import_module(
    "pbn.cli.main",
)


def create_pdf_legend_config() -> PdfLegendConfig:
    return PdfLegendConfig(
        pixels_per_inch=96.0,
        points_per_inch=72.0,
        color_field_px=30.0,
        column_count=4,
        rows_per_page=17,
        start_x_mm=20.0,
        header_y_mm=284.0,
        version_y_mm=284.0,
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
        margin_mm=10.0,
    )


def create_region_complexity_config(
    *,
    max_regions: int = 350,
) -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=max_regions,
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
    *,
    tmp_path: Path,
    page: str = "A4",
    orientation: str = "landscape",
    placement: str = "fit",
    margin_mm: float = 10.0,
    palette: str = "reference8",
    palette_version: int = 1,
    input_image: str = "image.jpg",
    output_pdf: str | None = None,
    max_regions: int = 350,
    minimum_region_size_mm: float = 3.0,
    color_distance: str = "delta_e_76",
    parallel_quantization_enabled: bool = True,
    parallel_quantization_break_even_workload: int = 360_448,
    parallel_quantization_max_workers: int = 8,
    font_size_pt: int = 9,
    line_width_pt: float = 0.4,
    line_color: str = "#000000",
    number_color: str = "#000000",
) -> GeneratorConfig:
    return GeneratorConfig(
        page=page,
        orientation=orientation,
        placement=placement,
        margin_mm=margin_mm,
        palette=palette,
        palette_version=palette_version,
        input_image=input_image,
        output_pdf=(
            output_pdf if output_pdf is not None else str(tmp_path / "output.pdf")
        ),
        region_complexity=create_region_complexity_config(
            max_regions=max_regions,
        ),
        image_input_limits=ImageInputLimitsConfig(
            maximum_pixel_count=50_000_000,
            maximum_width=20_000,
            maximum_height=20_000,
            processing_pixel_count=1_600_000,
        ),
        minimum_region_size_mm=minimum_region_size_mm,
        color_distance=color_distance,
        parallel_quantization_enabled=(parallel_quantization_enabled),
        parallel_quantization_break_even_workload=(
            parallel_quantization_break_even_workload
        ),
        parallel_quantization_max_workers=(parallel_quantization_max_workers),
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.0,
        font_size_pt=font_size_pt,
        line_width_pt=line_width_pt,
        line_color=line_color,
        number_color=number_color,
        pdf_legend=create_pdf_legend_config(),
    )


def config_values(
    config: GeneratorConfig,
) -> dict[str, object]:
    complexity = config.region_complexity
    merge_cost = complexity.merge_cost
    limits = config.image_input_limits
    legend = config.pdf_legend

    return {
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
        "legend_pixels_per_inch": legend.pixels_per_inch,
        "legend_points_per_inch": legend.points_per_inch,
        "legend_color_field_px": legend.color_field_px,
        "legend_column_count": legend.column_count,
        "legend_rows_per_page": legend.rows_per_page,
        "legend_start_x_mm": legend.start_x_mm,
        "legend_header_y_mm": legend.header_y_mm,
        "legend_version_y_mm": legend.version_y_mm,
        "legend_table_y_mm": legend.table_y_mm,
        "legend_column_width_pt": legend.column_width_pt,
        "legend_name_offset_pt": legend.name_offset_pt,
        "legend_row_height_pt": legend.row_height_pt,
        "legend_entry_font_name": legend.entry_font_name,
        "legend_entry_number_font_name": legend.entry_number_font_name,
        "legend_entry_font_size_pt": legend.entry_font_size_pt,
        "legend_entry_line_height_pt": legend.entry_line_height_pt,
        "legend_page": legend.page,
        "legend_orientation": legend.orientation,
        "legend_margin_mm": legend.margin_mm,
    }


def install_resolved_config(
    monkeypatch: pytest.MonkeyPatch,
    config: GeneratorConfig,
) -> None:
    def fake_missing_config_values(
        values: Mapping[str, object],
    ) -> tuple[str, ...]:
        return ()

    def fake_build_config(
        values: Mapping[str, object],
    ) -> GeneratorConfig:
        return config

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


def test_generate_writes_generated_pdf_to_output_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "result.pdf"
    generated_pdf = b"generated-pdf"
    config = create_config(
        tmp_path=tmp_path,
        output_pdf=str(output_path),
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return object()

    def fake_load_image(
        image_path: Path,
        limits: object = None,
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
            return generated_pdf

    class FakePdfExporter:
        pass

    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )
    monkeypatch.setattr(
        cli_main,
        "GeneratorApplication",
        FakeGeneratorApplication,
    )
    monkeypatch.setattr(
        cli_main,
        "PdfExporter",
        FakePdfExporter,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    cli_main.main()

    assert output_path.read_bytes() == generated_pdf


def test_generate_invokes_generator_application(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "result.pdf"
    config = create_config(
        tmp_path=tmp_path,
        output_pdf=str(output_path),
    )

    loaded_image = object()
    loaded_palette = object()

    captured: dict[str, object] = {}

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return loaded_palette

    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        return loaded_image

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
            captured["image_path"] = image_path
            captured["palette"] = palette
            captured["config"] = config
            captured["pdf_exporter"] = pdf_exporter
            return b"pdf"

    class FakePdfExporter:
        pass

    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )
    monkeypatch.setattr(
        cli_main,
        "GeneratorApplication",
        FakeGeneratorApplication,
    )
    monkeypatch.setattr(
        cli_main,
        "PdfExporter",
        FakePdfExporter,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    cli_main.main()

    assert captured["image_path"] == Path(
        config.input_image,
    )
    assert captured["palette"] is loaded_palette
    assert captured["config"] is config
    assert isinstance(
        captured["pdf_exporter"],
        FakePdfExporter,
    )


def test_generate_combines_cli_values_with_config_file_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "cli-output.pdf"

    base_config = create_config(
        tmp_path=tmp_path,
    )
    resolved_config = create_config(
        tmp_path=tmp_path,
        page="A3",
        orientation="portrait",
        placement="crop",
        margin_mm=12.5,
        palette="polychromos60",
        palette_version=1,
        input_image="cli-image.jpg",
        output_pdf=str(output_path),
        max_regions=500,
        minimum_region_size_mm=4.0,
        color_distance="delta_e_2000",
        font_size_pt=12,
        line_width_pt=0.6,
        line_color="#123456",
        number_color="#ABCDEF",
    )

    base_values = config_values(
        base_config,
    )
    captured: dict[str, object] = {}

    def fake_load_config_values(
        config_file: Path,
        value_names: tuple[str, ...],
    ) -> dict[str, object]:
        captured["config_file"] = config_file
        return {name: base_values[name] for name in value_names}

    def fake_build_config(
        values: Mapping[str, object],
    ) -> GeneratorConfig:
        captured["values"] = dict(values)
        return resolved_config

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

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return object()

    def fake_load_image(
        image_path: Path,
        limits: object = None,
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
            return b"pdf"

    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
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
            "--input",
            "cli-image.jpg",
            "--output",
            "cli-output.pdf",
            "--page",
            "A3",
            "--orientation",
            "portrait",
            "--placement",
            "crop",
            "--margin-mm",
            "12.5",
            "--palette",
            "polychromos60",
            "--palette-version",
            "1",
            "--max-regions",
            "500",
            "--minimum-region-size-mm",
            "4.0",
            "--color-distance",
            "delta_e_2000",
            "--font-size-pt",
            "12",
            "--line-width-pt",
            "0.6",
            "--line-color",
            "#123456",
            "--number-color",
            "#ABCDEF",
        ],
    )

    cli_main.main()

    assert captured["config_file"] == Path(
        "config/example.toml",
    )

    values = captured["values"]

    assert isinstance(
        values,
        dict,
    )
    assert values["input_image"] == "cli-image.jpg"
    assert values["output_pdf"] == "cli-output.pdf"
    assert values["page"] == "A3"
    assert values["orientation"] == "portrait"
    assert values["placement"] == "crop"
    assert values["margin_mm"] == 12.5
    assert values["palette"] == "polychromos60"
    assert values["palette_version"] == 1
    assert values["region_complexity_reduction_enabled"] is True
    assert values["max_regions"] == 500
    assert values["maximum_merge_cost"] == 0.300
    assert values["merge_cost_color_weight"] == 0.40
    assert values["merge_cost_affected_area_weight"] == 0.25
    assert values["merge_cost_border_weight"] == 0.15
    assert values["merge_cost_geometry_weight"] == 0.20
    assert values["merge_cost_enclosure_strength"] == 0.50
    assert values["merge_cost_compactness_strength"] == 0.15
    assert values["minimum_region_size_mm"] == 4.0
    assert values["color_distance"] == "delta_e_2000"
    assert values["parallel_quantization_enabled"] is True
    assert values["parallel_quantization_break_even_workload"] == 360_448
    assert values["parallel_quantization_max_workers"] == 8
    assert values["font_size_pt"] == 12
    assert values["line_width_pt"] == 0.6
    assert values["line_color"] == "#123456"
    assert values["number_color"] == "#ABCDEF"
    assert values["legend_margin_mm"] == 10.0


def test_generate_resolves_palette_from_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "test-output.pdf"

    config = create_config(
        tmp_path=tmp_path,
        output_pdf=str(output_path),
    )

    captured: dict[str, object] = {}

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            captured["palette_id"] = palette_id
            captured["version"] = version
            return object()

    def fake_load_image(
        image_path: Path,
        limits: object = None,
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
            return b"pdf"

    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
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
        ],
    )

    cli_main.main()

    assert captured["palette_id"] == "reference8"
    assert captured["version"] == 1


def test_generate_loads_input_image_from_resolved_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "test-output.pdf"

    config = create_config(
        tmp_path=tmp_path,
        input_image="cli-image.jpg",
        output_pdf=str(output_path),
    )

    captured: dict[str, object] = {}

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return object()

    def fake_load_image(
        image_path: Path,
        limits: object = None,
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
            captured["image_path"] = image_path
            return b"pdf"

    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
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
        ],
    )

    cli_main.main()

    assert captured["image_path"] == Path(
        "cli-image.jpg",
    )


def test_generate_accepts_all_generation_parameters() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "generate",
            "--input",
            "image.jpg",
            "--output",
            "result.pdf",
            "--page",
            "A3",
            "--orientation",
            "portrait",
            "--placement",
            "crop",
            "--margin-mm",
            "12.5",
            "--palette",
            "polychromos60",
            "--palette-version",
            "1",
            "--region-complexity-reduction-enabled",
            "false",
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
            "--minimum-region-size-mm",
            "4.0",
            "--color-distance",
            "delta_e_2000",
            "--parallel-quantization-enabled",
            "false",
            "--parallel-quantization-break-even-workload",
            "500000",
            "--parallel-quantization-max-workers",
            "6",
            "--outline-simplification-enabled",
            "false",
            "--outline-simplification-tolerance-px",
            "2.5",
            "--font-size-pt",
            "12",
            "--line-width-pt",
            "0.6",
            "--line-color",
            "#123456",
            "--number-color",
            "#ABCDEF",
            "--config_file",
            "config/example.toml",
        ],
    )

    assert args.command == "generate"
    assert args.input == "image.jpg"
    assert args.output == "result.pdf"
    assert args.page == "A3"
    assert args.orientation == "portrait"
    assert args.placement == "crop"
    assert args.margin_mm == 12.5
    assert args.palette == "polychromos60"
    assert args.palette_version == 1
    assert args.region_complexity_reduction_enabled is False
    assert args.max_regions == 500
    assert args.maximum_merge_cost == 0.300
    assert args.merge_cost_color_weight == 0.40
    assert args.merge_cost_affected_area_weight == 0.25
    assert args.merge_cost_border_weight == 0.15
    assert args.merge_cost_geometry_weight == 0.20
    assert args.merge_cost_enclosure_strength == 0.50
    assert args.merge_cost_compactness_strength == 0.15
    assert args.minimum_region_size_mm == 4.0
    assert args.color_distance == "delta_e_2000"
    assert args.parallel_quantization_enabled is False
    assert args.parallel_quantization_break_even_workload == 500_000
    assert args.parallel_quantization_max_workers == 6
    assert args.outline_simplification_enabled is False
    assert args.outline_simplification_tolerance_px == 2.5
    assert args.font_size_pt == 12
    assert args.line_width_pt == 0.6
    assert args.line_color == "#123456"
    assert args.number_color == "#ABCDEF"
    assert args.config_file == "config/example.toml"


def test_generate_command_exists() -> None:
    parser = build_parser()

    args = parser.parse_args(
        ["generate"],
    )

    assert args.command == "generate"


def test_generate_accepts_input_and_output() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "generate",
            "--input",
            "image.jpg",
            "--output",
            "result.pdf",
        ],
    )

    assert args.command == "generate"
    assert args.input == "image.jpg"
    assert args.output == "result.pdf"


def test_generate_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(
            [
                "generate",
                "--help",
            ],
        )

    assert exc_info.value.code == 0

    captured = capsys.readouterr()

    assert "usage:" in captured.out
    assert "--input" in captured.out
    assert "--output" in captured.out
    assert "--margin-mm" in captured.out
    assert "--line-color" in captured.out
    assert "--number-color" in captured.out
    assert "--legend-margin-mm" in captured.out
    assert "--region-complexity-reduction-enabled" in captured.out
    assert "--max-regions" in captured.out
    assert "--maximum-merge-cost" in captured.out
    assert "--merge-cost-color-weight" in captured.out
    assert "--merge-cost-affected-area-weight" in captured.out
    assert "--merge-cost-border-weight" in captured.out
    assert "--merge-cost-geometry-weight" in captured.out
    assert "--merge-cost-enclosure-strength" in captured.out
    assert "--merge-cost-compactness-strength" in captured.out
    assert "--color-distance" in captured.out
    assert "--parallel-quantization-enabled" in captured.out
    assert "--parallel-quantization-break-even-workload" in captured.out
    assert "--parallel-quantization-max-workers" in captured.out
    assert "--outline-simplification-enabled" in captured.out
    assert "--outline-simplification-tolerance-px" in captured.out


def test_generate_accepts_config_file() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "generate",
            "--config_file",
            "config/example.toml",
        ],
    )

    assert args.command == "generate"
    assert args.config_file == "config/example.toml"


def test_generate_loads_config_file_when_cli_is_incomplete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "test-output.pdf"

    config = create_config(
        tmp_path=tmp_path,
        input_image="config-image.jpg",
        output_pdf=str(output_path),
    )

    captured: dict[str, object] = {}

    def fake_load_config_values(
        config_file: Path,
        value_names: tuple[str, ...],
    ) -> dict[str, object]:
        captured["config_file"] = config_file
        captured["value_names"] = value_names
        return {}

    def fake_build_config(
        values: Mapping[str, object],
    ) -> GeneratorConfig:
        return config

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

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return object()

    def fake_load_image(
        image_path: Path,
        limits: object = None,
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
            return b"pdf"

    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
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
        ],
    )

    cli_main.main()

    assert captured["config_file"] == Path(
        "config/example.toml",
    )
    assert captured["value_names"]


def test_generate_creates_pdf_with_real_components(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "generated.pdf"

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            "config/example.toml",
            "--output",
            str(output_path),
        ],
    )

    cli_main.main()

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_validates_resolved_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "result.pdf"
    config = create_config(
        tmp_path=tmp_path,
        output_pdf=str(output_path),
    )

    captured: dict[str, object] = {}

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            captured["config"] = config_value

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
            return b"pdf"

    class FakePdfExporter:
        pass

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
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
        cli_main,
        "PdfExporter",
        FakePdfExporter,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    cli_main.main()

    assert captured["config"] is config


def test_generate_reports_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path=tmp_path,
    )

    config_error = ConfigurationError(
        "region_complexity.max_regions must be greater than zero.",
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            raise config_error

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0

    captured = capsys.readouterr()

    assert "region_complexity.max_regions must be greater than zero." in captured.err


def test_generate_reports_image_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    image_error = ImageNotFoundError(
        "Image does not exist: image.jpg",
    )

    config = create_config(
        tmp_path=tmp_path,
        input_image="image.jpg",
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            return None

    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        raise image_error

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0

    captured = capsys.readouterr()

    assert "Image does not exist: image.jpg" in captured.err


def test_generate_reports_unsupported_image_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    image_error = UnsupportedImageFormatError(
        "Unsupported image format: .xyz",
    )

    config = create_config(
        tmp_path=tmp_path,
        input_image="image.xyz",
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            return None

    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        raise image_error

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
    )
    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0

    captured = capsys.readouterr()

    assert "Unsupported image format: .xyz" in captured.err


def test_generate_reports_palette_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    palette_error = PaletteNotFoundError(
        "Palette not found: reference8-v1.json",
    )

    config = create_config(
        tmp_path=tmp_path,
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        return object()

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            return None

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            raise palette_error

    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )
    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
    )
    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0

    captured = capsys.readouterr()

    assert "PaletteNotFoundError: Palette not found: reference8-v1.json" in (
        captured.err
    )


def test_generate_reports_invalid_palette_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    palette_error = InvalidPaletteError(
        "Palette file is invalid.",
    )

    config = create_config(
        tmp_path=tmp_path,
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            return None

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
            raise palette_error

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
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
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0

    captured = capsys.readouterr()

    assert "InvalidPaletteError: Palette file is invalid." in captured.err


def test_progress_reporter_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reporter = cli_main.ConsoleProgressReporter()

    reporter.report(
        "Generating paint-by-numbers document.",
    )

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ("Generating paint-by-numbers document.\n")


def test_generate_passes_progress_reporter_to_application(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "result.pdf"
    config = create_config(
        tmp_path=tmp_path,
        output_pdf=str(output_path),
    )

    captured: dict[str, object] = {}

    install_resolved_config(
        monkeypatch,
        config,
    )

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

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            return None

    class FakeGeneratorApplication:
        def __init__(
            self,
            progress_reporter: object,
            quantization_executor: object | None = None,
            overlap_detector: object | None = None,
            image_loader: object | None = None,
        ) -> None:
            captured["progress_reporter"] = progress_reporter

        def generate_pdf(
            self,
            image_path: object,
            palette: object,
            config: GeneratorConfig,
            pdf_exporter: object,
        ) -> bytes:
            return b"pdf"

    class FakePdfExporter:
        pass

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
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
        cli_main,
        "PdfExporter",
        FakePdfExporter,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    cli_main.main()

    assert isinstance(
        captured["progress_reporter"],
        cli_main.ConsoleProgressReporter,
    )


def test_generate_hands_its_progress_reporter_to_the_application(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path=tmp_path,
    )

    install_resolved_config(
        monkeypatch,
        config,
    )

    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        return object()

    class FakeGeneratorConfigValidator:
        def validate(
            self,
            config_value: GeneratorConfig,
        ) -> None:
            return None

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            return object()

    captured: dict[str, object] = {}

    class FakeGeneratorApplication:
        def __init__(
            self,
            progress_reporter: object,
            quantization_executor: object | None = None,
            overlap_detector: object | None = None,
            image_loader: object | None = None,
        ) -> None:
            captured["progress_reporter"] = progress_reporter
            captured["image_loader"] = image_loader

        def generate_pdf(
            self,
            image_path: object,
            palette: object,
            config: GeneratorConfig,
            pdf_exporter: object,
        ) -> bytes:
            return b"pdf"

    class FakePdfExporter:
        pass

    monkeypatch.setattr(
        cli_main,
        "GeneratorConfigValidator",
        FakeGeneratorConfigValidator,
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
        cli_main,
        "PdfExporter",
        FakePdfExporter,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
        ],
    )

    cli_main.main()

    # Loading moved behind the application boundary, so the message is
    # asserted there. What remains the command line's responsibility is
    # handing over a reporter that can emit it.
    assert captured["progress_reporter"] is not None
