# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Measure source-color spread within quantized palette assignments.

This developer-only diagnostic measures how widely distinct source RGB values
are distributed around the palette color to which they were quantized.

It does not change production quantization behavior.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Protocol

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    PaletteColor,
)


class RgbLabConverter(Protocol):
    """
    Convert RGB colors to CIELAB.
    """

    def convert(
        self,
        rgb: RGB,
    ) -> Lab:
        """
        Convert one RGB color to CIELAB.
        """
        ...


@dataclass(frozen=True, slots=True)
class PaletteSourceColorSpread:
    """
    Source-color spread for one quantized palette color.
    """

    color: PaletteColor
    source_color_count: int
    pixel_count: int
    source_distance_min: float
    source_distance_max: float
    source_distance_mean: float


def build_palette_source_color_spreads(
    *,
    image: InputImage,
    color_matches: dict[RGB, PaletteColor],
    converter: RgbLabConverter,
    color_distance: ColorDistance,
) -> tuple[PaletteSourceColorSpread, ...]:
    """
    Measure distinct-source spread around each assigned palette color.

    Every distinct source RGB contributes exactly once to the distance
    statistics. Pixel frequency is recorded separately and therefore does not
    weight the perceptual spread.
    """
    source_pixel_counts = _source_pixel_counts(
        image,
    )

    sources_by_palette: dict[
        PaletteColor,
        list[RGB],
    ] = defaultdict(
        list,
    )

    pixel_counts_by_palette: Counter[PaletteColor] = Counter()

    for source, pixel_count in source_pixel_counts.items():
        palette_color = color_matches[source]

        sources_by_palette[palette_color].append(
            source,
        )

        pixel_counts_by_palette[palette_color] += pixel_count

    spreads = tuple(
        _build_palette_source_color_spread(
            color=palette_color,
            sources=tuple(
                sources,
            ),
            pixel_count=(pixel_counts_by_palette[palette_color]),
            converter=converter,
            color_distance=color_distance,
        )
        for palette_color, sources in sources_by_palette.items()
    )

    return tuple(
        sorted(
            spreads,
            key=lambda spread: (
                -spread.source_color_count,
                -spread.pixel_count,
                -spread.source_distance_max,
                spread.color.number,
            ),
        ),
    )


def format_palette_source_color_spread(
    spread: PaletteSourceColorSpread,
) -> str:
    """
    Format one palette source-color spread diagnostic.
    """
    return (
        "palette_source_spread="
        f"number={spread.color.number}, "
        f"name={spread.color.name}, "
        f"source_colors={spread.source_color_count}, "
        f"pixels={spread.pixel_count}, "
        "source_delta_e_min="
        f"{spread.source_distance_min:.6f}, "
        "source_delta_e_max="
        f"{spread.source_distance_max:.6f}, "
        "source_delta_e_mean="
        f"{spread.source_distance_mean:.6f}"
    )


def _build_palette_source_color_spread(
    *,
    color: PaletteColor,
    sources: tuple[RGB, ...],
    pixel_count: int,
    converter: RgbLabConverter,
    color_distance: ColorDistance,
) -> PaletteSourceColorSpread:
    distances = tuple(
        color_distance.distance(
            converter.convert(
                source,
            ),
            color.lab,
        )
        for source in sources
    )

    return PaletteSourceColorSpread(
        color=color,
        source_color_count=len(
            sources,
        ),
        pixel_count=pixel_count,
        source_distance_min=min(
            distances,
        ),
        source_distance_max=max(
            distances,
        ),
        source_distance_mean=(
            sum(
                distances,
            )
            / len(
                distances,
            )
        ),
    )


def _source_pixel_counts(
    image: InputImage,
) -> Counter[RGB]:
    return Counter(pixel for row in image.rows() for pixel in row)
