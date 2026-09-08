# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate source-color spread within quantized palette assignments.

This developer tool measures how many distinct source RGB colors are absorbed
by each used palette color and how far those source colors lie from their
assigned palette color under the configured color-distance metric.

It does not change production quantization behavior.
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from pbn.color import (
    ImageQuantizer,
    RgbToLabConverter,
)
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.palette_loader import load_palette
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    REPOSITORY_ROOT,
    SUPPORTED_COLOR_DISTANCES,
    palette_path,
    resolve_color_distance,
)
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)
from tools.quantization_source_spread import (
    build_palette_source_color_spreads,
    format_palette_source_color_spread,
)


def build_parser() -> ArgumentParser:
    """
    Build the quantization source-spread evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate how broadly distinct source RGB colors are absorbed "
            "by quantized palette colors."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
    )

    parser.add_argument(
        "--cases",
        nargs="+",
        choices=EVALUATION_CASES,
        default=EVALUATION_CASES,
    )

    parser.add_argument(
        "--palette",
        default=None,
    )

    parser.add_argument(
        "--palette-version",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--color-distance",
        choices=SUPPORTED_COLOR_DISTANCES,
        default=None,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )

    return parser


def main() -> None:
    """
    Run source-color spread diagnostics.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.limit <= 0:
        parser.error(
            "--limit must be greater than zero",
        )

    config = load_config(
        args.config,
    )

    selected_palette = args.palette if args.palette is not None else config.palette

    selected_palette_version = (
        args.palette_version
        if args.palette_version is not None
        else config.palette_version
    )

    selected_color_distance = (
        args.color_distance
        if args.color_distance is not None
        else config.color_distance
    )

    palette = load_palette(
        palette_path(
            palette_id=selected_palette,
            palette_version=selected_palette_version,
        ),
    )

    color_distance = resolve_color_distance(
        selected_color_distance,
    )

    quantizer = ImageQuantizer(
        color_distance=color_distance,
    )

    converter = RgbToLabConverter()

    print(
        (
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            f"limit={args.limit}"
        ),
    )

    for case in args.cases:
        image_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"

        image = load_image(
            image_path,
            DEVELOPER_IMAGE_INPUT_LIMITS,
        )

        unique_colors = quantizer.collect_unique_colors(
            image,
        )

        color_matches = dict(
            quantizer.quantize_colors(
                unique_colors,
                palette,
            ),
        )

        spreads = build_palette_source_color_spreads(
            image=image,
            color_matches=color_matches,
            converter=converter,
            color_distance=color_distance,
        )

        print(
            (
                f"{case}: "
                "distinct_source_colors="
                f"{len(unique_colors)}, "
                "used_palette_colors="
                f"{len(spreads)}, "
                f"pixels={image.width * image.height}"
            ),
        )

        for spread in spreads[: args.limit]:
            print(
                "  "
                + format_palette_source_color_spread(
                    spread,
                ),
            )


if __name__ == "__main__":
    main()
