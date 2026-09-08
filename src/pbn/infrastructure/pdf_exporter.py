# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from pbn.config import PdfLegendConfig
from pbn.infrastructure.pdf_legend_exporter import PdfLegendExporter
from pbn.models import (
    ImagePlacementGeometry,
    Palette,
    PhysicalOutputGeometry,
    VectorDocument,
)

_LABEL_FONT_NAME = "Helvetica"


class PdfExporter:
    """
    Exports a vector document and palette legend to PDF.
    """

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
        buffer = BytesIO()

        pdf = canvas.Canvas(
            buffer,
            pagesize=(
                geometry.width_mm * mm,
                geometry.height_mm * mm,
            ),
        )

        pdf.setLineWidth(
            line_width_pt,
        )

        pdf.setStrokeColor(
            HexColor(line_color),
        )

        pdf.setFillColor(
            HexColor(number_color),
        )

        pdf.setFont(
            _LABEL_FONT_NAME,
            font_size_pt,
        )

        font_ascent, font_descent = pdfmetrics.getAscentDescent(
            _LABEL_FONT_NAME,
            font_size_pt,
        )

        label_baseline_offset = (font_ascent + font_descent) / 2.0

        if margin_mm > 0.0:
            pdf.saveState()

            clip_path: Any = pdf.beginPath()

            clip_path.rect(
                margin_mm * mm,
                margin_mm * mm,
                (geometry.width_mm - 2.0 * margin_mm) * mm,
                (geometry.height_mm - 2.0 * margin_mm) * mm,
            )

            pdf.clipPath(  # pyright: ignore[reportUnknownMemberType]
                clip_path,
                stroke=0,
                fill=0,
            )

        for outline in document.outlines:
            if not outline.points:
                continue

            path: Any = pdf.beginPath()

            self._append_ring_to_path(
                path=path,
                points=outline.points,
                geometry=geometry,
                placement=placement,
            )

            for ring in outline.hole_rings:
                self._append_ring_to_path(
                    path=path,
                    points=ring,
                    geometry=geometry,
                    placement=placement,
                )

            pdf.drawPath(  # pyright: ignore[reportUnknownMemberType]
                path,
                stroke=1,
                fill=0,
            )

        for label in document.labels:
            label_x, label_y = label.position

            if not placement.contains_input_position(
                label_x,
                label_y,
            ):
                continue

            label_position = placement.to_output_position(
                label_x,
                label_y,
            )

            label_center_x = label_position[0] * mm

            label_center_y = (geometry.height_mm - label_position[1]) * mm

            label_baseline_y = label_center_y - label_baseline_offset

            if not self._label_fits_page_margin(
                text=label.text,
                center_x=label_center_x,
                baseline_y=label_baseline_y,
                geometry=geometry,
                margin_mm=margin_mm,
                font_size_pt=font_size_pt,
                font_ascent=font_ascent,
                font_descent=font_descent,
            ):
                continue

            pdf.drawCentredString(
                label_center_x,
                label_baseline_y,
                label.text,
            )

        if margin_mm > 0.0:
            pdf.restoreState()

        pdf.showPage()

        pdf.setPageSize(
            (
                legend_geometry.width_mm * mm,
                legend_geometry.height_mm * mm,
            ),
        )

        legend_exporter = PdfLegendExporter(
            config=legend_config,
        )

        legend_exporter.write_page(
            pdf=pdf,
            palette=palette,
            geometry=legend_geometry,
        )

        pdf.showPage()
        pdf.save()

        return buffer.getvalue()

    @staticmethod
    def _append_ring_to_path(
        *,
        path: Any,
        points: tuple[tuple[int, int], ...],
        geometry: PhysicalOutputGeometry,
        placement: ImagePlacementGeometry,
    ) -> None:
        if not points:
            return

        start_x, start_y = points[0]
        start_position = placement.to_output_position(
            start_x,
            start_y,
        )

        path.moveTo(
            start_position[0] * mm,
            (geometry.height_mm - start_position[1]) * mm,
        )

        for x, y in points[1:]:
            position = placement.to_output_position(
                x,
                y,
            )

            path.lineTo(
                position[0] * mm,
                (geometry.height_mm - position[1]) * mm,
            )

        path.close()

    @staticmethod
    def _label_fits_page_margin(
        *,
        text: str,
        center_x: float,
        baseline_y: float,
        geometry: PhysicalOutputGeometry,
        margin_mm: float,
        font_size_pt: int,
        font_ascent: float,
        font_descent: float,
    ) -> bool:
        margin = margin_mm * mm

        page_width = geometry.width_mm * mm
        page_height = geometry.height_mm * mm

        text_width = pdfmetrics.stringWidth(
            text,
            _LABEL_FONT_NAME,
            font_size_pt,
        )

        left = center_x - text_width / 2.0
        right = center_x + text_width / 2.0
        bottom = baseline_y + font_descent
        top = baseline_y + font_ascent

        return (
            left >= margin
            and right <= page_width - margin
            and bottom >= margin
            and top <= page_height - margin
        )
