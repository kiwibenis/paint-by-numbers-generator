# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from pbn.config import PdfLegendConfig
from pbn.exceptions import PdfExportError
from pbn.models import (
    A3,
    A4,
    Orientation,
    Palette,
    PaletteColor,
    PhysicalOutputGeometry,
)


class PdfLegendExporter:
    """
    Exports a palette legend to PDF.
    """

    def __init__(
        self,
        config: PdfLegendConfig,
    ) -> None:
        self._config = config

    def write(
        self,
        palette: Palette,
    ) -> bytes:
        buffer = BytesIO()

        geometry = self._resolve_geometry()

        pdf = canvas.Canvas(
            buffer,
            pagesize=(
                geometry.width_mm * mm,
                geometry.height_mm * mm,
            ),
        )

        self.write_page(
            pdf=pdf,
            palette=palette,
            geometry=geometry,
        )

        pdf.showPage()
        pdf.save()

        return buffer.getvalue()

    def write_page(
        self,
        pdf: canvas.Canvas,
        palette: Palette,
        geometry: PhysicalOutputGeometry,
    ) -> None:
        self._validate_fonts()
        self._validate_layout(
            pdf=pdf,
            palette=palette,
            geometry=geometry,
        )

        entries_per_page = self._config.column_count * self._config.rows_per_page

        for index, color in enumerate(palette.colors):
            if index > 0 and index % entries_per_page == 0:
                pdf.showPage()

            page_index = index % entries_per_page

            column = page_index // self._config.rows_per_page
            row = page_index % self._config.rows_per_page

            x = self._config.start_x_mm * mm + column * self._config.column_width_pt

            y = self._config.table_y_mm * mm - row * self._config.row_height_pt

            if page_index == 0:
                self._draw_header(
                    pdf,
                    palette,
                    geometry,
                )

            self._draw_color_entry(
                pdf,
                color,
                x,
                y,
            )

    def _validate_fonts(
        self,
    ) -> None:
        self._validate_font(
            field_name="entry_font_name",
            font_name=self._config.entry_font_name,
        )
        self._validate_font(
            field_name="entry_number_font_name",
            font_name=self._config.entry_number_font_name,
        )

    @staticmethod
    def _validate_font(
        *,
        field_name: str,
        font_name: str,
    ) -> None:
        try:
            pdfmetrics.getFont(
                font_name,
            )
        except KeyError as exc:
            raise PdfExportError(
                "PDF legend font is not available: " f"{field_name}={font_name}.",
            ) from exc

    def _validate_layout(
        self,
        *,
        pdf: canvas.Canvas,
        palette: Palette,
        geometry: PhysicalOutputGeometry,
    ) -> None:
        margin = self._config.margin_mm * mm

        left = margin
        right = geometry.width_mm * mm - margin
        bottom = margin
        top = geometry.height_mm * mm - margin

        start_x = self._config.start_x_mm * mm

        if start_x < left:
            self._raise_layout_margin_error()

        font_ascent, font_descent = pdfmetrics.getAscentDescent(
            self._config.entry_font_name,
            self._config.entry_font_size_pt,
        )

        header_y = self._config.header_y_mm * mm
        header_width = pdf.stringWidth(
            palette.display_name,
            self._config.entry_font_name,
            self._config.entry_font_size_pt,
        )

        if (
            start_x + header_width > right
            or header_y + font_ascent > top
            or header_y + font_descent < bottom
        ):
            self._raise_layout_margin_error()

        version_text = f"Version {palette.version}"

        version_width = pdf.stringWidth(
            version_text,
            self._config.entry_font_name,
            self._config.entry_font_size_pt,
        )

        version_x = geometry.width_mm * mm - start_x - version_width

        version_y = self._config.version_y_mm * mm

        if (
            version_x < left
            or version_x + version_width > right
            or version_y + font_ascent > top
            or version_y + font_descent < bottom
        ):
            self._raise_layout_margin_error()

        entries_per_page = self._config.column_count * self._config.rows_per_page

        for index, color in enumerate(palette.colors):
            page_index = index % entries_per_page

            column = page_index // self._config.rows_per_page
            row = page_index % self._config.rows_per_page

            x = start_x + column * self._config.column_width_pt

            y = self._config.table_y_mm * mm - row * self._config.row_height_pt

            if (
                x < left
                or x + self._config.column_width_pt > right
                or y < bottom
                or y + self._color_field_pt > top
            ):
                self._raise_layout_margin_error()

            name_width = self._config.column_width_pt - self._config.name_offset_pt

            lines = self._wrap_name(
                pdf,
                color.name,
                name_width,
            )

            for line in lines:
                line_width = pdf.stringWidth(
                    line,
                    self._config.entry_font_name,
                    self._config.entry_font_size_pt,
                )

                if line_width > name_width:
                    self._raise_layout_margin_error()

    @staticmethod
    def _raise_layout_margin_error() -> None:
        raise PdfExportError(
            "PDF legend layout exceeds configured page margin.",
        )

    def _resolve_geometry(
        self,
    ) -> PhysicalOutputGeometry:
        if self._config.page == "A4":
            page_size = A4
        elif self._config.page == "A3":
            page_size = A3
        else:
            raise ValueError(
                f"Unsupported page size: {self._config.page}",
            )

        for orientation in Orientation:
            if orientation.value == self._config.orientation:
                return PhysicalOutputGeometry(
                    page_size=page_size,
                    orientation=orientation,
                )

        raise ValueError(
            "Unsupported orientation: " f"{self._config.orientation}",
        )

    def _draw_header(
        self,
        pdf: canvas.Canvas,
        palette: Palette,
        geometry: PhysicalOutputGeometry,
    ) -> None:
        pdf.setFillColor(colors.black)

        pdf.setFont(
            self._config.entry_font_name,
            self._config.entry_font_size_pt,
        )

        header_y = self._config.header_y_mm * mm

        pdf.drawString(
            self._config.start_x_mm * mm,
            header_y,
            palette.display_name,
        )

        version_text = f"Version {palette.version}"

        page_width = geometry.width_mm * mm

        version_width = pdf.stringWidth(
            version_text,
            self._config.entry_font_name,
            self._config.entry_font_size_pt,
        )

        version_x = page_width - self._config.start_x_mm * mm - version_width

        version_y = self._config.version_y_mm * mm

        pdf.drawString(
            version_x,
            version_y,
            version_text,
        )

    def _draw_color_entry(
        self,
        pdf: canvas.Canvas,
        color: PaletteColor,
        x: float,
        y: float,
    ) -> None:
        fill_color = colors.Color(
            color.rgb.red / 255.0,
            color.rgb.green / 255.0,
            color.rgb.blue / 255.0,
        )

        pdf.setFillColor(fill_color)

        pdf.rect(
            x,
            y,
            self._color_field_pt,
            self._color_field_pt,
            fill=1,
            stroke=0,
        )

        if self._is_dark_color(color):
            pdf.setFillColor(colors.white)
        else:
            pdf.setFillColor(colors.black)

        pdf.setFont(
            self._config.entry_number_font_name,
            self._config.entry_font_size_pt,
        )

        number = str(color.number)

        number_width = pdf.stringWidth(
            number,
            self._config.entry_number_font_name,
            self._config.entry_font_size_pt,
        )

        number_x = x + (self._color_field_pt - number_width) / 2

        number_y = y + (self._color_field_pt - self._config.entry_font_size_pt) / 2 + 1

        pdf.drawString(
            number_x,
            number_y,
            number,
        )

        pdf.setFillColor(colors.black)

        pdf.setFont(
            self._config.entry_font_name,
            self._config.entry_font_size_pt,
        )

        name_x = x + self._config.name_offset_pt

        name_width = self._config.column_width_pt - self._config.name_offset_pt

        lines = self._wrap_name(
            pdf,
            color.name,
            name_width,
        )

        total_text_height = (
            self._config.entry_font_size_pt
            + (len(lines) - 1) * self._config.entry_line_height_pt
        )

        first_line_y = (
            y
            + (self._color_field_pt - total_text_height) / 2
            + total_text_height
            - self._config.entry_font_size_pt
        )

        for line_index, line in enumerate(lines):
            pdf.drawString(
                name_x,
                first_line_y - (line_index * self._config.entry_line_height_pt),
                line,
            )

    @property
    def _color_field_pt(self) -> float:
        return (
            self._config.color_field_px
            * self._config.points_per_inch
            / self._config.pixels_per_inch
        )

    def _wrap_name(
        self,
        pdf: canvas.Canvas,
        name: str,
        max_width: float,
    ) -> tuple[str, ...]:
        words = name.split()

        if not words:
            return ("",)

        lines: list[str] = []
        current = ""

        for word in words:
            candidate = word if not current else f"{current} {word}"

            if (
                pdf.stringWidth(
                    candidate,
                    self._config.entry_font_name,
                    self._config.entry_font_size_pt,
                )
                <= max_width
            ):
                current = candidate
                continue

            if current:
                lines.append(current)

            current = word

        if current:
            lines.append(current)

        if len(lines) <= 2:
            return tuple(lines)

        first = lines[0]
        second = " ".join(lines[1:])

        while (
            pdf.stringWidth(
                second,
                self._config.entry_font_name,
                self._config.entry_font_size_pt,
            )
            > max_width
            and " " in second
        ):
            second = second.rsplit(" ", 1)[0]

        return (
            first,
            second,
        )

    @staticmethod
    def _is_dark_color(
        color: PaletteColor,
    ) -> bool:
        luminance = (
            0.2126 * color.rgb.red + 0.7152 * color.rgb.green + 0.0722 * color.rgb.blue
        )

        return luminance < 150.0
