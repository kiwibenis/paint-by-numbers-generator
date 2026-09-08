# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import Protocol

from pbn.color.color_distance import ColorDistance
from pbn.exceptions import QuantizationPaletteError
from pbn.models import (
    MAXIMUM_PALETTE_SIZE,
    Palette,
)

COLOR_BYTES = 3
"""
Bytes one color occupies in a chunk: red, green, blue.
"""

QuantizationChunk = tuple[
    int,
    bytes,
]
"""
One chunk: its index, and its colors as three bytes each.

Bytes rather than `RGB` objects, per ADR-0014. The measurement behind
that decision put the same colors at 6.26 MB and 1453 ms as objects
against 1.17 MB and 0.3 ms as bytes.

The chunk index is what orders the results, because the executor is free
to return them in whatever order the workers finish.
"""

QuantizationChunkResult = tuple[
    int,
    bytes,
]
"""
One result: the chunk's index, and one palette index per color.

The index addresses `Palette.colors` of the palette the caller supplied.
The palette colors do not cross back: the caller supplied the palette
and can resolve an index against it, and a color returned would be a
copy of an object it already holds.

One byte per index holds only while a palette has at most
`MAXIMUM_PALETTE_SIZE` entries, which `ensure_addressable_palette`
checks at this boundary before any work is done.
"""


class QuantizationExecutorPort(Protocol):
    """
    Executes independent quantization chunks.

    The palette must be addressable by a single index byte, because the
    quantized image the results feed into stores one index per pixel.
    An implementation that moves palette indices across a process
    boundary depends on the same bound. `ensure_addressable_palette`
    states it at this boundary rather than leaving each implementation
    to discover it.
    """

    def quantize_chunks(
        self,
        chunks: tuple[QuantizationChunk, ...],
        palette: Palette,
        color_distance: ColorDistance,
    ) -> tuple[QuantizationChunkResult, ...]: ...


def ensure_addressable_palette(
    palette: Palette,
) -> None:
    """
    Reject a palette an index byte cannot address.

    Checked before the work rather than after it. Without this the
    failure appears only once the results are assembled, and the caller
    has already paid for a quantization whose outcome cannot be stored.
    """
    if len(palette.colors) > MAXIMUM_PALETTE_SIZE:
        raise QuantizationPaletteError(
            f"A palette of {len(palette.colors)} colors cannot be "
            f"addressed by one index byte, which bounds it at "
            f"{MAXIMUM_PALETTE_SIZE}.",
        )
