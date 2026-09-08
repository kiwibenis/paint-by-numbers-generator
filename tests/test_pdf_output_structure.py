# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import base64
import zlib

import pytest

from pbn.config import PdfLegendConfig
from pbn.infrastructure.pdf_exporter import PdfExporter
from pbn.models import (
    RGB,
    ImagePlacementGeometry,
    Lab,
    Label,
    Orientation,
    Outline,
    PageSize,
    Palette,
    PaletteColor,
    PhysicalOutputGeometry,
    VectorDocument,
)

HOSTILE_TEXTS = (
    ") Tj ET Q q BT /F1 40 Tf 50 700 Td (INJECTED",
    "back\\slash \\051 \\( evil",
    "x endstream endobj 99 0 obj << /Type /Catalog >> stream y",
    "1 0 0 RG 0 0 m 500 500 l S",
    "((((()))))",
    "trailer << /Root 99 0 R >> startxref 0 %%EOF",
)
"""
Values that would change the meaning of a content stream if they were
placed into it unescaped.

Each one closes the literal string it arrives in and continues with
operators: a text object is ended, the graphics state is restored, an
object or a cross reference table is begun. A value that survives as
text is inert; a value that survives as syntax is not.
"""

_LITERAL_OPENING = ord("(")
_LITERAL_CLOSING = ord(")")
_ESCAPE = ord("\\")


def literal_strings(
    content: bytes,
) -> tuple[list[bytes], bytes]:
    """
    Split a content stream into its literal strings and everything else.

    A minimal reader of the one construct that matters here: `(` opens a
    literal, `\\` escapes the next byte, and a `)` that is neither
    escaped nor nested closes it. Everything outside is syntax, which is
    what the assertions inspect.
    """
    literals: list[bytes] = []
    outside = bytearray()

    current = bytearray()
    depth = 0
    escaped = False

    for byte in content:
        if depth == 0:
            if byte == _LITERAL_OPENING:
                depth = 1
                continue

            outside.append(byte)
            continue

        if escaped:
            current.append(byte)
            escaped = False
            continue

        if byte == _ESCAPE:
            escaped = True
            continue

        if byte == _LITERAL_OPENING:
            depth += 1
            current.append(byte)
            continue

        if byte == _LITERAL_CLOSING:
            depth -= 1

            if depth == 0:
                literals.append(bytes(current))
                current = bytearray()
                continue

            current.append(byte)
            continue

        current.append(byte)

    if depth != 0:
        raise AssertionError(
            "content stream ends inside an unterminated literal string",
        )

    return literals, bytes(outside)


def content_streams(
    document: bytes,
) -> list[bytes]:
    """
    Return every content stream of a generated document, decompressed.
    """
    streams: list[bytes] = []

    position = 0

    while True:
        start = document.find(
            b"stream",
            position,
        )

        if start == -1:
            return streams

        body_start = start + len(b"stream")

        if document[body_start : body_start + 2] == b"\r\n":
            body_start += 2
        elif document[body_start : body_start + 1] in (b"\n", b"\r"):
            body_start += 1

        end = document.find(
            b"endstream",
            body_start,
        )

        if end == -1:
            return streams

        raw = document[body_start:end]
        position = end + len(b"endstream")

        streams.append(
            decompressed(raw),
        )


def decompressed(
    raw: bytes,
) -> bytes:
    """
    Return a stream body with the filters the exporter applies removed.
    """
    body = raw.strip()

    if body.startswith(b"Gat") or body.endswith(b"~>"):
        body = ascii85_decoded(body)

    try:
        return zlib.decompress(body)
    except zlib.error:
        return body


def ascii85_decoded(
    body: bytes,
) -> bytes:
    payload = body
    marker = payload.find(b"~>")

    if marker != -1:
        payload = payload[:marker]

    return base64.a85decode(
        payload,
        adobe=False,
    )


def create_palette() -> Palette:
    return Palette(
        id="hostile",
        version=1,
        manufacturer=HOSTILE_TEXTS[0],
        display_name=HOSTILE_TEXTS[1],
        colors=tuple(
            PaletteColor(
                number=index + 1,
                name=text,
                rgb=RGB(
                    red=10 * index,
                    green=20,
                    blue=30,
                ),
                lab=Lab(
                    l=50.0,
                    a=0.0,
                    b=0.0,
                ),
            )
            for index, text in enumerate(HOSTILE_TEXTS)
        ),
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


def create_geometry() -> PhysicalOutputGeometry:
    return PhysicalOutputGeometry(
        page_size=PageSize(
            width_mm=210.0,
            height_mm=297.0,
        ),
        orientation=Orientation.PORTRAIT,
    )


def export_with_hostile_values() -> bytes:
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
        labels=(
            Label(
                region_id=1,
                text=HOSTILE_TEXTS[0],
                position=(50, 50),
            ),
        ),
    )

    geometry = create_geometry()

    return PdfExporter().write(
        document=document,
        geometry=geometry,
        legend_geometry=geometry,
        placement=ImagePlacementGeometry(
            scale=1.0,
            image_width_mm=100.0,
            image_height_mm=100.0,
            crop_left_px=0,
            crop_top_px=0,
            crop_width_px=100,
            crop_height_px=100,
            output_offset_x_mm=0.0,
            output_offset_y_mm=0.0,
        ),
        palette=create_palette(),
        legend_config=create_legend_config(),
        margin_mm=0.0,
        font_size_pt=9,
        line_width_pt=0.4,
        line_color="#000000",
        number_color="#000000",
    )


@pytest.fixture(scope="module")
def hostile_document() -> bytes:
    return export_with_hostile_values()


def test_hostile_values_do_not_reach_content_stream_syntax(
    hostile_document: bytes,
) -> None:
    """
    A hostile value must arrive as a string, never as syntax.

    The check is on what lies outside the literal strings, because that
    is the only place a value could change the document. Asserting that
    the escaped form appears somewhere would pass on a writer that also
    emitted the raw form elsewhere.
    """
    for stream in content_streams(
        hostile_document,
    ):
        _, syntax = literal_strings(
            stream,
        )

        assert b"INJECTED" not in syntax
        assert b"startxref" not in syntax
        assert b"/Catalog" not in syntax
        assert b"endobj" not in syntax


def test_hostile_values_survive_as_text(
    hostile_document: bytes,
) -> None:
    """
    Escaping must not silently drop the value it protects.

    Without this, a writer that discarded every hostile value would pass
    the check above.
    """
    literals: list[bytes] = []

    for stream in content_streams(
        hostile_document,
    ):
        found, _ = literal_strings(
            stream,
        )
        literals.extend(found)

    joined = b" ".join(
        literals,
    )

    assert b"INJECTED" in joined
    assert b"startxref" in joined


def test_generated_document_has_one_trailer(
    hostile_document: bytes,
) -> None:
    """
    A second trailer or cross reference table would mean a value escaped
    into the file structure rather than into a stream.
    """
    assert hostile_document.count(b"\ntrailer") == 1
    assert hostile_document.count(b"\nstartxref") == 1
