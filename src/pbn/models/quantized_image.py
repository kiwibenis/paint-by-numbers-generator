# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from .palette_color import PaletteColor

MAXIMUM_PALETTE_SIZE = 256
"""
Palette entries a quantized image can address.

One index byte per pixel is what makes the representation compact, and a
byte addresses 256 entries. Every other bound on palette size in this
project derives from this one rather than repeating the number.
"""


@dataclass(frozen=True, slots=True)
class QuantizedImage:
    """
    Immutable quantized image.

    Pixels are stored compactly as one palette index per pixel in row-major
    order, alongside the palette those indices refer to. `PaletteColor`
    remains the vocabulary of the domain and is produced at this boundary;
    code on a per-pixel path compares indices directly.
    """

    width: int

    height: int

    palette: tuple[PaletteColor, ...]

    indices: bytes

    def __post_init__(self) -> None:
        if len(self.palette) > MAXIMUM_PALETTE_SIZE:
            raise ValueError(
                "A quantized image supports at most "
                f"{MAXIMUM_PALETTE_SIZE} palette entries, got "
                f"{len(self.palette)}.",
            )

        expected = self.width * self.height

        if len(self.indices) != expected:
            raise ValueError(
                f"Expected {expected} palette indices for "
                f"{self.width}x{self.height}, got {len(self.indices)}.",
            )

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Sequence[PaletteColor]],
    ) -> QuantizedImage:
        """
        Build a quantized image from rows of palette colors.
        """
        height = len(rows)
        width = len(rows[0]) if height else 0

        palette: list[PaletteColor] = []
        index_by_color: dict[PaletteColor, int] = {}
        indices = bytearray()

        for row in rows:
            if len(row) != width:
                raise ValueError(
                    "All rows must have the same width.",
                )

            for color in row:
                index = index_by_color.get(
                    color,
                )

                if index is None:
                    index = len(palette)

                    if index >= MAXIMUM_PALETTE_SIZE:
                        raise ValueError(
                            "A quantized image supports at most "
                            f"{MAXIMUM_PALETTE_SIZE} palette entries, "
                            "and the rows use more.",
                        )

                    index_by_color[color] = index
                    palette.append(color)

                indices.append(index)

        return cls(
            width=width,
            height=height,
            palette=tuple(palette),
            indices=bytes(indices),
        )

    def index_at(
        self,
        x: int,
        y: int,
    ) -> int:
        """
        Return the palette index of one pixel.
        """
        return self.indices[y * self.width + x]

    def color_at(
        self,
        x: int,
        y: int,
    ) -> PaletteColor:
        """
        Return the palette color of one pixel.
        """
        return self.palette[self.indices[y * self.width + x]]

    def rows_at(
        self,
        y: int,
    ) -> tuple[PaletteColor, ...]:
        """
        Return one row as palette colors.
        """
        start = y * self.width
        palette = self.palette

        return tuple(
            palette[index] for index in self.indices[start : start + self.width]
        )

    def rows(self) -> Iterator[tuple[PaletteColor, ...]]:
        """
        Iterate over the image as rows of palette colors.
        """
        palette = self.palette

        for y in range(self.height):
            start = y * self.width

            yield tuple(
                palette[index] for index in self.indices[start : start + self.width]
            )
