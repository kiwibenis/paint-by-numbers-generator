# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

from .palette_color import PaletteColor


@dataclass(frozen=True, slots=True)
class Palette:
    """
    Represents one complete drawing palette.
    """

    id: str

    manufacturer: str

    display_name: str

    version: int

    colors: tuple[PaletteColor, ...]
