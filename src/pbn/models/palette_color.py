# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

from .lab import Lab
from .rgb import RGB


@dataclass(frozen=True, slots=True)
class PaletteColor:
    """
    Represents one color contained in a drawing palette.
    """

    number: int
    name: str
    rgb: RGB
    lab: Lab
