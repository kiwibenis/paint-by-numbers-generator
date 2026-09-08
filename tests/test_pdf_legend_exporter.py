# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from reportlab.lib.units import mm

from pbn.config import PdfLegendConfig
from pbn.infrastructure import load_palette
from pbn.infrastructure.pdf_legend_exporter import PdfLegendExporter
from pbn.models import (
    A3,
    A4,
    RGB,
    Lab,
    Orientation,
    Palette,
    PaletteColor,
    PhysicalOutputGeometry,
)


def create_pdf_legend_config(
    *,
    page: str = "A4",
    orientation: str = "portrait",
    color_field_px: float = 30.0,
    entry_font_name: str = "Helvetica",
    entry_number_font_name: str = "Helvetica-Bold",
    entry_font_size_pt: int = 9,
    version_y_mm: float = 278.0,
) -> PdfLegendConfig:
    return PdfLegendConfig(
        pixels_per_inch=96.0,
        points_per_inch=72.0,
        color_field_px=color_field_px,
        column_count=4,
        rows_per_page=17,
        start_x_mm=20.0,
        header_y_mm=285.0,
        version_y_mm=version_y_mm,
        table_y_mm=265.0,
        column_width_pt=118.0,
        name_offset_pt=30.0,
        row_height_pt=42.5,
        entry_font_name=entry_font_name,
        entry_number_font_name=entry_number_font_name,
        entry_font_size_pt=entry_font_size_pt,
        entry_line_height_pt=9.0,
        page=page,
        orientation=orientation,
        margin_mm=5.0,
    )


def create_exporter(
    config: PdfLegendConfig | None = None,
) -> PdfLegendExporter:
    return PdfLegendExporter(
        config=config or create_pdf_legend_config(),
    )


def create_canvas_mock() -> Mock:
    canvas_instance = Mock()
    canvas_instance.stringWidth.return_value = 50.0
    return canvas_instance


def test_pdf_legend_exporter_uses_single_page_for_polychromos_palette() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos60-v1.json"),
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter().write(
            palette=palette,
        )

    canvas_instance.showPage.assert_called_once()


def test_pdf_legend_exporter_draws_one_color_field_per_palette_color() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos60-v1.json"),
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter().write(
            palette=palette,
        )

    assert canvas_instance.rect.call_count == 60


def test_pdf_legend_exporter_uses_configured_color_field_size() -> None:
    color = PaletteColor(
        number=42,
        name="Test Red",
        rgb=RGB(
            red=255,
            green=128,
            blue=0,
        ),
        lab=Lab(
            l=50.0,
            a=50.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    config = create_pdf_legend_config(
        color_field_px=50.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter(config).write(
            palette=palette,
        )

    canvas_instance.rect.assert_called_once()

    _, _, width, height = canvas_instance.rect.call_args.args[:4]

    expected_size = 50 * 72 / 96

    assert width == expected_size
    assert height == expected_size


def test_pdf_legend_exporter_uses_palette_rgb_for_color_field() -> None:
    color = PaletteColor(
        number=42,
        name="Test Red",
        rgb=RGB(
            red=255,
            green=128,
            blue=0,
        ),
        lab=Lab(
            l=50.0,
            a=50.0,
            b=0.0,
        ),
    )

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter().write(
            palette=palette,
        )

    fill_color_calls = canvas_instance.setFillColor.call_args_list

    assert any(
        call.args[0].red == 1.0
        and call.args[0].green == 128 / 255.0
        and call.args[0].blue == 0.0
        for call in fill_color_calls
    )


def test_pdf_legend_exporter_draws_palette_number_and_name() -> None:
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

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter().write(
            palette=palette,
        )

    draw_string_calls = canvas_instance.drawString.call_args_list

    assert any(call.args[2] == "42" for call in draw_string_calls)

    assert any(call.args[2] == "Test Red" for call in draw_string_calls)


def test_pdf_legend_exporter_uses_configured_entry_font() -> None:
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

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    config = create_pdf_legend_config(
        entry_font_name="Courier",
        entry_font_size_pt=11,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter(config).write(
            palette=palette,
        )

    canvas_instance.setFont.assert_any_call(
        "Courier",
        11,
    )


def test_pdf_legend_exporter_uses_configured_number_font() -> None:
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

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    config = create_pdf_legend_config(
        entry_number_font_name="Courier-Bold",
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter(config).write(
            palette=palette,
        )

    canvas_instance.setFont.assert_any_call(
        "Courier-Bold",
        9,
    )


def test_pdf_legend_exporter_keeps_polychromos_colors_inside_a4_page() -> None:
    palette = load_palette(
        Path("palettes/faberCastellPolychromos60-v1.json"),
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter().write(
            palette=palette,
        )

    geometry = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.PORTRAIT,
    )

    page_width = geometry.width_mm * mm
    page_height = geometry.height_mm * mm

    rect_calls = canvas_instance.rect.call_args_list

    assert len(rect_calls) == 60

    for rect_call in rect_calls:
        x, y, width, height = rect_call.args[:4]

        assert x >= 0
        assert y >= 0
        assert x + width <= page_width
        assert y + height <= page_height


def test_pdf_legend_exporter_starts_new_page_for_additional_colors() -> None:
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
        for index in range(1, 70)
    )

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=colors,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter().write(
            palette=palette,
        )

    assert canvas_instance.showPage.call_count == 2


def test_pdf_legend_exporter_draws_palette_metadata() -> None:
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

    palette = Palette(
        id="test-palette",
        version=3,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    config = create_pdf_legend_config(
        version_y_mm=271.0,
    )

    canvas_instance = create_canvas_mock()

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter(config).write(
            palette=palette,
        )

    canvas_instance.drawString.assert_any_call(
        20 * mm,
        285 * mm,
        "Test Palette",
    )

    version_text = "Version 3"
    version_width = 50.0

    geometry = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.PORTRAIT,
    )

    page_width = geometry.width_mm * mm

    expected_version_x = page_width - 20 * mm - version_width

    canvas_instance.drawString.assert_any_call(
        expected_version_x,
        271.0 * mm,
        version_text,
    )


def test_pdf_legend_exporter_generates_pdf() -> None:
    color = PaletteColor(
        number=1,
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

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    pdf = create_exporter().write(
        palette=palette,
    )

    assert pdf.startswith(b"%PDF-")


def test_pdf_legend_exporter_write_uses_configured_page_geometry() -> None:
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

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    config = create_pdf_legend_config(
        page="A3",
        orientation="landscape",
    )

    exporter = create_exporter(
        config,
    )
    canvas_instance = create_canvas_mock()

    expected_geometry = PhysicalOutputGeometry(
        page_size=A3,
        orientation=Orientation.LANDSCAPE,
    )

    with (
        patch(
            "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
            return_value=canvas_instance,
        ) as canvas_factory,
        patch.object(
            exporter,
            "write_page",
        ) as write_page,
    ):
        exporter.write(
            palette=palette,
        )

    assert canvas_factory.call_args.kwargs["pagesize"] == (
        expected_geometry.width_mm * mm,
        expected_geometry.height_mm * mm,
    )

    write_page.assert_called_once_with(
        pdf=canvas_instance,
        palette=palette,
        geometry=expected_geometry,
    )


def test_pdf_legend_exporter_uses_independent_page_geometry() -> None:
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

    palette = Palette(
        id="test-palette",
        version=1,
        manufacturer="Test Manufacturer",
        display_name="Test Palette",
        colors=(color,),
    )

    config = create_pdf_legend_config(
        page="A3",
        orientation="portrait",
        version_y_mm=271.0,
    )

    canvas_instance = create_canvas_mock()

    legend_geometry = PhysicalOutputGeometry(
        page_size=A3,
        orientation=Orientation.PORTRAIT,
    )

    with patch(
        "pbn.infrastructure.pdf_legend_exporter.canvas.Canvas",
        return_value=canvas_instance,
    ):
        create_exporter(config).write_page(
            pdf=canvas_instance,
            palette=palette,
            geometry=legend_geometry,
        )

    version_text = "Version 1"
    version_width = 50.0
    page_width = 297 * mm

    expected_version_x = page_width - config.start_x_mm * mm - version_width

    canvas_instance.drawString.assert_any_call(
        expected_version_x,
        config.version_y_mm * mm,
        version_text,
    )
