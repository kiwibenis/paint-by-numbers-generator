# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from pbn.config import PdfLegendConfig
from pbn.infrastructure.pdf_exporter import PdfExporter
from pbn.models import (
    ImagePlacementGeometry,
    Label,
    Orientation,
    PageSize,
    Palette,
    PhysicalOutputGeometry,
    VectorDocument,
)


def create_geometry() -> PhysicalOutputGeometry:
    return PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )


def create_placement() -> ImagePlacementGeometry:
    return ImagePlacementGeometry(
        scale=1.0,
        image_width_mm=190.0,
        image_height_mm=277.0,
        crop_left_px=0,
        crop_top_px=0,
        crop_width_px=190,
        crop_height_px=277,
        output_offset_x_mm=10.0,
        output_offset_y_mm=10.0,
    )


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


@pytest.mark.parametrize(
    "position",
    (
        (0.0, 138.5),
        (190.0, 138.5),
        (95.0, 0.0),
        (95.0, 277.0),
    ),
)
def test_pdf_exporter_skips_label_exceeding_printer_margin(
    position: tuple[float, float],
) -> None:
    document = VectorDocument(
        outlines=(),
        labels=(
            Label(
                region_id=1,
                text="120",
                position=position,
            ),
        ),
    )

    canvas_instance = Mock()
    canvas_instance.stringWidth.return_value = 50.0

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        PdfExporter().write(
            document=document,
            geometry=create_geometry(),
            legend_geometry=create_geometry(),
            placement=create_placement(),
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=10.0,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.drawCentredString.assert_not_called()


def test_pdf_exporter_draws_label_inside_printer_margin() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(
            Label(
                region_id=1,
                text="120",
                position=(95.0, 138.5),
            ),
        ),
    )

    canvas_instance = Mock()
    canvas_instance.stringWidth.return_value = 50.0

    with patch(
        "pbn.infrastructure.pdf_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        PdfExporter().write(
            document=document,
            geometry=create_geometry(),
            legend_geometry=create_geometry(),
            placement=create_placement(),
            palette=create_palette(),
            legend_config=create_legend_config(),
            margin_mm=10.0,
            font_size_pt=9,
            line_width_pt=0.4,
            line_color="#000000",
            number_color="#000000",
        )

    canvas_instance.drawCentredString.assert_called_once()
