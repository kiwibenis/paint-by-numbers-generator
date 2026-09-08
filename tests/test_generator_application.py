# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pathlib import Path

import pytest

from pbn.application import (
    GeneratorApplication,
    GeneratorConfigResolver,
)
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.models import (
    A3,
    RGB,
    ImagePlacementGeometry,
    InputImage,
    Lab,
    Orientation,
    Palette,
    PaletteColor,
    PhysicalOutputGeometry,
    VectorDocument,
)
from pbn.pipeline import PaintByNumbersGenerator
from tests.fake_image_loader import FakeImageLoader
from tests.fake_overlap_detector import FakeOverlapDetector


def test_generate_passes_outline_simplification_config_to_generator(
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
        color_distance: object = None,
        quantizer: object = None,
        complexity_reducer: object = None,
        overlap_detector: object = None,
        *,
        outline_simplification_enabled: bool = False,
        outline_simplification_tolerance_px: float = 0.0,
    ) -> None:
        captured["enabled"] = outline_simplification_enabled
        captured["tolerance"] = outline_simplification_tolerance_px

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: object,
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

    result = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    ).generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["enabled"] is config.outline_simplification_enabled
    assert captured["tolerance"] == config.outline_simplification_tolerance_px


def test_generate_passes_overlap_detector_to_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config()
    overlap_detector = FakeOverlapDetector()

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object] = {}

    def fake_generator_init(
        self: PaintByNumbersGenerator,
        color_distance: object = None,
        quantizer: object = None,
        complexity_reducer: object = None,
        overlap_detector: object = None,
        *,
        outline_simplification_enabled: bool = False,
        outline_simplification_tolerance_px: float = 0.0,
    ) -> None:
        captured["overlap_detector"] = overlap_detector

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: object,
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

    result = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=overlap_detector,
    ).generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert captured["overlap_detector"] is overlap_detector


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
    line_color: str = "#000000",
    number_color: str = "#000000",
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
        color_distance="delta_e_76",
        parallel_quantization_enabled=True,
        parallel_quantization_break_even_workload=360_448,
        parallel_quantization_max_workers=8,
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.0,
        font_size_pt=9,
        line_width_pt=0.4,
        line_color=line_color,
        number_color=number_color,
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
    """
    A 400x300 image.

    The size matters because the resolver derives the minimum circle
    diameter from it. The image data must match the declared size, so the
    fixture cannot claim a large size it does not supply.
    """
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    return InputImage.from_rows(
        tuple(tuple(black for _ in range(400)) for _ in range(300)),
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


def test_generate_returns_vector_document(
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

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        captured["image"] = image
        captured["palette"] = palette
        captured["minimum_circle_diameter_px"] = minimum_circle_diameter_px

        return expected_document

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
    assert captured["image"] is image
    assert captured["palette"] is palette
    assert captured["minimum_circle_diameter_px"] == 5


def test_generate_pdf_uses_pdf_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = create_image()
    palette = create_palette()
    config = create_config(
        line_color="#123456",
        number_color="#AbCdEf",
    )

    expected_document = VectorDocument(
        outlines=(),
        labels=(),
        palette_id="test",
        palette_version=1,
    )

    captured: dict[str, object] = {}

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    class FakePdfExporter:
        def write(
            self,
            document: VectorDocument,
            geometry: PhysicalOutputGeometry,
            legend_geometry: PhysicalOutputGeometry,
            placement: ImagePlacementGeometry,
            palette: Palette,
            legend_config: PdfLegendConfig,
            margin_mm: float,
            font_size_pt: int,
            line_width_pt: float,
            line_color: str,
            number_color: str,
        ) -> bytes:
            captured["document"] = document
            captured["geometry"] = geometry
            captured["legend_geometry"] = legend_geometry
            captured["placement"] = placement
            captured["palette"] = palette
            captured["legend_config"] = legend_config
            captured["margin_mm"] = margin_mm
            captured["font_size_pt"] = font_size_pt
            captured["line_width_pt"] = line_width_pt
            captured["line_color"] = line_color
            captured["number_color"] = number_color

            return b"%PDF-test"

    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate_pdf(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
        pdf_exporter=FakePdfExporter(),
    )

    assert result == b"%PDF-test"
    assert captured["document"] is expected_document
    assert captured["palette"] is palette
    assert captured["legend_config"] is config.pdf_legend
    assert captured["margin_mm"] == config.margin_mm
    assert captured["font_size_pt"] == config.font_size_pt
    assert captured["line_width_pt"] == config.line_width_pt
    assert captured["line_color"] == "#123456"
    assert captured["number_color"] == "#AbCdEf"
    assert isinstance(
        captured["geometry"],
        PhysicalOutputGeometry,
    )
    assert isinstance(
        captured["legend_geometry"],
        PhysicalOutputGeometry,
    )


def test_generate_pdf_resolves_independent_legend_geometry(
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

    expected_legend_geometry = PhysicalOutputGeometry(
        page_size=A3,
        orientation=Orientation.PORTRAIT,
    )

    captured: dict[str, object] = {}

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    def fake_resolve_palette_legend_geometry(
        self: GeneratorConfigResolver,
        config: GeneratorConfig,
    ) -> PhysicalOutputGeometry:
        return expected_legend_geometry

    class FakePdfExporter:
        def write(
            self,
            document: VectorDocument,
            geometry: PhysicalOutputGeometry,
            legend_geometry: PhysicalOutputGeometry,
            placement: ImagePlacementGeometry,
            palette: Palette,
            legend_config: PdfLegendConfig,
            margin_mm: float,
            font_size_pt: int,
            line_width_pt: float,
            line_color: str,
            number_color: str,
        ) -> bytes:
            captured["legend_geometry"] = legend_geometry
            return b"%PDF-test"

    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )
    monkeypatch.setattr(
        GeneratorConfigResolver,
        "resolve_palette_legend_geometry",
        fake_resolve_palette_legend_geometry,
    )

    application = GeneratorApplication(
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate_pdf(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
        pdf_exporter=FakePdfExporter(),
    )

    assert result == b"%PDF-test"
    assert captured["legend_geometry"] is expected_legend_geometry


def test_generate_accepts_progress_reporter(
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

    class FakeProgressReporter:
        def report(
            self,
            message: str,
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
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        progress_reporter=FakeProgressReporter(),
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document


def test_generate_reports_progress(
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

    messages: list[str] = []

    class FakeProgressReporter:
        def report(
            self,
            message: str,
        ) -> None:
            messages.append(message)

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        progress_reporter=FakeProgressReporter(),
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
    )

    assert result is expected_document
    assert messages == [
        "Loading input image.",
        "Generating paint-by-numbers document.",
    ]


def test_generate_pdf_reports_export_progress(
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

    messages: list[str] = []

    class FakeProgressReporter:
        def report(
            self,
            message: str,
        ) -> None:
            messages.append(message)

    def fake_generate(
        self: PaintByNumbersGenerator,
        image: InputImage,
        palette: Palette,
        minimum_circle_diameter_px: int,
    ) -> VectorDocument:
        return expected_document

    class FakePdfExporter:
        def write(
            self,
            document: VectorDocument,
            geometry: PhysicalOutputGeometry,
            legend_geometry: PhysicalOutputGeometry,
            placement: ImagePlacementGeometry,
            palette: Palette,
            legend_config: PdfLegendConfig,
            margin_mm: float,
            font_size_pt: int,
            line_width_pt: float,
            line_color: str,
            number_color: str,
        ) -> bytes:
            return b"%PDF-test"

    monkeypatch.setattr(
        PaintByNumbersGenerator,
        "generate",
        fake_generate,
    )

    application = GeneratorApplication(
        progress_reporter=FakeProgressReporter(),
        image_loader=FakeImageLoader(image),
        overlap_detector=FakeOverlapDetector(),
    )

    result = application.generate_pdf(
        image_path=Path("input.png"),
        palette=palette,
        config=config,
        pdf_exporter=FakePdfExporter(),
    )

    assert result == b"%PDF-test"
    assert messages == [
        "Loading input image.",
        "Generating paint-by-numbers document.",
        "Exporting PDF document.",
    ]
