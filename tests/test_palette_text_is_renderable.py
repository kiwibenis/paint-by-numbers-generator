# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from pbn.infrastructure.palette_document import (
    PaletteDocumentError,
    is_renderable,
    unsupported_code_points,
    validate_palette_document,
)

LEGEND_FONT_NAMES = (
    "Helvetica",
    "Helvetica-Bold",
)
"""
The fonts the legend is drawn with.

Kept here rather than imported, so that changing the exporter's fonts
without revisiting the accepted character set makes this module fail
instead of passing against the wrong renderer.
"""

_FALLBACK_FONT = b"ZapfDingbats"
"""
The font the library substitutes when the legend font has no glyph.

There is no exception and no return value to inspect: the substitution
is visible only in the produced document, which is why these tests read
one.
"""


def substitutes_a_fallback_font(
    character: str,
    font_name: str,
) -> bool:
    """
    Report whether drawing one character leaves the legend font.
    """
    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            100.0,
            60.0,
        ),
        pageCompression=0,
    )

    pdf.setFont(
        font_name,
        9,
    )

    pdf.drawString(
        5.0,
        20.0,
        character,
    )

    pdf.showPage()
    pdf.save()

    return _FALLBACK_FONT in buffer.getvalue()


def accepted_characters() -> tuple[str, ...]:
    """
    Every character below U+2200 the validator accepts.

    The upper bound covers the legend encoding, whose highest character
    is U+20AC, with room above it. Characters beyond that are outside
    the encoding by construction and are covered by the rejection tests.
    """
    return tuple(
        chr(code_point)
        for code_point in range(0x2200)
        if is_renderable(chr(code_point))
    )


def test_accepted_character_set_is_the_expected_size() -> None:
    """
    A guard on the two tests below, which would both pass on an empty
    accepted set.
    """
    assert len(accepted_characters()) == 218


@pytest.mark.parametrize(
    "font_name",
    LEGEND_FONT_NAMES,
)
def test_every_accepted_character_renders_in_the_legend_font(
    font_name: str,
) -> None:
    """
    The accepted set must not be wider than the renderer.

    This is the assertion the validator's bound rests on. Stating it as
    a comment would let the two drift the moment the legend font
    changes.
    """
    substituted = [
        character
        for character in accepted_characters()
        if substitutes_a_fallback_font(
            character,
            font_name,
        )
    ]

    assert substituted == []


@pytest.mark.parametrize(
    "character",
    (
        "П",
        "深",
        "\U0001f534",
        "\x00",
        "\n",
        "\x7f",
        "Ā",
    ),
)
def test_characters_the_legend_cannot_render_are_rejected(
    character: str,
) -> None:
    assert not is_renderable(
        character,
    )
    assert unsupported_code_points(
        f"Colour {character}",
    ) == (f"U+{ord(character):04X}",)


@pytest.mark.parametrize(
    "value",
    (
        "Titanium White",
        "Grün",
        "Bleu Céruleum",
        "Preis 10 €",
        "Niño",
        "Åkerblom",
    ),
)
def test_latin_palette_names_remain_accepted(
    value: str,
) -> None:
    assert (
        unsupported_code_points(
            value,
        )
        == ()
    )


def test_unsupported_code_points_reports_each_character_once() -> None:
    assert unsupported_code_points(
        "ПуПу",
    ) == (
        "U+041F",
        "U+0443",
    )


def create_document(
    color_name: str,
) -> dict[str, object]:
    return {
        "metadata": {
            "id": "test",
            "manufacturer": "Test",
            "display_name": "Test Palette",
            "version": 1,
        },
        "colors": [
            {
                "number": 1,
                "name": color_name,
                "rgb": {
                    "red": 10,
                    "green": 20,
                    "blue": 30,
                },
            },
        ],
    }


def test_validation_rejects_a_color_name_the_legend_cannot_render() -> None:
    with pytest.raises(
        PaletteDocumentError,
        match=r"colors\[0\]\.name contains characters .* U\+041F",
    ):
        validate_palette_document(
            create_document(
                "Пурпурный",
            ),
        )


def test_validation_reports_code_points_rather_than_characters() -> None:
    """
    A rejected value is the one thing in the document known to contain
    characters a terminal should not be handed.
    """
    with pytest.raises(
        PaletteDocumentError,
    ) as failure:
        validate_palette_document(
            create_document(
                "White\x1b[31m",
            ),
        )

    message = str(
        failure.value,
    )

    assert "U+001B" in message
    assert "\x1b" not in message


def test_validation_accepts_a_latin_color_name() -> None:
    document = validate_palette_document(
        create_document(
            "Bleu Céruleum",
        ),
    )

    assert document["colors"][0]["name"] == "Bleu Céruleum"
