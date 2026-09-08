# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import unicodedata
from typing import Any

from pbn.models import MAXIMUM_PALETTE_SIZE

MAXIMUM_PALETTE_DOCUMENT_BYTES = 1_048_576

TEXT_ENCODING = "cp1252"
"""
The encoding whose characters a palette may use.

This is WinAnsi, the encoding of the built-in fonts the legend is drawn
with. A character outside it is not rejected by the PDF library; it is
silently replaced by an unrelated symbol, so a palette containing one
would produce a legend that no longer states which pencil a number
means. Rejecting the document is the loud version of that failure.

The bound is the renderer's, not a preference for Latin script. It is
asserted against the renderer in
`tests/test_palette_text_is_renderable.py` rather than left as a claim
here, so the two cannot drift apart unnoticed.
"""

MAXIMUM_COLOR_COUNT = MAXIMUM_PALETTE_SIZE
"""
Colors a palette document may declare.

Derived from the storage invariant rather than repeating its value. A
quantized image addresses its palette with one index byte, so a palette
larger than that cannot be used in full and a document declaring one
would be accepted only to fail later.
"""

MAXIMUM_TEXT_LENGTH = 128

_METADATA_KEYS = frozenset(
    {
        "id",
        "manufacturer",
        "display_name",
        "version",
    },
)

_COLOR_KEYS = frozenset(
    {
        "number",
        "name",
        "rgb",
    },
)

_RGB_KEYS = frozenset(
    {
        "red",
        "green",
        "blue",
    },
)


class PaletteDocumentError(ValueError):
    """
    A palette document does not match the expected schema.
    """


def validate_palette_document(
    document: object,
) -> dict[str, Any]:
    """
    Validate a decoded palette document against an explicit schema.

    Palette content reaches generated output, so its shape is checked
    before use rather than discovered through key access. Every failure
    is reported as one error type, which the caller translates into a
    project-specific palette error.
    """
    root = _require_mapping(
        document,
        "document",
    )

    _require_exact_keys(
        root,
        frozenset({"metadata", "colors"}),
        "document",
    )

    metadata = _require_mapping(
        root["metadata"],
        "metadata",
    )

    _require_exact_keys(
        metadata,
        _METADATA_KEYS,
        "metadata",
    )

    for key in ("id", "manufacturer", "display_name"):
        _require_text(
            metadata[key],
            f"metadata.{key}",
        )

    _require_positive_integer(
        metadata["version"],
        "metadata.version",
    )

    colors = root["colors"]

    if not isinstance(colors, list):
        raise PaletteDocumentError(
            "colors must be a list.",
        )

    if not colors:
        raise PaletteDocumentError(
            "colors must not be empty.",
        )

    if len(colors) > MAXIMUM_COLOR_COUNT:
        raise PaletteDocumentError(
            f"colors must not exceed {MAXIMUM_COLOR_COUNT} entries.",
        )

    for index, color in enumerate(colors):
        _validate_color(
            color,
            index,
        )

    _require_unique_numbers(
        colors,
    )

    return root


def _require_unique_numbers(
    colors: list[Any],
) -> None:
    """
    Reject a document in which one number names two colors.

    The number is both the manufacturer's reference and the label printed
    inside every region of that color, so a repeated number produces a
    template a painter cannot follow: the legend offers two paints under
    the number the region shows, with nothing to tell them apart.

    Checked here rather than per color, because it is the only rule in this
    document that no single entry can violate on its own. A generation with
    a `reference8` document whose white and black shared number one
    completed with exit code zero and produced exactly that legend.
    """
    first_index_by_number: dict[int, int] = {}

    for index, color in enumerate(colors):
        number = color["number"]

        if number in first_index_by_number:
            raise PaletteDocumentError(
                f"colors[{index}].number repeats "
                f"colors[{first_index_by_number[number]}].number: "
                f"{number}.",
            )

        first_index_by_number[number] = index


def _validate_color(
    color: object,
    index: int,
) -> None:
    entry = _require_mapping(
        color,
        f"colors[{index}]",
    )

    _require_exact_keys(
        entry,
        _COLOR_KEYS,
        f"colors[{index}]",
    )

    _require_positive_integer(
        entry["number"],
        f"colors[{index}].number",
    )

    _require_text(
        entry["name"],
        f"colors[{index}].name",
    )

    rgb = _require_mapping(
        entry["rgb"],
        f"colors[{index}].rgb",
    )

    _require_exact_keys(
        rgb,
        _RGB_KEYS,
        f"colors[{index}].rgb",
    )

    for channel in ("red", "green", "blue"):
        _require_channel(
            rgb[channel],
            f"colors[{index}].rgb.{channel}",
        )


def _require_mapping(
    value: object,
    location: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PaletteDocumentError(
            f"{location} must be an object.",
        )

    for key in value:
        if not isinstance(key, str):
            raise PaletteDocumentError(
                f"{location} must use text keys.",
            )

    return value


def _require_exact_keys(
    value: dict[str, Any],
    expected: frozenset[str],
    location: str,
) -> None:
    """
    Reject unknown keys rather than ignoring them.

    Unpacking a document into a domain model would otherwise accept
    whatever the document happens to contain.
    """
    present = frozenset(value)

    missing = expected - present

    if missing:
        raise PaletteDocumentError(
            f"{location} is missing: {', '.join(sorted(missing))}.",
        )

    unexpected = present - expected

    if unexpected:
        raise PaletteDocumentError(
            f"{location} has unexpected keys: " f"{', '.join(sorted(unexpected))}.",
        )


def _require_text(
    value: object,
    location: str,
) -> None:
    if not isinstance(value, str):
        raise PaletteDocumentError(
            f"{location} must be text.",
        )

    if not value:
        raise PaletteDocumentError(
            f"{location} must not be empty.",
        )

    if len(value) > MAXIMUM_TEXT_LENGTH:
        raise PaletteDocumentError(
            f"{location} must not exceed " f"{MAXIMUM_TEXT_LENGTH} characters.",
        )

    unsupported = unsupported_code_points(
        value,
    )

    if unsupported:
        raise PaletteDocumentError(
            f"{location} contains characters the generated legend "
            f"cannot render: {', '.join(unsupported)}.",
        )


def unsupported_code_points(
    value: str,
) -> tuple[str, ...]:
    """
    Return the code points of `value` that the legend cannot render.

    Reported as `U+XXXX` rather than as the characters themselves. The
    rejected set is exactly the one a terminal would be asked to
    interpret, and a diagnostic message is not the place to hand it one.

    Order of first appearance, without repetition, so a document with
    one stray character does not produce a message the length of the
    field.
    """
    found: list[str] = []
    seen: set[str] = set()

    for character in value:
        if character in seen:
            continue

        seen.add(character)

        if is_renderable(character):
            continue

        found.append(
            f"U+{ord(character):04X}",
        )

    return tuple(
        found,
    )


def is_renderable(
    character: str,
) -> bool:
    """
    Report whether the legend font can draw one character.

    Two conditions, both measured against the renderer rather than
    assumed: the character must exist in the legend encoding, and it
    must not be a control character. The control characters are inside
    the encoding but have no glyph, and the library substitutes for them
    exactly as it does for a character outside it.
    """
    if unicodedata.category(character) == "Cc":
        return False

    try:
        character.encode(
            TEXT_ENCODING,
        )
    except UnicodeEncodeError:
        return False

    return True


def _require_positive_integer(
    value: object,
    location: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PaletteDocumentError(
            f"{location} must be an integer.",
        )

    if value < 1:
        raise PaletteDocumentError(
            f"{location} must be at least one.",
        )


def _require_channel(
    value: object,
    location: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PaletteDocumentError(
            f"{location} must be an integer.",
        )

    if not 0 <= value <= 255:
        raise PaletteDocumentError(
            f"{location} must be between 0 and 255.",
        )
