# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import replace
from unittest.mock import Mock

import pytest
from reportlab.lib.units import mm

from pbn.config import PdfLegendConfig
from pbn.exceptions import PdfExportError
from pbn.infrastructure.pdf_legend_exporter import PdfLegendExporter
from pbn.models import (
    A4,
    RGB,
    Lab,
    Orientation,
    Palette,
    PaletteColor,
    PhysicalOutputGeometry,
)


def create_config() -> PdfLegendConfig:
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


def create_palette(
    color_count: int = 68,
) -> Palette:
    colors = tuple(
        PaletteColor(
            number=index,
            name=f"Color {index}",
            rgb=RGB(
                red=255,
                green=0,
                blue=0,
            ),
            lab=Lab(
                l=50.0,
                a=50.0,
                b=50.0,
            ),
        )
        for index in range(
            1,
            color_count + 1,
        )
    )

    return Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=colors,
    )


def create_geometry() -> PhysicalOutputGeometry:
    return PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.PORTRAIT,
    )


def create_canvas_mock() -> Mock:
    pdf = Mock()
    pdf.stringWidth.return_value = 50.0
    return pdf


def test_write_page_keeps_color_fields_inside_configured_margin() -> None:
    config = create_config()
    palette = create_palette()
    geometry = create_geometry()
    pdf = create_canvas_mock()

    PdfLegendExporter(
        config=config,
    ).write_page(
        pdf=pdf,
        palette=palette,
        geometry=geometry,
    )

    margin = config.margin_mm * mm
    page_width = geometry.width_mm * mm
    page_height = geometry.height_mm * mm

    assert pdf.rect.call_count == 68

    for call in pdf.rect.call_args_list:
        x, y, width, height = call.args[:4]

        assert x >= margin
        assert y >= margin
        assert x + width <= page_width - margin
        assert y + height <= page_height - margin


@pytest.mark.parametrize(
    "config",
    (
        replace(
            create_config(),
            margin_mm=25.0,
        ),
        replace(
            create_config(),
            column_width_pt=140.0,
        ),
        replace(
            create_config(),
            header_y_mm=293.0,
        ),
        replace(
            create_config(),
            column_count=1,
            start_x_mm=30.0,
            header_y_mm=260.0,
            version_y_mm=250.0,
            table_y_mm=240.0,
            margin_mm=30.0,
        ),
    ),
)
def test_write_page_rejects_layout_outside_configured_margin(
    config: PdfLegendConfig,
) -> None:
    with pytest.raises(
        PdfExportError,
        match="PDF legend layout exceeds configured page margin",
    ):
        PdfLegendExporter(
            config=config,
        ).write_page(
            pdf=create_canvas_mock(),
            palette=create_palette(),
            geometry=create_geometry(),
        )
