# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate visual detail loss across the region-generation stages.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, replace
from pathlib import Path
from struct import pack

from pbn.application import GeneratorConfigValidator
from pbn.application.generator_config_resolver import (
    GeneratorConfigResolver,
)
from pbn.color import ImageQuantizer
from pbn.exceptions import ConfigurationError
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    ImageSize,
    QuantizedImage,
)
from pbn.regions import (
    RegionDetector,
    RegionMerger,
)
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    PREVIEW_OUTPUT_DIRECTORY,
    REPOSITORY_ROOT,
    palette_path,
    resolve_color_distance,
    write_region_preview,
)
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)

SUPPORTED_STAGES = (
    "quantized",
    "detected",
    "mandatory-merged",
)


@dataclass(frozen=True, slots=True)
class RegionStageEvaluation:
    """
    Region counts observed across the region-generation stages.
    """

    case: str
    minimum_region_size_mm: float
    minimum_circle_diameter_px: int
    detected_region_count: int
    mandatory_region_count: int


def build_quantized_preview_bmp(
    image: QuantizedImage,
) -> bytes:
    """
    Render a quantized image into an uncompressed 24-bit BMP.
    """
    width = image.width
    height = image.height

    bytes_per_pixel = 3

    unpadded_row_size = width * bytes_per_pixel

    row_size = (unpadded_row_size + 3) & ~3

    pixel_data_size = row_size * height

    pixel_data = bytearray(
        pixel_data_size,
    )

    for y, row in enumerate(
        tuple(image.rows()),
    ):
        for x, color in enumerate(
            row,
        ):
            offset = y * row_size + x * bytes_per_pixel

            pixel_data[offset] = color.rgb.blue
            pixel_data[offset + 1] = color.rgb.green
            pixel_data[offset + 2] = color.rgb.red

    pixel_offset = 54

    file_size = pixel_offset + pixel_data_size

    file_header = b"BM" + pack(
        "<IHHI",
        file_size,
        0,
        0,
        pixel_offset,
    )

    information_header = pack(
        "<IiiHHIIiiII",
        40,
        width,
        -height,
        1,
        24,
        0,
        pixel_data_size,
        2835,
        2835,
        0,
        0,
    )

    return (
        file_header
        + information_header
        + bytes(
            pixel_data,
        )
    )


def stage_preview_output_path(
    *,
    output_directory: Path,
    case: str,
    stage: str,
    minimum_region_size_mm: float | None = None,
) -> Path:
    """
    Return the deterministic preview path for one pipeline stage.
    """
    if stage not in SUPPORTED_STAGES:
        raise ValueError(
            f"Unsupported stage: {stage}",
        )

    minimum_size_suffix = ""

    if minimum_region_size_mm is not None:
        minimum_size_token = format(
            minimum_region_size_mm,
            "g",
        ).replace(
            ".",
            "p",
        )

        minimum_size_suffix = "-minimum-region-size-" f"{minimum_size_token}mm"

    return output_directory / (
        "region-stage-" f"{case}-" f"{stage}" f"{minimum_size_suffix}.bmp"
    )


def write_quantized_preview(
    *,
    output_path: Path,
    image: QuantizedImage,
) -> None:
    """
    Write one quantized-image preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_quantized_preview_bmp(
            image,
        ),
    )


def format_stage_evaluation(
    evaluation: RegionStageEvaluation,
) -> str:
    """
    Format one stage-loss evaluation result.
    """
    return (
        f"{evaluation.case}: "
        "minimum_region_size_mm="
        f"{evaluation.minimum_region_size_mm:g}, "
        "minimum_circle_diameter_px="
        f"{evaluation.minimum_circle_diameter_px}, "
        "detected_regions="
        f"{evaluation.detected_region_count}, "
        "mandatory_regions="
        f"{evaluation.mandatory_region_count}"
    )


def build_parser() -> ArgumentParser:
    """
    Build the stage-loss evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Generate visual previews before and after mandatory " "region merging."
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
        default=None,
    )

    parser.add_argument(
        "--minimum-region-size-mm",
        nargs="+",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--preview-output-directory",
        type=Path,
        default=PREVIEW_OUTPUT_DIRECTORY,
    )

    return parser


def main() -> None:
    """
    Generate previews for each region-generation stage.
    """
    parser = build_parser()
    args = parser.parse_args()

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

    selected_minimum_region_sizes_mm = (
        tuple(
            args.minimum_region_size_mm,
        )
        if args.minimum_region_size_mm is not None
        else (config.minimum_region_size_mm,)
    )

    evaluation_configs = tuple(
        replace(
            config,
            minimum_region_size_mm=minimum_region_size_mm,
        )
        for minimum_region_size_mm in selected_minimum_region_sizes_mm
    )

    validator = GeneratorConfigValidator()

    for evaluation_config in evaluation_configs:
        try:
            validator.validate(
                evaluation_config,
            )
        except ConfigurationError as exc:
            parser.error(
                str(exc),
            )

    palette = load_palette(
        palette_path(
            palette_id=selected_palette,
            palette_version=(selected_palette_version),
        ),
    )

    color_distance = resolve_color_distance(
        selected_color_distance,
    )

    formatted_minimum_region_sizes = ",".join(
        format(
            minimum_region_size_mm,
            "g",
        )
        for minimum_region_size_mm in selected_minimum_region_sizes_mm
    )

    print(
        (
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            "minimum_region_size_mm="
            f"{formatted_minimum_region_sizes}"
        ),
    )

    quantizer = ImageQuantizer(
        color_distance=color_distance,
    )
    detector = RegionDetector()
    resolver = GeneratorConfigResolver()

    compare_multiple_minimum_sizes = len(evaluation_configs) > 1

    for case in args.cases:
        image_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"

        image = load_image(
            image_path,
            DEVELOPER_IMAGE_INPUT_LIMITS,
        )

        image_size = ImageSize(
            width=image.width,
            height=image.height,
        )

        quantized_image = quantizer.quantize(
            image,
            palette,
        )

        detected_regions = detector.detect(
            quantized_image,
        )

        quantized_output_path = stage_preview_output_path(
            output_directory=(args.preview_output_directory),
            case=case,
            stage="quantized",
        )

        detected_output_path = stage_preview_output_path(
            output_directory=(args.preview_output_directory),
            case=case,
            stage="detected",
        )

        write_quantized_preview(
            output_path=quantized_output_path,
            image=quantized_image,
        )

        write_region_preview(
            output_path=detected_output_path,
            regions=detected_regions,
            image_size=image_size,
        )

        print(
            f"  quantized_preview={quantized_output_path}",
        )
        print(
            f"  detected_preview={detected_output_path}",
        )

        for evaluation_config in evaluation_configs:
            minimum_circle_diameter_px = resolver.calculate_minimum_circle_diameter(
                config=evaluation_config,
                image_size=image_size,
            )

            mandatory_regions = RegionMerger().merge(
                detected_regions,
                minimum_circle_diameter_px,
            )

            evaluation = RegionStageEvaluation(
                case=case,
                minimum_region_size_mm=(evaluation_config.minimum_region_size_mm),
                minimum_circle_diameter_px=(minimum_circle_diameter_px),
                detected_region_count=len(
                    detected_regions,
                ),
                mandatory_region_count=len(
                    mandatory_regions,
                ),
            )

            print(
                format_stage_evaluation(
                    evaluation,
                ),
            )

            mandatory_output_path = stage_preview_output_path(
                output_directory=(args.preview_output_directory),
                case=case,
                stage="mandatory-merged",
                minimum_region_size_mm=(
                    evaluation_config.minimum_region_size_mm
                    if compare_multiple_minimum_sizes
                    else None
                ),
            )

            write_region_preview(
                output_path=mandatory_output_path,
                regions=mandatory_regions,
                image_size=image_size,
            )

            print(
                "  mandatory_preview=" f"{mandatory_output_path}",
            )


if __name__ == "__main__":
    main()
