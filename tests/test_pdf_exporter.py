# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import re
from unittest.mock import Mock, call, patch

import pytest
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from pbn.config import PdfLegendConfig
from pbn.infrastructure.pdf_exporter import PdfExporter
from pbn.models import (
    ImagePlacementGeometry,
    Label,
    Orientation,
    Outline,
    PageSize,
    Palette,
    PhysicalOutputGeometry,
    VectorDocument,
)

LABEL_FONT_NAME = "Helvetica"
TEST_MARGIN_MM = 0.0


def label_baseline_y(
    center_y: float,
    font_size_pt: int,
) -> float:
    ascent, descent = pdfmetrics.getAscentDescent(
        LABEL_FONT_NAME,
        font_size_pt,
    )

    return center_y - (ascent + descent) / 2.0


def create_palette() -> Palette:
    return Palette(
        id="test-palette",
        version=1,
        manufacturer="Test",
        display_name="Test Palette",
        colors=(),
    )


def create_legend_config() -> PdfLegendConfig:
    return PdfLegendConfig(
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
    )


def create_canvas_mock() -> Mock:
    canvas_instance = Mock()
    canvas_instance.stringWidth.return_value = 50.0
    return canvas_instance


def create_legend_geometry() -> PhysicalOutputGeometry:
    return PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )


def create_a3_portrait_legend_geometry() -> PhysicalOutputGeometry:
    return PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=297.0,
            height_mm=420.0,
        ),
        orientation=Orientation.PORTRAIT,
    )


def test_pdf_exporter_maps_outline_to_physical_position() -> None:
    document = VectorDocument(
        outlines=(
            Outline(
                region_id=1,
                points=(
                    (100, 200),
                    (200, 200),
                    (200, 300),
                    (100, 300),
                ),
            ),
        ),
        labels=(),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.LANDSCAPE,
    )

    placement = ImagePlacementGeometry(
        scale=0.1,
        image_width_mm=280.0,
        image_height_mm=210.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=2800,
        crop_height_px=2100,
        output_offset_x_mm=8.5,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    path = canvas_instance.beginPath.return_value

    path.moveTo.assert_called_once_with(
        18.5 * mm,
        190.0 * mm,
    )

    path.lineTo.assert_any_call(
        28.5 * mm,
        190.0 * mm,
    )
    path.lineTo.assert_any_call(
        28.5 * mm,
        180.0 * mm,
    )
    path.lineTo.assert_any_call(
        18.5 * mm,
        180.0 * mm,
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_draws_label() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(
            Label(
                region_id=1,
                text="7",
                position=(50.0, 60.0),
            ),
        ),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.drawCentredString.assert_called_once_with(
        50.0 * mm,
        label_baseline_y(
            237.0 * mm,
            9,
        ),
        "7",
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_applies_configured_font_and_line_sizes() -> None:
    document = VectorDocument(
        outlines=(
            Outline(
                region_id=1,
                points=(
                    (10, 20),
                    (20, 20),
                    (20, 30),
                ),
            ),
        ),
        labels=(
            Label(
                region_id=1,
                text="7",
                position=(15.0, 25.0),
            ),
        ),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=13,
            line_width_pt=0.75,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.setFont.assert_called_once_with(
        LABEL_FONT_NAME,
        13,
    )
    canvas_instance.setLineWidth.assert_called_once_with(
        0.75,
    )
    canvas_instance.drawCentredString.assert_called_once_with(
        15.0 * mm,
        label_baseline_y(
            272.0 * mm,
            13,
        ),
        "7",
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_applies_configured_output_colors() -> None:
    document = VectorDocument(
        outlines=(
            Outline(
                region_id=1,
                points=(
                    (10, 20),
                    (20, 20),
                    (20, 30),
                ),
            ),
        ),
        labels=(
            Label(
                region_id=1,
                text="7",
                position=(15.0, 25.0),
            ),
        ),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with (
        patch(
            "pbn.infrastructure.pdf_exporter.canvas.Canvas",
            return_value=canvas_instance,
        ),
        patch(
            "pbn.infrastructure.pdf_exporter.PdfLegendExporter",
        ),
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            line_color="#123456",
            number_color="#AbCdEf",
            font_size_pt=9,
            line_width_pt=0.4,
        )

    canvas_instance.setStrokeColor.assert_called_once_with(
        HexColor("#123456"),
    )
    canvas_instance.setFillColor.assert_called_once_with(
        HexColor("#AbCdEf"),
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_draws_outline() -> None:
    document = VectorDocument(
        outlines=(
            Outline(
                region_id=1,
                points=(
                    (10, 20),
                    (110, 20),
                    (110, 120),
                    (10, 120),
                ),
            ),
        ),
        labels=(),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.beginPath.assert_called_once()

    path = canvas_instance.beginPath.return_value

    path.moveTo.assert_called_once_with(
        10.0 * mm,
        277.0 * mm,
    )
    path.lineTo.assert_any_call(
        110.0 * mm,
        277.0 * mm,
    )
    path.lineTo.assert_any_call(
        110.0 * mm,
        177.0 * mm,
    )
    path.lineTo.assert_any_call(
        10.0 * mm,
        177.0 * mm,
    )
    path.close.assert_called_once_with()

    canvas_instance.drawPath.assert_called_once_with(
        path,
        stroke=1,
        fill=0,
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_generates_pdf_document() -> None:
    document = VectorDocument(
        outlines=(
            Outline(
                region_id=1,
                points=(
                    (0, 0),
                    (100, 0),
                    (100, 100),
                    (0, 100),
                ),
            ),
        ),
        labels=(),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.LANDSCAPE,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    pdf = PdfExporter().write(
        document=document,
        geometry=geometry,
        legend_geometry=create_legend_geometry(),
        placement=placement,
        palette=create_palette(),
        legend_config=create_legend_config(),
        margin_mm=TEST_MARGIN_MM,
        font_size_pt=9,
        line_width_pt=0.4,
        line_color="#000000",
        number_color="#000000",
    )

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")

    page_sizes = re.findall(
        rb"/MediaBox\s+\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]",
        pdf,
    )

    assert len(page_sizes) == 2

    first_width, first_height = (float(value) for value in page_sizes[0])
    second_width, second_height = (float(value) for value in page_sizes[1])

    assert first_width > first_height
    assert second_width < second_height


def test_pdf_exporter_maps_label_to_physical_position() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(
            Label(
                region_id=1,
                text="7",
                position=(100.5, 200.5),
            ),
        ),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.LANDSCAPE,
    )

    placement = ImagePlacementGeometry(
        scale=0.1,
        image_width_mm=280.0,
        image_height_mm=210.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=2800,
        crop_height_px=2100,
        output_offset_x_mm=8.5,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.drawCentredString.assert_called_once_with(
        18.55 * mm,
        label_baseline_y(
            189.95 * mm,
            9,
        ),
        "7",
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_converts_physical_y_to_pdf_coordinates() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(
            Label(
                region_id=1,
                text="7",
                position=(100.0, 200.0),
            ),
        ),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.LANDSCAPE,
    )

    placement = ImagePlacementGeometry(
        scale=0.1,
        image_width_mm=280.0,
        image_height_mm=210.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=2800,
        crop_height_px=2100,
        output_offset_x_mm=8.5,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.drawCentredString.assert_called_once_with(
        18.5 * mm,
        label_baseline_y(
            190.0 * mm,
            9,
        ),
        "7",
    )

    assert isinstance(pdf, bytes)


def test_pdf_exporter_writes_palette_legend_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = VectorDocument(
        outlines=(),
        labels=(),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    palette = create_palette()
    legend_config = create_legend_config()
    legend_geometry = create_legend_geometry()

    captured: dict[str, object] = {}

    class FakeLegendExporter:
        def __init__(
            self,
            config: PdfLegendConfig,
        ) -> None:
            captured["config"] = config

        def write_page(
            self,
            pdf: object,
            palette: Palette,
            geometry: PhysicalOutputGeometry,
        ) -> None:
            captured["pdf"] = pdf
            captured["palette"] = palette
            captured["geometry"] = geometry

    monkeypatch.setattr(
        "pbn.infrastructure.pdf_exporter.PdfLegendExporter",
        FakeLegendExporter,
    )

    pdf = PdfExporter().write(
        document=document,
        geometry=geometry,
        legend_geometry=legend_geometry,
        placement=placement,
        palette=palette,
        legend_config=legend_config,
        margin_mm=TEST_MARGIN_MM,
        font_size_pt=9,
        line_width_pt=0.4,
        line_color="#000000",
        number_color="#000000",
    )

    assert isinstance(pdf, bytes)
    assert captured["palette"] is palette
    assert captured["config"] is legend_config
    assert captured["geometry"] is legend_geometry


def test_pdf_exporter_uses_independent_legend_page_geometry() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(),
    )

    pbn_geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.LANDSCAPE,
    )

    legend_geometry = create_a3_portrait_legend_geometry()

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    pdf = PdfExporter().write(
        document=document,
        geometry=pbn_geometry,
        legend_geometry=legend_geometry,
        placement=placement,
        palette=create_palette(),
        legend_config=create_legend_config(),
        margin_mm=TEST_MARGIN_MM,
        font_size_pt=9,
        line_width_pt=0.4,
        line_color="#000000",
        number_color="#000000",
    )

    page_sizes = re.findall(
        rb"/MediaBox\s+\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]",
        pdf,
    )

    assert len(page_sizes) == 2

    first_width, first_height = (float(value) for value in page_sizes[0])
    second_width, second_height = (float(value) for value in page_sizes[1])

    assert first_width > first_height
    assert second_width < second_height
    assert second_width == pytest.approx(
        legend_geometry.width_mm * 72.0 / 25.4,
    )
    assert second_height == pytest.approx(
        legend_geometry.height_mm * 72.0 / 25.4,
    )


def test_pdf_exporter_preserves_outline_hole_ring() -> None:
    document = VectorDocument(
        outlines=(
            Outline(
                region_id=1,
                points=(
                    (10, 20),
                    (110, 20),
                    (110, 120),
                    (10, 120),
                ),
                hole_rings=(
                    (
                        (40, 50),
                        (40, 90),
                        (80, 90),
                        (80, 50),
                    ),
                ),
            ),
        ),
        labels=(),
    )

    geometry = PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )

    placement = ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=210.0,
        image_height_mm=297.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=210,
        crop_height_px=297,
        output_offset_x_mm=0.0,
        output_offset_y_mm=0.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        pdf = PdfExporter().write(
            document=document,
            geometry=geometry,
            legend_geometry=create_legend_geometry(),
            placement=placement,
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=TEST_MARGIN_MM,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    path = canvas_instance.beginPath.return_value

    assert path.moveTo.call_args_list == [
        call(
            10.0 * mm,
            277.0 * mm,
        ),
        call(
            40.0 * mm,
            247.0 * mm,
        ),
    ]

    assert path.lineTo.call_args_list == [
        call(
            110.0 * mm,
            277.0 * mm,
        ),
        call(
            110.0 * mm,
            177.0 * mm,
        ),
        call(
            10.0 * mm,
            177.0 * mm,
        ),
        call(
            40.0 * mm,
            207.0 * mm,
        ),
        call(
            80.0 * mm,
            207.0 * mm,
        ),
        call(
            80.0 * mm,
            247.0 * mm,
        ),
    ]

    assert path.close.call_count == 2

    canvas_instance.drawPath.assert_called_once_with(
        path,
        stroke=1,
        fill=0,
    )

    assert isinstance(pdf, bytes)
