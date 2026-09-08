# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from pbn.models import PaletteColor

from .pixel_index import unpack_pixels


@dataclass(frozen=True, slots=True)
class Region:
    """
    Represents one connected color region.

    Pixels are stored as packed indices rather than coordinate tuples.
    See `pixel_index` for the packing; `coordinates` produces the
    coordinates where a caller genuinely needs them.
    """

    id: int

    color: PaletteColor

    pixels: frozenset[int]

    @property
    def size(self) -> int:
        return len(self.pixels)

    def coordinates(self) -> Iterator[tuple[int, int]]:
        """
        Iterate the pixel coordinates of this region.
        """
        return unpack_pixels(
            self.pixels,
        )
