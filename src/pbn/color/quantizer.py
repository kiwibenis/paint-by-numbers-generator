# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.exceptions import QuantizationPaletteError
from pbn.models import (
    MAXIMUM_PALETTE_SIZE,
    RGB,
    InputImage,
    Palette,
    PaletteColor,
    QuantizedImage,
)

from .color_distance import ColorDistance
from .nearest_palette_color import NearestPaletteColorFinder
from .rgb_to_lab import RgbToLabConverter


class ImageQuantizer:
    """
    Quantizes an input image to a fixed color palette.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
    ) -> None:
        self._converter = RgbToLabConverter()
        self._finder = NearestPaletteColorFinder(
            color_distance=color_distance,
        )

    def quantize(
        self,
        image: InputImage,
        palette: Palette,
    ) -> QuantizedImage:
        unique_colors = self.collect_unique_colors(
            image,
        )

        color_matches = self.quantize_colors(
            unique_colors,
            palette,
        )

        return self.reconstruct_quantized_image(
            image,
            color_matches,
        )

    def collect_unique_colors(
        self,
        image: InputImage,
    ) -> tuple[RGB, ...]:
        """
        Collect unique image colors in first-seen order.
        """
        return tuple(
            RGB(
                red=packed >> 16,
                green=(packed >> 8) & 0xFF,
                blue=packed & 0xFF,
            )
            for packed in _unique_packed_colors(
                image.pixels,
            )
        )

    def quantize_colors(
        self,
        colors: tuple[RGB, ...],
        palette: Palette,
    ) -> tuple[
        tuple[RGB, PaletteColor],
        ...,
    ]:
        """
        Quantize an ordered collection of RGB colors.
        """
        matches: list[tuple[RGB, PaletteColor]] = []

        for rgb in colors:
            lab = self._converter.convert(
                rgb,
            )

            nearest = self._finder.find(
                lab,
                palette,
            )

            matches.append(
                (
                    rgb,
                    nearest,
                ),
            )

        return tuple(
            matches,
        )

    def reconstruct_quantized_image(
        self,
        image: InputImage,
        color_matches: tuple[
            tuple[RGB, PaletteColor],
            ...,
        ],
    ) -> QuantizedImage:
        """
        Reconstruct a quantized image from RGB-to-palette matches.
        """
        palette_colors: list[PaletteColor] = []
        index_by_palette_color: dict[PaletteColor, int] = {}
        index_by_packed: dict[int, int] = {}

        for rgb, palette_color in color_matches:
            index = index_by_palette_color.get(
                palette_color,
            )

            if index is None:
                index = len(palette_colors)

                if index >= MAXIMUM_PALETTE_SIZE:
                    # Reached before the index array is built, so the
                    # failure names the cause rather than surfacing as
                    # a range error out of `bytes`.
                    raise QuantizationPaletteError(
                        "The image uses more than "
                        f"{MAXIMUM_PALETTE_SIZE} palette colors, which "
                        "a quantized image cannot address.",
                    )

                index_by_palette_color[palette_color] = index
                palette_colors.append(palette_color)

            index_by_packed[(rgb.red << 16) | (rgb.green << 8) | rgb.blue] = index

        pixels = image.pixels

        # Packed integers rather than color objects, so the per-pixel path
        # allocates nothing that is discarded again immediately.
        indices = bytes(
            index_by_packed[
                (pixels[offset] << 16) | (pixels[offset + 1] << 8) | pixels[offset + 2]
            ]
            for offset in range(
                0,
                len(pixels),
                3,
            )
        )

        return QuantizedImage(
            width=image.width,
            height=image.height,
            palette=tuple(palette_colors),
            indices=indices,
        )


def _unique_packed_colors(
    pixels: bytes,
) -> tuple[int, ...]:
    """
    Return the distinct colors of a pixel buffer in first-seen order.

    Colors are packed into integers so that collecting them does not
    allocate one color object per pixel.
    """
    return tuple(
        dict.fromkeys(
            (pixels[offset] << 16) | (pixels[offset + 1] << 8) | pixels[offset + 2]
            for offset in range(
                0,
                len(pixels),
                3,
            )
        ),
    )
