# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import json
from pathlib import Path

from pbn.color import RgbToLabConverter
from pbn.exceptions import (
    InvalidPaletteError,
    PaletteNotFoundError,
)
from pbn.models import (
    RGB,
    Palette,
    PaletteColor,
)

from .palette_document import (
    MAXIMUM_PALETTE_DOCUMENT_BYTES,
    PaletteDocumentError,
    validate_palette_document,
)
from .palette_file_name import (
    PaletteIdentity,
    parse_palette_file_name,
)


class PaletteLoader:
    """
    Loads palette definitions from JSON files.
    """

    def __init__(self) -> None:
        self._converter = RgbToLabConverter()

    def load(
        self,
        file: Path,
    ) -> Palette:
        raw = self._read_document(
            file,
        )

        expected = self._parse_filename(
            file,
        )

        # Parsing failures are reported as one project-specific error in
        # accordance with ADR-0002, rather than escaping as whatever the
        # standard library happened to raise.
        try:
            document = validate_palette_document(
                raw,
            )

            metadata = document["metadata"]

            if metadata["id"] != expected.palette_id:
                raise InvalidPaletteError(str(file))

            if metadata["version"] != expected.version:
                raise InvalidPaletteError(str(file))

            colors = tuple(
                self._build_color(
                    item,
                )
                for item in document["colors"]
            )

            return Palette(
                id=metadata["id"],
                manufacturer=metadata["manufacturer"],
                display_name=metadata["display_name"],
                version=metadata["version"],
                colors=colors,
            )

        except (
            PaletteDocumentError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidPaletteError(str(file)) from exc

    def _build_color(
        self,
        item: dict[str, object],
    ) -> PaletteColor:
        """
        Build one palette color from validated fields.

        Fields are read explicitly rather than unpacked, so a document
        cannot decide which arguments a domain model receives.
        """
        channels = item["rgb"]

        if not isinstance(channels, dict):
            raise InvalidPaletteError(
                "Color channels must be an object.",
            )

        rgb = RGB(
            red=channels["red"],
            green=channels["green"],
            blue=channels["blue"],
        )

        return PaletteColor(
            number=item["number"],  # type: ignore[arg-type]
            name=item["name"],  # type: ignore[arg-type]
            rgb=rgb,
            lab=self._converter.convert(rgb),
        )

    @staticmethod
    def _read_document(
        file: Path,
    ) -> object:
        """
        Read a palette document within a bounded size.
        """
        try:
            size = file.stat().st_size
        except FileNotFoundError as exc:
            raise PaletteNotFoundError(str(file)) from exc
        except OSError as exc:
            raise InvalidPaletteError(str(file)) from exc

        if size > MAXIMUM_PALETTE_DOCUMENT_BYTES:
            raise InvalidPaletteError(str(file))

        try:
            with file.open(
                "r",
                encoding="utf-8",
            ) as fp:
                return json.load(fp)

        except FileNotFoundError as exc:
            raise PaletteNotFoundError(str(file)) from exc

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            OSError,
        ) as exc:
            raise InvalidPaletteError(str(file)) from exc

    @staticmethod
    def _parse_filename(
        file: Path,
    ) -> PaletteIdentity:
        """
        Return the identity the file name denotes.

        The rule lives in `palette_file_name` rather than here, because
        the catalogue and the selection have to agree with this on which
        names exist. They did not: this accepted names that
        `PaletteManager.get` then refused to build.
        """
        identity = parse_palette_file_name(
            file.name,
        )

        if identity is None:
            raise InvalidPaletteError(str(file))

        return identity


def load_palette(
    file: Path,
) -> Palette:
    """
    Load a palette from a JSON file.
    """
    return PaletteLoader().load(
        file,
    )
