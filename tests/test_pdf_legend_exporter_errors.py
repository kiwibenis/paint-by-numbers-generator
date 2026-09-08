# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import re
from dataclasses import replace
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

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


@pytest.mark.parametrize(
    "field_name",
    (
        "entry_font_name",
        "entry_number_font_name",
    ),
)
def test_write_page_reports_unavailable_configured_font(
    field_name: str,
) -> None:
    missing_font = "DefinitelyMissingFont"

    config = replace(
        create_pdf_legend_config(),
        # The field is a parameter of the test, so the mapping cannot
        # be matched against the field types. replace raises TypeError
        # on an unknown field, which is what keeps this honest.
        **{field_name: missing_font},  # type: ignore[arg-type]
    )

    exporter = PdfLegendExporter(
        config=config,
    )

    pdf = canvas.Canvas(
        BytesIO(),
    )

    with pytest.raises(
        PdfExportError,
        match=re.escape(
            "PDF legend font is not available: " f"{field_name}={missing_font}."
        ),
    ):
        exporter.write_page(
            pdf=pdf,
            palette=create_palette(),
            geometry=create_geometry(),
        )


def create_pdf_legend_config() -> PdfLegendConfig:
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


def create_palette() -> Palette:
    color = PaletteColor(
        number=42,
        name="Test Red",
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

    return Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )


def create_geometry() -> PhysicalOutputGeometry:
    return PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.PORTRAIT,
    )
