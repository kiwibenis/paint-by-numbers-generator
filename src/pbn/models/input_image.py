# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from .rgb import RGB

BYTES_PER_PIXEL = 3


@dataclass(frozen=True, slots=True)
class InputImage:
    """
    Immutable normalized input image.

    Pixels are stored compactly as three bytes per pixel in row-major
    order. `RGB` remains the vocabulary of the domain and is produced at
    this boundary; code on a per-pixel path indexes `pixels` directly.
    """

    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        expected = self.width * self.height * BYTES_PER_PIXEL

        if len(self.pixels) != expected:
            raise ValueError(
                f"Expected {expected} pixel bytes for "
                f"{self.width}x{self.height}, got {len(self.pixels)}.",
            )

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Sequence[RGB]],
    ) -> InputImage:
        """
        Build an image from rows of color objects.
        """
        height = len(rows)
        width = len(rows[0]) if height else 0

        data = bytearray()

        for row in rows:
            if len(row) != width:
                raise ValueError(
                    "All rows must have the same width.",
                )

            for color in row:
                data.append(color.red)
                data.append(color.green)
                data.append(color.blue)

        return cls(
            width=width,
            height=height,
            pixels=bytes(data),
        )

    def rgb_at(
        self,
        x: int,
        y: int,
    ) -> RGB:
        """
        Return the color of one pixel.
        """
        offset = (y * self.width + x) * BYTES_PER_PIXEL

        return RGB(
            red=self.pixels[offset],
            green=self.pixels[offset + 1],
            blue=self.pixels[offset + 2],
        )

    def rows_at(
        self,
        y: int,
    ) -> tuple[RGB, ...]:
        """
        Return one row as color objects.
        """
        row_length = self.width * BYTES_PER_PIXEL
        start = y * row_length

        return tuple(
            RGB(
                red=self.pixels[offset],
                green=self.pixels[offset + 1],
                blue=self.pixels[offset + 2],
            )
            for offset in range(
                start,
                start + row_length,
                BYTES_PER_PIXEL,
            )
        )

    def rows(self) -> Iterator[tuple[RGB, ...]]:
        """
        Iterate over the image as rows of color objects.
        """
        row_length = self.width * BYTES_PER_PIXEL

        for y in range(self.height):
            start = y * row_length

            yield tuple(
                RGB(
                    red=self.pixels[offset],
                    green=self.pixels[offset + 1],
                    blue=self.pixels[offset + 2],
                )
                for offset in range(
                    start,
                    start + row_length,
                    BYTES_PER_PIXEL,
                )
            )
