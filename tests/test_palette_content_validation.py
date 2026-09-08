# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from pbn.exceptions import InvalidPaletteError
from pbn.infrastructure.palette_document import (
    MAXIMUM_COLOR_COUNT,
    MAXIMUM_TEXT_LENGTH,
    PaletteDocumentError,
    validate_palette_document,
)
from pbn.infrastructure.palette_loader import PaletteLoader
from pbn.models import RGB

_VALID: dict[str, Any] = {
    "metadata": {
        "id": "test",
        "manufacturer": "Test",
        "display_name": "Test Palette",
        "version": 1,
    },
    "colors": [
        {
            "number": 1,
            "name": "Black",
            "rgb": {
                "red": 0,
                "green": 0,
                "blue": 0,
            },
        },
    ],
}


def _document(
    **changes: Any,
) -> dict[str, Any]:
    document = deepcopy(_VALID)
    document.update(changes)

    return document


def test_valid_document_is_accepted() -> None:
    assert validate_palette_document(
        deepcopy(_VALID),
    )


@pytest.mark.parametrize(
    "document",
    [
        [],
        "text",
        42,
        None,
    ],
)
def test_non_object_documents_are_rejected(
    document: object,
) -> None:
    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


def test_unexpected_top_level_keys_are_rejected() -> None:
    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            _document(extra="value"),
        )


def test_unexpected_metadata_keys_are_rejected() -> None:
    document = deepcopy(_VALID)
    document["metadata"]["extra"] = "value"

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


def test_unexpected_color_keys_are_rejected() -> None:
    """
    Unpacking a document into a model would accept whatever it contains.
    """
    document = deepcopy(_VALID)
    document["colors"][0]["extra"] = "value"

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


def test_unexpected_channel_keys_are_rejected() -> None:
    document = deepcopy(_VALID)
    document["colors"][0]["rgb"]["alpha"] = 255

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


@pytest.mark.parametrize(
    "name",
    [
        42,
        None,
        ["Black"],
        {"value": "Black"},
        "",
        "x" * (MAXIMUM_TEXT_LENGTH + 1),
    ],
)
def test_unusable_color_names_are_rejected(
    name: object,
) -> None:
    """
    A non-string name otherwise reaches the PDF legend export.
    """
    document = deepcopy(_VALID)
    document["colors"][0]["name"] = name

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        256,
        1.5,
        True,
        "0",
        None,
    ],
)
def test_unusable_channel_values_are_rejected(
    value: object,
) -> None:
    document = deepcopy(_VALID)
    document["colors"][0]["rgb"]["red"] = value

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


@pytest.mark.parametrize(
    "version",
    [
        0,
        -1,
        "1",
        1.0,
        True,
    ],
)
def test_unusable_versions_are_rejected(
    version: object,
) -> None:
    document = deepcopy(_VALID)
    document["metadata"]["version"] = version

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            document,
        )


def test_empty_color_list_is_rejected() -> None:
    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            _document(colors=[]),
        )


def test_color_count_is_bounded() -> None:
    colors = [
        {
            "number": index + 1,
            "name": f"C{index}",
            "rgb": {"red": 0, "green": 0, "blue": 0},
        }
        for index in range(MAXIMUM_COLOR_COUNT + 1)
    ]

    with pytest.raises(PaletteDocumentError):
        validate_palette_document(
            _document(colors=colors),
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        256,
    ],
)
def test_color_model_rejects_channels_outside_the_range(
    value: int,
) -> None:
    with pytest.raises(ValueError):
        RGB(
            red=value,
            green=0,
            blue=0,
        )


def test_color_model_rejects_non_integer_channels() -> None:
    with pytest.raises(TypeError):
        RGB(
            red="0",  # type: ignore[arg-type]
            green=0,
            blue=0,
        )


def _write(
    directory: Path,
    document: object,
    name: str = "test-v1.json",
) -> Path:
    path = directory / name
    path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    return path


def test_loader_accepts_a_valid_document(
    tmp_path: Path,
) -> None:
    palette = PaletteLoader().load(
        _write(
            tmp_path,
            _VALID,
        ),
    )

    assert palette.id == "test"
    assert len(palette.colors) == 1


@pytest.mark.parametrize(
    "document",
    [
        {"metadata": {}, "colors": []},
        {"colors": []},
        {"metadata": _VALID["metadata"]},
        [],
        "text",
    ],
)
def test_loader_translates_schema_failures(
    tmp_path: Path,
    document: object,
) -> None:
    """
    Parsing failures become one project-specific error, per ADR-0002.
    """
    with pytest.raises(InvalidPaletteError):
        PaletteLoader().load(
            _write(
                tmp_path,
                document,
            ),
        )


def test_loader_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test-v1.json"
    path.write_text(
        "{not json",
        encoding="utf-8",
    )

    with pytest.raises(InvalidPaletteError):
        PaletteLoader().load(
            path,
        )


def test_loader_bounds_the_document_size(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test-v1.json"
    path.write_text(
        " " * 2_000_000,
        encoding="utf-8",
    )

    with pytest.raises(InvalidPaletteError):
        PaletteLoader().load(
            path,
        )


def test_shipped_palettes_satisfy_the_schema() -> None:
    for path in sorted(
        Path("palettes").glob("*.json"),
    ):
        palette = PaletteLoader().load(
            path,
        )

        assert palette.colors
