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

_NON_FINITE_VALUES = (
    float("nan"),
    float("inf"),
    float("-inf"),
)

_POSITIVE_LEGEND_FLOAT_FIELDS = (
    "pixels_per_inch",
    "points_per_inch",
    "color_field_px",
    "column_width_pt",
    "row_height_pt",
    "entry_line_height_pt",
)

_POSITION_LEGEND_FIELDS = (
    "start_x_mm",
    "header_y_mm",
    "version_y_mm",
    "table_y_mm",
    "name_offset_pt",
)


@pytest.mark.parametrize(
    "value",
    _NON_FINITE_VALUES,
)
def test_validate_rejects_non_finite_minimum_region_size(
    value: float,
) -> None:
    config = create_config(
        minimum_region_size_mm=value,
    )

    with pytest.raises(
        ConfigurationError,
        match="minimum_region_size_mm must be finite",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


@pytest.mark.parametrize(
    "value",
    _NON_FINITE_VALUES,
)
def test_validate_rejects_non_finite_line_width(
    value: float,
) -> None:
    config = create_config(
        line_width_pt=value,
    )

    with pytest.raises(
        ConfigurationError,
        match="line_width_pt must be finite",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


@pytest.mark.parametrize(
    "field_name",
    _POSITIVE_LEGEND_FLOAT_FIELDS,
)
@pytest.mark.parametrize(
    "value",
    _NON_FINITE_VALUES,
)
def test_validate_rejects_non_finite_positive_pdf_legend_value(
    field_name: str,
    value: float,
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
        match=rf"pdf_legend\.{field_name} must be finite",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


@pytest.mark.parametrize(
    "field_name",
    _POSITION_LEGEND_FIELDS,
)
@pytest.mark.parametrize(
    "value",
    _NON_FINITE_VALUES,
)
def test_validate_rejects_non_finite_pdf_legend_position(
    field_name: str,
    value: float,
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
        match=rf"pdf_legend\.{field_name} must be finite",
    ):
        GeneratorConfigValidator().validate(
            config,
        )


def create_region_complexity_config() -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=350,
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
    minimum_region_size_mm: float = 3.0,
    line_width_pt: float = 0.4,
    pdf_legend: PdfLegendConfig | None = None,
) -> GeneratorConfig:
    return GeneratorConfig(
        page="A4",
        orientation="landscape",
        placement="fit",
        margin_mm=10.0,
        palette="reference8",
        palette_version=1,
        input_image="config-image.jpg",
        output_pdf="config-output.pdf",
        region_complexity=create_region_complexity_config(),
        image_input_limits=ImageInputLimitsConfig(
            maximum_pixel_count=50_000_000,
            maximum_width=20_000,
            maximum_height=20_000,
            processing_pixel_count=1_600_000,
        ),
        minimum_region_size_mm=minimum_region_size_mm,
        color_distance="delta_e_76",
        parallel_quantization_enabled=True,
        parallel_quantization_break_even_workload=360_448,
        parallel_quantization_max_workers=8,
        outline_simplification_enabled=True,
        outline_simplification_tolerance_px=1.0,
        font_size_pt=9,
        line_width_pt=line_width_pt,
        line_color="#000000",
        number_color="#000000",
        pdf_legend=(
            pdf_legend if pdf_legend is not None else create_pdf_legend_config()
        ),
    )
