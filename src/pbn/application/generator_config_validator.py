# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import re
from math import isclose, isfinite
from pathlib import Path
from typing import Protocol

from pbn.exceptions import ConfigurationError
from pbn.models import A3, A4

_POINTS_PER_INCH = 72.0
_MILLIMETERS_PER_INCH = 25.4
_HEX_COLOR_PATTERN = re.compile(
    r"#[0-9A-Fa-f]{6}",
)


class PdfLegendConfigView(Protocol):
    """
    Read-only PDF legend configuration required for validation.
    """

    @property
    def pixels_per_inch(self) -> float: ...

    @property
    def points_per_inch(self) -> float: ...

    @property
    def color_field_px(self) -> float: ...

    @property
    def column_count(self) -> int: ...

    @property
    def rows_per_page(self) -> int: ...

    @property
    def start_x_mm(self) -> float: ...

    @property
    def header_y_mm(self) -> float: ...

    @property
    def version_y_mm(self) -> float: ...

    @property
    def table_y_mm(self) -> float: ...

    @property
    def column_width_pt(self) -> float: ...

    @property
    def name_offset_pt(self) -> float: ...

    @property
    def row_height_pt(self) -> float: ...

    @property
    def entry_font_name(self) -> str: ...

    @property
    def entry_number_font_name(self) -> str: ...

    @property
    def entry_font_size_pt(self) -> int: ...

    @property
    def entry_line_height_pt(self) -> float: ...

    @property
    def page(self) -> str: ...

    @property
    def orientation(self) -> str: ...

    @property
    def margin_mm(self) -> float: ...


class RegionMergeCostConfigView(Protocol):
    """
    Read-only merge-cost policy configuration required for validation.
    """

    @property
    def color_weight(self) -> float: ...

    @property
    def affected_area_weight(self) -> float: ...

    @property
    def border_weight(self) -> float: ...

    @property
    def geometry_weight(self) -> float: ...

    @property
    def enclosure_strength(self) -> float: ...

    @property
    def compactness_strength(self) -> float: ...


class RegionComplexityConfigView(Protocol):
    """
    Read-only region-complexity policy configuration required for validation.
    """

    @property
    def reduction_enabled(self) -> bool: ...

    @property
    def max_regions(self) -> int: ...

    @property
    def maximum_merge_cost(self) -> float: ...

    @property
    def merge_cost(self) -> RegionMergeCostConfigView: ...


class ImageInputLimitsConfigView(Protocol):
    """
    Read-only input-limit configuration required for validation.
    """

    @property
    def maximum_pixel_count(self) -> int: ...

    @property
    def maximum_width(self) -> int: ...

    @property
    def maximum_height(self) -> int: ...

    @property
    def processing_pixel_count(self) -> int: ...


class GeneratorConfigView(Protocol):
    """
    Read-only generator configuration required for validation.
    """

    @property
    def page(self) -> str: ...

    @property
    def orientation(self) -> str: ...

    @property
    def placement(self) -> str: ...

    @property
    def margin_mm(self) -> float: ...

    @property
    def palette(self) -> str: ...

    @property
    def palette_version(self) -> int: ...

    @property
    def input_image(self) -> str: ...

    @property
    def output_pdf(self) -> str: ...

    @property
    def region_complexity(self) -> RegionComplexityConfigView: ...

    @property
    def image_input_limits(self) -> ImageInputLimitsConfigView: ...

    @property
    def minimum_region_size_mm(self) -> float: ...

    @property
    def color_distance(self) -> str: ...

    @property
    def parallel_quantization_enabled(self) -> bool: ...

    @property
    def parallel_quantization_break_even_workload(self) -> int: ...

    @property
    def parallel_quantization_max_workers(self) -> int: ...

    @property
    def outline_simplification_enabled(self) -> bool: ...

    @property
    def outline_simplification_tolerance_px(self) -> float: ...

    @property
    def font_size_pt(self) -> int: ...

    @property
    def line_width_pt(self) -> float: ...

    @property
    def line_color(self) -> str: ...

    @property
    def number_color(self) -> str: ...

    @property
    def pdf_legend(self) -> PdfLegendConfigView: ...


class GeneratorConfigValidator:
    """
    Validates application configuration.
    """

    def validate(
        self,
        config: GeneratorConfigView,
    ) -> None:
        self._validate_required_values(
            config,
        )
        self._validate_page(
            config,
        )
        self._validate_orientation(
            config,
        )
        self._validate_placement(
            config,
        )
        self._validate_margin(
            config,
        )
        self._validate_color_distance(
            config,
        )
        self._validate_palette_version(
            config,
        )
        self._validate_generation_parameters(
            config,
        )
        self.validate_region_complexity(
            config.region_complexity,
        )
        self.validate_image_input_limits(
            config.image_input_limits,
        )
        self._validate_output_colors(
            config,
        )
        self._validate_parallel_quantization(
            config,
        )
        self._validate_outline_simplification(
            config,
        )
        self._validate_pdf_legend(
            config,
        )
        self._validate_output(
            config,
        )

    def validate_region_merge_cost(
        self,
        config: RegionMergeCostConfigView,
    ) -> None:
        """
        Validate one complete merge-cost policy configuration.
        """
        self._validate_merge_cost_weights(
            config,
        )
        self._validate_merge_cost_strengths(
            config,
        )

    @staticmethod
    def validate_image_input_limits(
        config: ImageInputLimitsConfigView,
    ) -> None:
        """
        Validate one complete input-limit configuration.

        The bounds are enforced before pixel data is materialized, so a
        limit that cannot bound anything is rejected at configuration time
        rather than at request time.
        """
        positive_values = (
            ("maximum_pixel_count", config.maximum_pixel_count),
            ("maximum_width", config.maximum_width),
            ("maximum_height", config.maximum_height),
            ("processing_pixel_count", config.processing_pixel_count),
        )

        for name, value in positive_values:
            if value < 1:
                raise ConfigurationError(
                    f"{name} must be at least one.",
                )

        if config.processing_pixel_count > config.maximum_pixel_count:
            raise ConfigurationError(
                "processing_pixel_count must not exceed " "maximum_pixel_count.",
            )

        if config.maximum_pixel_count > config.maximum_width * config.maximum_height:
            raise ConfigurationError(
                "maximum_pixel_count must not exceed the product of "
                "maximum_width and maximum_height.",
            )

    def validate_region_complexity(
        self,
        config: RegionComplexityConfigView,
    ) -> None:
        """
        Validate one complete optional region-complexity policy.
        """
        self._validate_region_complexity_policy(
            config,
        )
        self.validate_region_merge_cost(
            config.merge_cost,
        )

    @staticmethod
    def _validate_required_values(
        config: GeneratorConfigView,
    ) -> None:
        if not config.input_image.strip():
            raise ConfigurationError(
                "input_image must not be empty.",
            )

        if not config.output_pdf.strip():
            raise ConfigurationError(
                "output_pdf must not be empty.",
            )

        if not config.palette.strip():
            raise ConfigurationError(
                "palette must not be empty.",
            )

    @staticmethod
    def _validate_page(
        config: GeneratorConfigView,
    ) -> None:
        if config.page not in {
            "A4",
            "A3",
        }:
            raise ConfigurationError(
                f"Unsupported page size: {config.page}",
            )

    @staticmethod
    def _validate_orientation(
        config: GeneratorConfigView,
    ) -> None:
        if config.orientation not in {
            "portrait",
            "landscape",
        }:
            raise ConfigurationError(
                f"Unsupported orientation: {config.orientation}",
            )

    @staticmethod
    def _validate_placement(
        config: GeneratorConfigView,
    ) -> None:
        if config.placement not in {
            "fit",
            "crop",
        }:
            raise ConfigurationError(
                f"Unsupported image placement: {config.placement}",
            )

    @staticmethod
    def _validate_margin(
        config: GeneratorConfigView,
    ) -> None:
        if not isfinite(
            config.margin_mm,
        ):
            raise ConfigurationError(
                "margin_mm must be finite.",
            )

        if config.margin_mm <= 0:
            raise ConfigurationError(
                "margin_mm must be greater than zero.",
            )

        effective_margin_mm = config.margin_mm

        if isfinite(config.line_width_pt) and config.line_width_pt > 0:
            effective_margin_mm += (
                config.line_width_pt * _MILLIMETERS_PER_INCH / _POINTS_PER_INCH / 2.0
            )

        page_size = A4 if config.page == "A4" else A3

        if (
            2.0 * effective_margin_mm >= page_size.width_mm
            or 2.0 * effective_margin_mm >= page_size.height_mm
        ):
            raise ConfigurationError(
                "margin_mm must leave a positive printable area.",
            )

    @staticmethod
    def _validate_color_distance(
        config: GeneratorConfigView,
    ) -> None:
        if config.color_distance not in {
            "delta_e_76",
            "delta_e_2000",
        }:
            raise ConfigurationError(
                "Unsupported color distance: " f"{config.color_distance}",
            )

    @staticmethod
    def _validate_palette_version(
        config: GeneratorConfigView,
    ) -> None:
        if config.palette_version <= 0:
            raise ConfigurationError(
                "palette_version must be greater than zero.",
            )

    @staticmethod
    def _validate_generation_parameters(
        config: GeneratorConfigView,
    ) -> None:
        if not isfinite(
            config.minimum_region_size_mm,
        ):
            raise ConfigurationError(
                "minimum_region_size_mm must be finite.",
            )

        if config.minimum_region_size_mm <= 0:
            raise ConfigurationError(
                "minimum_region_size_mm must be greater than zero.",
            )

        if config.font_size_pt <= 0:
            raise ConfigurationError(
                "font_size_pt must be greater than zero.",
            )

        if not isfinite(
            config.line_width_pt,
        ):
            raise ConfigurationError(
                "line_width_pt must be finite.",
            )

        if config.line_width_pt <= 0:
            raise ConfigurationError(
                "line_width_pt must be greater than zero.",
            )

    @staticmethod
    def _validate_output_colors(
        config: GeneratorConfigView,
    ) -> None:
        color_values = (
            (
                "line_color",
                config.line_color,
            ),
            (
                "number_color",
                config.number_color,
            ),
        )

        for field_name, value in color_values:
            if _HEX_COLOR_PATTERN.fullmatch(value) is None:
                raise ConfigurationError(
                    f"{field_name} must use " "#RRGGBB hexadecimal format.",
                )

    @staticmethod
    def _validate_parallel_quantization(
        config: GeneratorConfigView,
    ) -> None:
        if config.parallel_quantization_break_even_workload <= 0:
            raise ConfigurationError(
                "parallel_quantization_break_even_workload "
                "must be greater than zero.",
            )

        if config.parallel_quantization_max_workers <= 0:
            raise ConfigurationError(
                "parallel_quantization_max_workers " "must be greater than zero.",
            )

    @staticmethod
    def _validate_outline_simplification(
        config: GeneratorConfigView,
    ) -> None:
        if not isfinite(
            config.outline_simplification_tolerance_px,
        ):
            raise ConfigurationError(
                "outline_simplification_tolerance_px must be finite.",
            )

        if config.outline_simplification_tolerance_px < 0.0:
            raise ConfigurationError(
                "outline_simplification_tolerance_px " "must not be negative.",
            )

    @staticmethod
    def _validate_region_complexity_policy(
        config: RegionComplexityConfigView,
    ) -> None:
        if not isinstance(
            config.reduction_enabled,
            bool,
        ):
            raise ConfigurationError(
                "region_complexity.reduction_enabled must be a boolean.",
            )

        if isinstance(
            config.max_regions,
            bool,
        ) or not isinstance(
            config.max_regions,
            int,
        ):
            raise ConfigurationError(
                "region_complexity.max_regions must be an integer.",
            )

        if config.max_regions <= 0:
            raise ConfigurationError(
                "region_complexity.max_regions must be greater than zero.",
            )

        if not isfinite(
            config.maximum_merge_cost,
        ):
            raise ConfigurationError(
                "region_complexity.maximum_merge_cost must be finite.",
            )

        if not 0.0 <= config.maximum_merge_cost <= 1.0:
            raise ConfigurationError(
                "region_complexity.maximum_merge_cost must be " "between 0.0 and 1.0.",
            )

    @staticmethod
    def _validate_merge_cost_weights(
        config: RegionMergeCostConfigView,
    ) -> None:
        weights = (
            (
                "color_weight",
                config.color_weight,
            ),
            (
                "affected_area_weight",
                config.affected_area_weight,
            ),
            (
                "border_weight",
                config.border_weight,
            ),
            (
                "geometry_weight",
                config.geometry_weight,
            ),
        )

        for field_name, value in weights:
            if not isfinite(value):
                raise ConfigurationError(
                    f"merge_cost.{field_name} must be finite.",
                )

            if value < 0.0:
                raise ConfigurationError(
                    f"merge_cost.{field_name} must not be negative.",
                )

        if not isclose(
            sum(value for _, value in weights),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ConfigurationError(
                "merge-cost component weights must sum to 1.0.",
            )

    @staticmethod
    def _validate_merge_cost_strengths(
        config: RegionMergeCostConfigView,
    ) -> None:
        strengths = (
            (
                "enclosure_strength",
                config.enclosure_strength,
            ),
            (
                "compactness_strength",
                config.compactness_strength,
            ),
        )

        for field_name, value in strengths:
            if not isfinite(value):
                raise ConfigurationError(
                    f"merge_cost.{field_name} must be finite.",
                )

            if not 0.0 <= value <= 1.0:
                raise ConfigurationError(
                    f"merge_cost.{field_name} must be " "between 0.0 and 1.0.",
                )

    @staticmethod
    def _validate_pdf_legend(
        config: GeneratorConfigView,
    ) -> None:
        legend = config.pdf_legend

        if legend.page not in {
            "A4",
            "A3",
        }:
            raise ConfigurationError(
                f"Unsupported PDF legend page size: {legend.page}",
            )

        if legend.orientation not in {
            "portrait",
            "landscape",
        }:
            raise ConfigurationError(
                "Unsupported PDF legend orientation: " f"{legend.orientation}",
            )

        if not isfinite(
            legend.margin_mm,
        ):
            raise ConfigurationError(
                "pdf_legend.margin_mm must be finite.",
            )

        if legend.margin_mm <= 0:
            raise ConfigurationError(
                "pdf_legend.margin_mm must be greater than zero.",
            )

        page_size = A4 if legend.page == "A4" else A3

        if (
            2.0 * legend.margin_mm >= page_size.width_mm
            or 2.0 * legend.margin_mm >= page_size.height_mm
        ):
            raise ConfigurationError(
                "pdf_legend.margin_mm must leave " "a positive printable area.",
            )

        positive_float_values = (
            (
                "pixels_per_inch",
                legend.pixels_per_inch,
            ),
            (
                "points_per_inch",
                legend.points_per_inch,
            ),
            (
                "color_field_px",
                legend.color_field_px,
            ),
            (
                "column_width_pt",
                legend.column_width_pt,
            ),
            (
                "row_height_pt",
                legend.row_height_pt,
            ),
            (
                "entry_line_height_pt",
                legend.entry_line_height_pt,
            ),
        )

        for field_name, value in positive_float_values:
            if not isfinite(value):
                raise ConfigurationError(
                    f"pdf_legend.{field_name} must be finite.",
                )

            if value <= 0:
                raise ConfigurationError(
                    f"pdf_legend.{field_name} " "must be greater than zero.",
                )

        positive_integer_values = (
            (
                "column_count",
                legend.column_count,
            ),
            (
                "rows_per_page",
                legend.rows_per_page,
            ),
            (
                "entry_font_size_pt",
                legend.entry_font_size_pt,
            ),
        )

        for field_name, value in positive_integer_values:
            if value <= 0:
                raise ConfigurationError(
                    f"pdf_legend.{field_name} " "must be greater than zero.",
                )

        position_values = (
            (
                "start_x_mm",
                legend.start_x_mm,
            ),
            (
                "header_y_mm",
                legend.header_y_mm,
            ),
            (
                "version_y_mm",
                legend.version_y_mm,
            ),
            (
                "table_y_mm",
                legend.table_y_mm,
            ),
            (
                "name_offset_pt",
                legend.name_offset_pt,
            ),
        )

        for field_name, value in position_values:
            if not isfinite(value):
                raise ConfigurationError(
                    f"pdf_legend.{field_name} must be finite.",
                )

        if not legend.entry_font_name.strip():
            raise ConfigurationError(
                "pdf_legend.entry_font_name must not be empty.",
            )

        if not legend.entry_number_font_name.strip():
            raise ConfigurationError(
                "pdf_legend.entry_number_font_name " "must not be empty.",
            )

    @staticmethod
    def _validate_output(
        config: GeneratorConfigView,
    ) -> None:
        output_path = Path(
            config.output_pdf,
        )

        if not output_path.suffix:
            raise ConfigurationError(
                "output_pdf must specify a file extension.",
            )

        if output_path.suffix.lower() != ".pdf":
            raise ConfigurationError(
                "output_pdf must use the .pdf format.",
            )
