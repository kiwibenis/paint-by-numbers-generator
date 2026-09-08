# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import replace

import pytest

from pbn.application.generator_config_validator import (
    GeneratorConfigValidator,
)
from pbn.config import (
    GeneratorConfig,
    ImageInputLimitsConfig,
    PdfLegendConfig,
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.exceptions import ConfigurationError


def test_validate_accepts_valid_config() -> None:
    config = create_config()

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_accepts_a3_page() -> None:
    config = create_config(
        page="A3",
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_accepts_portrait_orientation() -> None:
    config = create_config(
        orientation="portrait",
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_accepts_crop_placement() -> None:
    config = create_config(
        placement="crop",
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_accepts_a3_landscape_pdf_legend() -> None:
    pdf_legend = replace(
        create_pdf_legend_config(),
        page="A3",
        orientation="landscape",
    )

    config = create_config(
        pdf_legend=pdf_legend,
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_accepts_mixed_case_output_colors() -> None:
    config = create_config(
        line_color="#12abEF",
        number_color="#AbCdEf",
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_rejects_invalid_line_color() -> None:
    config = create_config(
        line_color="000000",
    )

    with pytest.raises(
        ConfigurationError,
        match="line_color must use #RRGGBB hexadecimal format",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_invalid_number_color() -> None:
    config = create_config(
        number_color="#12345G",
    )

    with pytest.raises(
        ConfigurationError,
        match="number_color must use #RRGGBB hexadecimal format",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_empty_input_image() -> None:
    config = create_config(
        input_image="",
    )

    with pytest.raises(
        ConfigurationError,
        match="input_image must not be empty",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_empty_output_pdf() -> None:
    config = create_config(
        output_pdf="",
    )

    with pytest.raises(
        ConfigurationError,
        match="output_pdf must not be empty",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_empty_palette() -> None:
    config = create_config(
        palette="",
    )

    with pytest.raises(
        ConfigurationError,
        match="palette must not be empty",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_unsupported_page() -> None:
    config = create_config(
        page="A5",
    )

    with pytest.raises(
        ConfigurationError,
        match="Unsupported page size",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_unsupported_orientation() -> None:
    config = create_config(
        orientation="diagonal",
    )

    with pytest.raises(
        ConfigurationError,
        match="Unsupported orientation",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_unsupported_placement() -> None:
    config = create_config(
        placement="stretch",
    )

    with pytest.raises(
        ConfigurationError,
        match="Unsupported image placement",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_zero_margin() -> None:
    config = create_config(
        margin_mm=0.0,
    )

    with pytest.raises(
        ConfigurationError,
        match="margin_mm must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_negative_margin() -> None:
    config = create_config(
        margin_mm=-1.0,
    )

    with pytest.raises(
        ConfigurationError,
        match="margin_mm must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


@pytest.mark.parametrize(
    "margin_mm",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_validate_rejects_non_finite_margin(
    margin_mm: float,
) -> None:
    config = create_config(
        margin_mm=margin_mm,
    )

    with pytest.raises(
        ConfigurationError,
        match="margin_mm must be finite",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_margin_without_printable_area() -> None:
    config = create_config(
        page="A4",
        margin_mm=105.0,
    )

    with pytest.raises(
        ConfigurationError,
        match="margin_mm must leave a positive printable area",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_zero_palette_version() -> None:
    config = create_config(
        palette_version=0,
    )

    with pytest.raises(
        ConfigurationError,
        match="palette_version must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_negative_palette_version() -> None:
    config = create_config(
        palette_version=-1,
    )

    with pytest.raises(
        ConfigurationError,
        match="palette_version must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_zero_max_regions() -> None:
    config = create_config(
        max_regions=0,
    )

    with pytest.raises(
        ConfigurationError,
        match="region_complexity.max_regions must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_negative_max_regions() -> None:
    config = create_config(
        max_regions=-1,
    )

    with pytest.raises(
        ConfigurationError,
        match="region_complexity.max_regions must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_accepts_one_max_region() -> None:
    config = create_config(
        max_regions=1,
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_rejects_zero_minimum_region_size() -> None:
    config = create_config(
        minimum_region_size_mm=0.0,
    )

    with pytest.raises(
        ConfigurationError,
        match="minimum_region_size_mm must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_negative_minimum_region_size() -> None:
    config = create_config(
        minimum_region_size_mm=-1.0,
    )

    with pytest.raises(
        ConfigurationError,
        match="minimum_region_size_mm must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_zero_font_size() -> None:
    config = create_config(
        font_size_pt=0,
    )

    with pytest.raises(
        ConfigurationError,
        match="font_size_pt must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_negative_font_size() -> None:
    config = create_config(
        font_size_pt=-1,
    )

    with pytest.raises(
        ConfigurationError,
        match="font_size_pt must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_zero_line_width() -> None:
    config = create_config(
        line_width_pt=0.0,
    )

    with pytest.raises(
        ConfigurationError,
        match="line_width_pt must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_negative_line_width() -> None:
    config = create_config(
        line_width_pt=-0.1,
    )

    with pytest.raises(
        ConfigurationError,
        match="line_width_pt must be greater than zero",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "error_message"),
    (
        (
            "page",
            "A5",
            "Unsupported PDF legend page size",
        ),
        (
            "orientation",
            "diagonal",
            "Unsupported PDF legend orientation",
        ),
        (
            "pixels_per_inch",
            0.0,
            "pdf_legend.pixels_per_inch must be greater than zero",
        ),
        (
            "points_per_inch",
            0.0,
            "pdf_legend.points_per_inch must be greater than zero",
        ),
        (
            "color_field_px",
            0.0,
            "pdf_legend.color_field_px must be greater than zero",
        ),
        (
            "column_count",
            0,
            "pdf_legend.column_count must be greater than zero",
        ),
        (
            "rows_per_page",
            0,
            "pdf_legend.rows_per_page must be greater than zero",
        ),
        (
            "column_width_pt",
            0.0,
            "pdf_legend.column_width_pt must be greater than zero",
        ),
        (
            "row_height_pt",
            0.0,
            "pdf_legend.row_height_pt must be greater than zero",
        ),
        (
            "entry_font_size_pt",
            0,
            "pdf_legend.entry_font_size_pt must be greater than zero",
        ),
        (
            "entry_line_height_pt",
            0.0,
            "pdf_legend.entry_line_height_pt must be greater than zero",
        ),
        (
            "entry_font_name",
            "",
            "pdf_legend.entry_font_name must not be empty",
        ),
        (
            "entry_number_font_name",
            "",
            "pdf_legend.entry_number_font_name must not be empty",
        ),
    ),
)
def test_validate_rejects_invalid_pdf_legend_config(
    field_name: str,
    value: object,
    error_message: str,
) -> None:
    pdf_legend = replace(
        create_pdf_legend_config(),
        # The field is a parameter of the test, so the mapping cannot
        # be matched against the field types. replace raises TypeError
        # on an unknown field, which is what keeps this honest.
        **{field_name: value},  # type: ignore[arg-type]
    )

    config = create_config(
        pdf_legend=pdf_legend,
    )

    with pytest.raises(
        ConfigurationError,
        match=error_message,
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_accepts_pdf_output_with_uppercase_extension() -> None:
    config = create_config(
        output_pdf="result.PDF",
    )

    GeneratorConfigValidator().validate(
        config,
    )


def test_validate_rejects_output_without_extension() -> None:
    config = create_config(
        output_pdf="result",
    )

    with pytest.raises(
        ConfigurationError,
        match="output_pdf must specify a file extension",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def test_validate_rejects_non_pdf_output() -> None:
    config = create_config(
        output_pdf="result.svg",
    )

    with pytest.raises(
        ConfigurationError,
        match="output_pdf must use the .pdf format",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def create_region_complexity_config(
    *,
    max_regions: int = 350,
) -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=max_regions,
        maximum_merge_cost=0.300,
        merge_cost=RegionMergeCostConfig(
            color_weight=0.40,
            affected_area_weight=0.25,
            border_weight=0.15,
            geometry_weight=0.20,
            enclosure_strength=0.50,
            compactness_strength=0.15,
        ),
    )


def create_pdf_legend_config() -> PdfLegendConfig:
    return PdfLegendConfig(
        pixels_per_inch=96.0,
        points_per_inch=72.0,
        color_field_px=30.0,
        column_count=4,
        rows_per_page=17,
        start_x_mm=20.0,
        header_y_mm=285.0,
        version_y_mm=278.0,
        table_y_mm=265.0,
        column_width_pt=118.0,
        name_offset_pt=30.0,
        row_height_pt=42.5,
        entry_font_name="Helvetica",
        entry_number_font_name="Helvetica-Bold",
        entry_font_size_pt=9,
        entry_line_height_pt=9.0,
        page="A4",
        orientation="portrait",
        margin_mm=5.0,
    )


def create_config(
    *,
    page: str = "A4",
    orientation: str = "landscape",
    placement: str = "fit",
    margin_mm: float = 10.0,
    palette: str = "reference8",
    palette_version: int = 1,
    input_image: str = "config-image.jpg",
    output_pdf: str = "config-output.pdf",
    max_regions: int = 350,
    minimum_region_size_mm: float = 3.0,
    color_distance: str = "delta_e_76",
    font_size_pt: int = 9,
    line_width_pt: float = 0.4,
    line_color: str = "#000000",
    number_color: str = "#000000",
    pdf_legend: PdfLegendConfig | None = None,
) -> GeneratorConfig:
    return GeneratorConfig(
        page=page,
        orientation=orientation,
        placement=placement,
        margin_mm=margin_mm,
        palette=palette,
        palette_version=palette_version,
        input_image=input_image,
        output_pdf=output_pdf,
        region_complexity=create_region_complexity_config(
            max_regions=max_regions,
        ),
        image_input_limits=ImageInputLimitsConfig(
            maximum_pixel_count=50_000_000,
            maximum_width=20_000,
            maximum_height=20_000,
            processing_pixel_count=1_600_000,
        ),
        minimum_region_size_mm=minimum_region_size_mm,
        color_distance=color_distance,
        parallel_quantization_enabled=True,
        parallel_quantization_break_even_workload=360_448,
        parallel_quantization_max_workers=8,
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.0,
        font_size_pt=font_size_pt,
        line_width_pt=line_width_pt,
        line_color=line_color,
        number_color=number_color,
        pdf_legend=(
            pdf_legend if pdf_legend is not None else create_pdf_legend_config()
        ),
    )
