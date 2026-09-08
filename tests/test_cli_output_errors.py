# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from collections.abc import Mapping
from pathlib import Path

import pytest

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


def test_generate_reports_pdf_output_write_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    generated_pdf = b"%PDF-test"

    config = create_config(
        output_path,
    )

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
            return generated_pdf

    def fake_write_bytes(
        self: Path,
        data: bytes,
    ) -> int:
        assert self == output_path
        assert data == generated_pdf

        raise OSError(
            "Permission denied",
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
        Path,
        "write_bytes",
        fake_write_bytes,
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

    assert f"PdfExportError: Could not write PDF output: {output_path}" in captured.err


def create_region_complexity_config() -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=False,
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
    output_path: Path,
) -> GeneratorConfig:
    return GeneratorConfig(
        page="A4",
        orientation="landscape",
        placement="fit",
        margin_mm=10.0,
        palette="reference8",
        palette_version=1,
        input_image="image.jpg",
        output_pdf=str(output_path),
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
        pdf_legend=PdfLegendConfig(
            pixels_per_inch=96.0,
            points_per_inch=72.0,
            color_field_px=30.0,
            column_count=4,
            rows_per_page=17,
            start_x_mm=20.0,
            header_y_mm=285.0,
            version_y_mm=278.0,
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
        ),
    )
