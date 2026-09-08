# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.models import (
    RGB,
    ImageSize,
    Lab,
    PaletteColor,
    QuantizedImage,
)
from pbn.regions import RegionDetector
from tools.benchmark_region_complexity import (
    build_region_preview_bmp,
)
from tools.evaluate_region_stage_loss import (
    RegionStageEvaluation,
    build_parser,
    build_quantized_preview_bmp,
    format_stage_evaluation,
    stage_preview_output_path,
)


def _color(
    *,
    number: int,
    name: str,
    red: int,
    green: int,
    blue: int,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=name,
        rgb=RGB(
            red=red,
            green=green,
            blue=blue,
        ),
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )


def test_quantized_preview_matches_detected_region_preview() -> None:
    first = _color(
        number=1,
        name="First",
        red=255,
        green=0,
        blue=0,
    )
    second = _color(
        number=2,
        name="Second",
        red=0,
        green=255,
        blue=0,
    )

    image = QuantizedImage.from_rows(
        (
            (
                first,
                second,
            ),
            (
                first,
                second,
            ),
        )
    )

    detected_regions = RegionDetector().detect(
        image,
    )

    quantized_preview = build_quantized_preview_bmp(
        image,
    )
    detected_preview = build_region_preview_bmp(
        regions=detected_regions,
        image_size=ImageSize(
            width=2,
            height=2,
        ),
    )

    assert quantized_preview == detected_preview


@pytest.mark.parametrize(
    (
        "stage",
        "expected_name",
    ),
    (
        (
            "quantized",
            "region-stage-simple-quantized.bmp",
        ),
        (
            "detected",
            "region-stage-simple-detected.bmp",
        ),
        (
            "mandatory-merged",
            "region-stage-simple-mandatory-merged.bmp",
        ),
    ),
)
def test_stage_preview_output_path(
    stage: str,
    expected_name: str,
) -> None:
    output_directory = Path(
        "output",
    )

    assert stage_preview_output_path(
        output_directory=output_directory,
        case="simple",
        stage=stage,
    ) == (output_directory / expected_name)


def test_stage_preview_output_path_includes_minimum_region_size() -> None:
    output_directory = Path(
        "output",
    )

    assert stage_preview_output_path(
        output_directory=output_directory,
        case="simple",
        stage="mandatory-merged",
        minimum_region_size_mm=1.2,
    ) == (
        output_directory
        / ("region-stage-simple-mandatory-merged-" "minimum-region-size-1p2mm.bmp")
    )


def test_stage_preview_output_path_rejects_unknown_stage() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported stage",
    ):
        stage_preview_output_path(
            output_directory=Path(
                "output",
            ),
            case="simple",
            stage="unknown",
        )


def test_format_stage_evaluation_reports_region_counts() -> None:
    evaluation = RegionStageEvaluation(
        case="simple",
        minimum_region_size_mm=1.2,
        minimum_circle_diameter_px=7,
        detected_region_count=123,
        mandatory_region_count=65,
    )

    assert format_stage_evaluation(
        evaluation,
    ) == (
        "simple: "
        "minimum_region_size_mm=1.2, "
        "minimum_circle_diameter_px=7, "
        "detected_regions=123, "
        "mandatory_regions=65"
    )


def test_parser_accepts_multiple_minimum_region_sizes() -> None:
    args = build_parser().parse_args(
        [
            "--minimum-region-size-mm",
            "1.2",
            "2.0",
            "3.0",
        ],
    )

    assert args.minimum_region_size_mm == [
        1.2,
        2.0,
        3.0,
    ]
