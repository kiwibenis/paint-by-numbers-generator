# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class PaletteError(PbnError):
    """Base class for palette related errors."""

    public_message: ClassVar[str] = "The requested palette could not be used."
    caused_by_request: ClassVar[bool] = False


class PaletteNotFoundError(PaletteError):
    """
    Palette file not found.

    The palette identifier is caller input, but distinguishing an unknown
    palette from a rejected identifier would answer questions about the
    file system. Both therefore share one public message.
    """

    public_message: ClassVar[str] = "The requested palette is not available."
    caused_by_request: ClassVar[bool] = True


class InvalidPaletteError(PaletteError):
    """
    Palette file is invalid.

    Shipped palettes are operator data. A caller selects an identifier
    and cannot supply a document, so a malformed one is an operational
    failure rather than a rejected request.
    """

    public_message: ClassVar[str] = "The requested palette could not be loaded."
    caused_by_request: ClassVar[bool] = False


class PaletteCatalogueError(PaletteError):
    """
    The set of available palettes could not be read.

    Distinct from a palette that fails to load, which is skipped when
    listing. This is the directory itself being unreadable, so there is
    no catalogue to report and nothing a caller did to cause it.
    """

    public_message: ClassVar[str] = "The palette catalogue could not be read."
    caused_by_request: ClassVar[bool] = False
