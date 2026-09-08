# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import pytest

from pbn.application import generator_application
from pbn.application.generator_application import GeneratorApplication
from pbn.application.quantization_executor_port import (
    COLOR_BYTES,
    QuantizationChunk,
    QuantizationChunkResult,
)
from pbn.color import ImageQuantizer
from pbn.color.color_distance import ColorDistance
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
    QuantizedImage,
    VectorDocument,
)
from pbn.pipeline import PaintByNumbersGenerator
from tests.fake_image_loader import FakeImageLoader
from tests.fake_overlap_detector import FakeOverlapDetector


class Quantizer(Protocol):
    def quantize(
        self,
        image: InputImage,
        palette: Palette,
    ) -> QuantizedImage: ...


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
    *,
    color_distance: str = "delta_e_2000",
    parallel_quantization_enabled: bool = True,
    parallel_quantization_break_even_workload: int = 360_448,
    parallel_quantization_max_workers: int = 8,
) -> GeneratorConfig:
    return GeneratorConfig(
        page="A4",
        orientation="landscape",
        placement="fit",
        margin_mm=10.0,
        palette="reference8",
        palette_version=1,
        input_image="input.png",
        output_pdf="output.pdf",
        region_complexity=create_region_complexity_config(),
        image_input_limits=ImageInputLimitsConfig(
            maximum_pixel_count=50_000_000,
            maximum_width=20_000,
            maximum_height=20_000,
            processing_pixel_count=1_600_000,
        ),
        minimum_region_size_mm=3.0,
        color_distance=color_distance,
        parallel_quantization_enabled=parallel_quantization_enabled,
        parallel_quantization_break_even_workload=(
            parallel_quantization_break_even_workload
        ),
        parallel_quantization_max_workers=parallel_quantization_max_workers,
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
            page="A3",
            orientation="portrait",
            margin_mm=5.0,
        ),
    )


def create_image() -> InputImage:
    return InputImage.from_rows(
        (
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
            ),
        ),
    )


def create_palette() -> Palette:
    black = PaletteColor(
        number=1,
        name="Black",
        rgb=RGB(
            red=0,
            green=0,
            blue=0,
        ),
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(black,),
    )


def test_generate_injects_parallel_quantizer_when_executor_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config(
        parallel_quantization_break_even_workload=500_000,
    )

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object] = {}

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            return ()

    class FakeParallelImageQuantizer:
        def __init__(
            self,
            color_distance: ColorDistance,
            executor: FakeExecutor,
            worker_count: int,
            break_even_workload: int | None = None,
        ) -> None:
            captured["parallel_color_distance"] = color_distance
            captured["executor"] = executor
            captured["worker_count"] = worker_count
            captured["break_even_workload"] = break_even_workload

    def fake_cpu_count() -> int:
        return 4

    def fake_generator_init(
        self: PaintByNumbersGenerator,
        color_distance: ColorDistance | None = None,
        quantizer: object | None = None,
        complexity_reducer: object | None = None,
        overlap_detector: object | None = None,
        *,
        outline_simplification_enabled: bool,
        outline_simplification_tolerance_px: float,
    ) -> None:
        captured["generator_color_distance"] = color_distance
        captured["quantizer"] = quantizer

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    monkeypatch.setattr(
        os,
        "cpu_count",
        fake_cpu_count,
    )
    monkeypatch.setattr(
        generator_application,
        "ParallelImageQuantizer",
        FakeParallelImageQuantizer,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "__init__",
        fake_generator_init,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    executor = FakeExecutor()

    application = GeneratorApplication(
        quantization_executor=executor,
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["executor"] is executor
    assert captured["worker_count"] == 4
    assert captured["break_even_workload"] == 500_000
    assert captured["parallel_color_distance"] is captured["generator_color_distance"]
    assert isinstance(
        captured["quantizer"],
        FakeParallelImageQuantizer,
    )


def test_generate_caps_parallel_workers_by_configured_maximum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config(
        parallel_quantization_max_workers=3,
    )

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object] = {}

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            return ()

    class FakeParallelImageQuantizer:
        def __init__(
            self,
            color_distance: ColorDistance,
            executor: FakeExecutor,
            worker_count: int,
            break_even_workload: int | None = None,
        ) -> None:
            captured["worker_count"] = worker_count

    def fake_cpu_count() -> int:
        return 12

    def fake_generator_init(
        self: PaintByNumbersGenerator,
        color_distance: ColorDistance | None = None,
        quantizer: object | None = None,
        complexity_reducer: object | None = None,
        overlap_detector: object | None = None,
        *,
        outline_simplification_enabled: bool,
        outline_simplification_tolerance_px: float,
    ) -> None:
        pass

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    monkeypatch.setattr(
        os,
        "cpu_count",
        fake_cpu_count,
    )
    monkeypatch.setattr(
        generator_application,
        "ParallelImageQuantizer",
        FakeParallelImageQuantizer,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "__init__",
        fake_generator_init,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        quantization_executor=FakeExecutor(),
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["worker_count"] == 3


def test_generate_uses_sequential_quantizer_when_parallel_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config(
        parallel_quantization_enabled=False,
    )

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object | None] = {}

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            raise AssertionError(
                "Parallel executor must not be used when disabled.",
            )

    class FakeParallelImageQuantizer:
        def __init__(
            self,
            color_distance: ColorDistance,
            executor: FakeExecutor,
            worker_count: int,
            break_even_workload: int | None = None,
        ) -> None:
            raise AssertionError(
                "Parallel quantizer must not be created when disabled.",
            )

    def fake_generator_init(
        self: PaintByNumbersGenerator,
        color_distance: ColorDistance | None = None,
        quantizer: object | None = None,
        complexity_reducer: object | None = None,
        overlap_detector: object | None = None,
        *,
        outline_simplification_enabled: bool,
        outline_simplification_tolerance_px: float,
    ) -> None:
        captured["quantizer"] = quantizer

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    monkeypatch.setattr(
        generator_application,
        "ParallelImageQuantizer",
        FakeParallelImageQuantizer,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "__init__",
        fake_generator_init,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        quantization_executor=FakeExecutor(),
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["quantizer"] is None


def test_generate_uses_sequential_quantizer_for_delta_e_76(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config(
        color_distance="delta_e_76",
    )

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object | None] = {}

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            raise AssertionError(
                "Parallel executor must not be used for Delta E 76.",
            )

    class FakeParallelImageQuantizer:
        def __init__(
            self,
            color_distance: ColorDistance,
            executor: FakeExecutor,
            worker_count: int,
            break_even_workload: int | None = None,
        ) -> None:
            raise AssertionError(
                "Parallel quantizer must not be created for Delta E 76.",
            )

    def fake_generator_init(
        self: PaintByNumbersGenerator,
        color_distance: ColorDistance | None = None,
        quantizer: object | None = None,
        complexity_reducer: object | None = None,
        overlap_detector: object | None = None,
        *,
        outline_simplification_enabled: bool,
        outline_simplification_tolerance_px: float,
    ) -> None:
        captured["quantizer"] = quantizer

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    monkeypatch.setattr(
        generator_application,
        "ParallelImageQuantizer",
        FakeParallelImageQuantizer,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "__init__",
        fake_generator_init,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        quantization_executor=FakeExecutor(),
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["quantizer"] is None


def test_generate_preserves_sequential_quantizer_without_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config()

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object] = {}

    def fake_generator_init(
        self: PaintByNumbersGenerator,
        color_distance: ColorDistance | None = None,
        quantizer: object | None = None,
        complexity_reducer: object | None = None,
        overlap_detector: object | None = None,
        *,
        outline_simplification_enabled: bool,
        outline_simplification_tolerance_px: float,
    ) -> None:
        captured["quantizer"] = quantizer

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "__init__",
        fake_generator_init,
    )
    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["quantizer"] is None


def test_generate_preserves_quantization_output_across_execution_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = InputImage.from_rows(
        (
            (
                RGB(0, 0, 0),
                RGB(64, 64, 64),
                RGB(128, 128, 128),
                RGB(192, 192, 192),
                RGB(255, 255, 255),
            ),
        ),
    )

    palette = Palette(
        id="determinism",
        manufacturer="Test",
        display_name="Determinism",
        version=1,
        colors=(
            PaletteColor(
                number=1,
                name="Black",
                rgb=RGB(0, 0, 0),
                lab=Lab(
                    l=0.0,
                    a=0.0,
                    b=0.0,
                ),
            ),
            PaletteColor(
                number=2,
                name="Gray",
                rgb=RGB(128, 128, 128),
                lab=Lab(
                    l=53.6,
                    a=0.0,
                    b=0.0,
                ),
            ),
            PaletteColor(
                number=3,
                name="White",
                rgb=RGB(255, 255, 255),
                lab=Lab(
                    l=100.0,
                    a=0.0,
                    b=0.0,
                ),
            ),
        ),
    )

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="determinism",
        palette_version=1,
    )

    quantized_results: list[QuantizedImage] = []
    executor_calls = 0

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            nonlocal executor_calls
            executor_calls += 1

            quantizer = ImageQuantizer(
                color_distance=color_distance,
            )

            results: list[QuantizationChunkResult] = []

            index_by_color = {
                color: index
                for index, color in enumerate(
                    palette.colors,
                )
            }

            for chunk_index, packed_colors in chunks:
                colors = tuple(
                    RGB(
                        packed_colors[offset],
                        packed_colors[offset + 1],
                        packed_colors[offset + 2],
                    )
                    for offset in range(
                        0,
                        len(packed_colors),
                        COLOR_BYTES,
                    )
                )

                chunk_image = InputImage.from_rows(
                    (colors,),
                )

                quantized_chunk = quantizer.quantize(
                    chunk_image,
                    palette,
                )

                results.append(
                    (
                        chunk_index,
                        bytes(
                            index_by_color[palette_color]
                            for palette_color in (quantized_chunk.rows_at(0))
                        ),
                    ),
                )

            return tuple(
                reversed(
                    results,
                ),
            )

    class FakeGenerator:
        def __init__(
            self,
            color_distance: ColorDistance,
            quantizer: Quantizer | None = None,
            complexity_reducer: object | None = None,
            overlap_detector: object | None = None,
            *,
            outline_simplification_enabled: bool,
            outline_simplification_tolerance_px: float,
        ) -> None:
            self._color_distance = color_distance
            self._quantizer = quantizer

        def generate(
            self,
            image: InputImage,
            palette: Palette,
            minimum_circle_diameter_px: int,
        ) -> VectorDocument:
            quantizer = self._quantizer

            if quantizer is None:
                quantizer = ImageQuantizer(
                    color_distance=self._color_distance,
                )

            quantized_results.append(
                quantizer.quantize(
                    image,
                    palette,
                ),
            )

            return expected_document

    def fake_cpu_count() -> int:
        return 4

    monkeypatch.setattr(
        os,
        "cpu_count",
        fake_cpu_count,
    )
    monkeypatch.setattr(
        generator_application,
        "PaintByNumbersGenerator",
        FakeGenerator,
    )

    executor = FakeExecutor()

    disabled_document = GeneratorApplication(
        quantization_executor=executor,
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    ).generate(
        image_path=Path("input.png"),
        palette=palette,
        config=create_config(
            parallel_quantization_enabled=False,
            parallel_quantization_break_even_workload=1,
            parallel_quantization_max_workers=4,
        ),
    )

    sequential_document = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    ).generate(
        image_path=Path("input.png"),
        palette=palette,
        config=create_config(
            parallel_quantization_break_even_workload=1,
            parallel_quantization_max_workers=4,
        ),
    )

    parallel_document = GeneratorApplication(
        quantization_executor=executor,
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    ).generate(
        image_path=Path("input.png"),
        palette=palette,
        config=create_config(
            parallel_quantization_break_even_workload=1,
            parallel_quantization_max_workers=4,
        ),
    )

    assert disabled_document == expected_document
    assert sequential_document == expected_document
    assert parallel_document == expected_document

    assert len(quantized_results) == 3
    assert quantized_results[0] == quantized_results[1] == quantized_results[2]
    assert executor_calls == 1
