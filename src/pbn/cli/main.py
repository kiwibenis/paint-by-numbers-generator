# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import sys
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import NoReturn

from pbn.application import (
    GeneratorApplication,
    GeneratorConfigValidator,
)
from pbn.application.generator_config_builder import (
    build_config,
    missing_config_values,
)
from pbn.exceptions import (
    ConfigurationError,
    GeometryError,
    PaletteError,
    PbnError,
    PdfExportError,
)
from pbn.infrastructure import (
    ImageLoader,
    PaletteManager,
    build_overlap_detector,
)
from pbn.infrastructure.config_loader import (
    load_config_values,
)
from pbn.infrastructure.overlap_detector_factory import (
    GEOMETRY_LIBRARY,
)
from pbn.infrastructure.pdf_exporter import PdfExporter
from pbn.infrastructure.process_quantization_executor import (
    ProcessQuantizationExecutor,
)

from ..version import __version__
from .contract import (
    exit_code_for,
    report_failure,
    report_palettes,
    report_success,
)


class ConsoleProgressReporter:
    """
    Reports application progress to the command line.
    """

    def report(
        self,
        message: str,
    ) -> None:
        print(
            message,
            file=sys.stderr,
        )


def _parse_boolean(
    value: str,
) -> bool:
    if value == "true":
        return True

    if value == "false":
        return False

    raise ArgumentTypeError(
        "expected 'true' or 'false'",
    )


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="pbn",
        description="Paint By Numbers Generator",
        allow_abbrev=False,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    palettes_parser = subparsers.add_parser(
        "palettes",
        help="List the palettes that can be selected.",
        allow_abbrev=False,
    )

    palettes_parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Write the listing as one JSON object on standard output "
            "instead of one line per palette."
        ),
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate a paint-by-numbers PDF.",
        allow_abbrev=False,
    )

    generate_parser.add_argument(
        "--input",
        help="Input image.",
    )

    generate_parser.add_argument(
        "--output",
        help="Output PDF.",
    )

    generate_parser.add_argument(
        "--page",
        help="Output page size.",
    )

    generate_parser.add_argument(
        "--orientation",
        help="Output orientation.",
    )

    generate_parser.add_argument(
        "--placement",
        help="Image placement mode.",
    )

    generate_parser.add_argument(
        "--margin-mm",
        type=float,
        help="Printer-safe output margin in millimeters.",
    )

    generate_parser.add_argument(
        "--palette",
        help="Reference palette.",
    )

    generate_parser.add_argument(
        "--palette-version",
        type=int,
        help="Reference palette version.",
    )

    generate_parser.add_argument(
        "--region-complexity-reduction-enabled",
        type=_parse_boolean,
        help="Enable optional cost-based region complexity reduction.",
    )

    generate_parser.add_argument(
        "--max-regions",
        type=int,
        help="Target upper region count for optional complexity reduction.",
    )

    generate_parser.add_argument(
        "--maximum-merge-cost",
        type=float,
        help="Maximum acceptable optional region merge cost.",
    )

    generate_parser.add_argument(
        "--merge-cost-color-weight",
        type=float,
        help="Merge-cost color-difference component weight.",
    )

    generate_parser.add_argument(
        "--merge-cost-affected-area-weight",
        type=float,
        help="Merge-cost affected-area component weight.",
    )

    generate_parser.add_argument(
        "--merge-cost-border-weight",
        type=float,
        help="Merge-cost shared-border component weight.",
    )

    generate_parser.add_argument(
        "--merge-cost-geometry-weight",
        type=float,
        help="Merge-cost geometry component weight.",
    )

    generate_parser.add_argument(
        "--merge-cost-enclosure-strength",
        type=float,
        help="Merge-cost enclosure protection strength.",
    )

    generate_parser.add_argument(
        "--merge-cost-compactness-strength",
        type=float,
        help="Merge-cost compactness protection strength.",
    )

    generate_parser.add_argument(
        "--minimum-region-size-mm",
        type=float,
        help="Minimum region size in millimeters.",
    )

    generate_parser.add_argument(
        "--color-distance",
        help="Color distance metric.",
    )

    generate_parser.add_argument(
        "--parallel-quantization-enabled",
        type=_parse_boolean,
        help="Enable automatic parallel quantization selection.",
    )

    generate_parser.add_argument(
        "--parallel-quantization-break-even-workload",
        type=int,
        help="Calibrated parallel quantization break-even workload.",
    )

    generate_parser.add_argument(
        "--parallel-quantization-max-workers",
        type=int,
        help="Maximum worker count for parallel quantization.",
    )

    generate_parser.add_argument(
        "--outline-simplification-enabled",
        type=_parse_boolean,
        help="Enable Douglas-Peucker outline simplification.",
    )

    generate_parser.add_argument(
        "--outline-simplification-tolerance-px",
        type=float,
        help="Douglas-Peucker outline tolerance in pixels.",
    )

    generate_parser.add_argument(
        "--maximum-input-pixel-count",
        type=int,
        help="Maximum accepted input pixel count.",
    )

    generate_parser.add_argument(
        "--maximum-input-width",
        type=int,
        help="Maximum accepted input width in pixels.",
    )

    generate_parser.add_argument(
        "--maximum-input-height",
        type=int,
        help="Maximum accepted input height in pixels.",
    )

    generate_parser.add_argument(
        "--processing-pixel-count",
        type=int,
        help="Pixel count an accepted input is processed at.",
    )

    generate_parser.add_argument(
        "--font-size-pt",
        type=int,
        help="Label font size in points.",
    )

    generate_parser.add_argument(
        "--line-width-pt",
        type=float,
        help="PDF line width in points.",
    )

    generate_parser.add_argument(
        "--line-color",
        help="PBN outline color in #RRGGBB hexadecimal format.",
    )

    generate_parser.add_argument(
        "--number-color",
        help="PBN number color in #RRGGBB hexadecimal format.",
    )

    generate_parser.add_argument(
        "--legend-pixels-per-inch",
        type=float,
        help="Palette legend pixels per inch.",
    )

    generate_parser.add_argument(
        "--legend-points-per-inch",
        type=float,
        help="Palette legend points per inch.",
    )

    generate_parser.add_argument(
        "--legend-color-field-px",
        type=float,
        help="Palette legend color field size in pixels.",
    )

    generate_parser.add_argument(
        "--legend-column-count",
        type=int,
        help="Palette legend column count.",
    )

    generate_parser.add_argument(
        "--legend-rows-per-page",
        type=int,
        help="Palette legend rows per page.",
    )

    generate_parser.add_argument(
        "--legend-start-x-mm",
        type=float,
        help="Palette legend horizontal start position in millimeters.",
    )

    generate_parser.add_argument(
        "--legend-header-y-mm",
        type=float,
        help="Palette legend header position in millimeters.",
    )

    generate_parser.add_argument(
        "--legend-version-y-mm",
        type=float,
        help="Palette legend version position in millimeters.",
    )

    generate_parser.add_argument(
        "--legend-table-y-mm",
        type=float,
        help="Palette legend table position in millimeters.",
    )

    generate_parser.add_argument(
        "--legend-column-width-pt",
        type=float,
        help="Palette legend column width in points.",
    )

    generate_parser.add_argument(
        "--legend-name-offset-pt",
        type=float,
        help="Palette legend name offset in points.",
    )

    generate_parser.add_argument(
        "--legend-row-height-pt",
        type=float,
        help="Palette legend row height in points.",
    )

    generate_parser.add_argument(
        "--legend-entry-font-name",
        help="Palette legend entry font name.",
    )

    generate_parser.add_argument(
        "--legend-entry-number-font-name",
        help="Palette legend number font name.",
    )

    generate_parser.add_argument(
        "--legend-entry-font-size-pt",
        type=int,
        help="Palette legend entry font size in points.",
    )

    generate_parser.add_argument(
        "--legend-entry-line-height-pt",
        type=float,
        help="Palette legend entry line height in points.",
    )

    generate_parser.add_argument(
        "--legend-page",
        help="Palette legend page size.",
    )

    generate_parser.add_argument(
        "--legend-orientation",
        help="Palette legend orientation.",
    )

    generate_parser.add_argument(
        "--legend-margin-mm",
        type=float,
        help="Printer-safe palette legend margin in millimeters.",
    )

    generate_parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Write the outcome as one JSON object on standard output. "
            "Progress and diagnostics stay on standard error."
        ),
    )

    generate_parser.add_argument(
        "--config_file",
        help="Optional fallback configuration file.",
    )

    return parser


def _fail(
    machine_readable: bool,
    error: PbnError,
) -> NoReturn:
    """
    Report a failure and exit with the code it corresponds to.

    One place, so that the exit code is derived from the error rather
    than chosen at each raise site.
    """
    report_failure(
        machine_readable=machine_readable,
        error=error,
    )

    raise SystemExit(
        exit_code_for(error),
    )


def _list_palettes(
    *,
    machine_readable: bool,
) -> None:
    """
    Report the selectable palettes, or why they could not be read.

    A failure here is operational rather than caused by the request:
    there is no request to blame, and the caller supplied nothing that
    could have caused it.
    """
    try:
        palettes = PaletteManager().available_palettes()
    except PbnError as error:
        _fail(
            machine_readable,
            error,
        )

    report_palettes(
        machine_readable=machine_readable,
        palettes=palettes,
    )


def main() -> None:
    parser = build_parser()

    args = parser.parse_args()

    if args.command == "palettes":
        _list_palettes(
            machine_readable=bool(
                getattr(args, "json", False),
            ),
        )

        return

    if args.command == "generate":
        machine_readable: bool = bool(
            getattr(args, "json", False),
        )

        cli_values: dict[str, object | None] = {
            "input_image": args.input,
            "output_pdf": args.output,
            "page": args.page,
            "orientation": args.orientation,
            "placement": args.placement,
            "margin_mm": args.margin_mm,
            "palette": args.palette,
            "palette_version": args.palette_version,
            "region_complexity_reduction_enabled": (
                args.region_complexity_reduction_enabled
            ),
            "max_regions": args.max_regions,
            "maximum_merge_cost": args.maximum_merge_cost,
            "merge_cost_color_weight": args.merge_cost_color_weight,
            "merge_cost_affected_area_weight": (args.merge_cost_affected_area_weight),
            "merge_cost_border_weight": args.merge_cost_border_weight,
            "merge_cost_geometry_weight": args.merge_cost_geometry_weight,
            "merge_cost_enclosure_strength": (args.merge_cost_enclosure_strength),
            "merge_cost_compactness_strength": (args.merge_cost_compactness_strength),
            "minimum_region_size_mm": args.minimum_region_size_mm,
            "color_distance": args.color_distance,
            "parallel_quantization_enabled": (args.parallel_quantization_enabled),
            "parallel_quantization_break_even_workload": (
                args.parallel_quantization_break_even_workload
            ),
            "parallel_quantization_max_workers": (
                args.parallel_quantization_max_workers
            ),
            "outline_simplification_enabled": (args.outline_simplification_enabled),
            "outline_simplification_tolerance_px": (
                args.outline_simplification_tolerance_px
            ),
            "maximum_input_pixel_count": (args.maximum_input_pixel_count),
            "maximum_input_width": args.maximum_input_width,
            "maximum_input_height": args.maximum_input_height,
            "processing_pixel_count": args.processing_pixel_count,
            "font_size_pt": args.font_size_pt,
            "line_width_pt": args.line_width_pt,
            "line_color": args.line_color,
            "number_color": args.number_color,
            "legend_pixels_per_inch": args.legend_pixels_per_inch,
            "legend_points_per_inch": args.legend_points_per_inch,
            "legend_color_field_px": args.legend_color_field_px,
            "legend_column_count": args.legend_column_count,
            "legend_rows_per_page": args.legend_rows_per_page,
            "legend_start_x_mm": args.legend_start_x_mm,
            "legend_header_y_mm": args.legend_header_y_mm,
            "legend_version_y_mm": args.legend_version_y_mm,
            "legend_table_y_mm": args.legend_table_y_mm,
            "legend_column_width_pt": args.legend_column_width_pt,
            "legend_name_offset_pt": args.legend_name_offset_pt,
            "legend_row_height_pt": args.legend_row_height_pt,
            "legend_entry_font_name": args.legend_entry_font_name,
            "legend_entry_number_font_name": (args.legend_entry_number_font_name),
            "legend_entry_font_size_pt": (args.legend_entry_font_size_pt),
            "legend_entry_line_height_pt": (args.legend_entry_line_height_pt),
            "legend_page": args.legend_page,
            "legend_orientation": args.legend_orientation,
            "legend_margin_mm": args.legend_margin_mm,
        }

        explicit_cli_values: dict[str, object] = {
            name: value for name, value in cli_values.items() if value is not None
        }

        try:
            missing_values = missing_config_values(
                explicit_cli_values,
            )

            effective_values: dict[str, object] = dict(
                explicit_cli_values,
            )

            if missing_values and args.config_file is not None:
                toml_values = load_config_values(
                    Path(args.config_file),
                    missing_values,
                )

                effective_values = {
                    **toml_values,
                    **explicit_cli_values,
                }

            config = build_config(
                effective_values,
            )

            GeneratorConfigValidator().validate(
                config,
            )
        except ConfigurationError as exc:
            _fail(machine_readable, exc)

        progress_reporter = ConsoleProgressReporter()

        try:
            palette = PaletteManager().get(
                config.palette,
                config.palette_version,
            )
        except PaletteError as exc:
            _fail(machine_readable, exc)

        pdf_exporter = PdfExporter()
        quantization_executor = ProcessQuantizationExecutor()

        try:
            overlap_detector = build_overlap_detector()
        except GeometryError as exc:
            _fail(machine_readable, exc)

        progress_reporter.report(
            f"Using accelerated outline overlap predicates " f"({GEOMETRY_LIBRARY}).",
        )

        try:
            pdf = GeneratorApplication(
                progress_reporter=progress_reporter,
                quantization_executor=quantization_executor,
                overlap_detector=overlap_detector,
                image_loader=ImageLoader(),
            ).generate_pdf(
                image_path=Path(config.input_image),
                palette=palette,
                config=config,
                pdf_exporter=pdf_exporter,
            )
        except PbnError as exc:
            # Every project error, not an enumerated few: the exit code
            # comes from the attribution of ADR-0019, so a type this
            # does not name still reaches a caller as the right code.
            _fail(machine_readable, exc)

        output_path = Path(
            config.output_pdf,
        )

        try:
            output_path.write_bytes(
                pdf,
            )
        except OSError:
            _fail(
                machine_readable,
                PdfExportError(
                    f"Could not write PDF output: {output_path}",
                ),
            )

        report_success(
            machine_readable=machine_readable,
            output=str(output_path),
        )

        return

    parser.print_help()


if __name__ == "__main__":
    main()
