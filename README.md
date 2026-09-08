# Paint By Numbers Generator

Generate professional paint-by-numbers templates from photographs.

The project is designed as a Python library.

Applications are responsible for loading configuration files, selecting input
images and writing generated output files.

## Installation

The project requires Python 3.12 or 3.13.

Clone the repository and install it in editable mode from the repository root:

    git clone https://github.com/kiwibenis/paint-by-numbers-generator.git
    cd paint-by-numbers-generator

Create and activate a virtual environment, then install the project:

    python -m venv .venv

On Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

On Linux or macOS:

    source .venv/bin/activate

Install the project:

    python -m pip install --upgrade pip
    python -m pip install -e .

For development, install the optional development dependencies instead:

    python -m pip install -e ".[dev]"

The shipped reference palettes are currently loaded from the repository's
`palettes/` directory relative to the current working directory. Commands that
use these palettes should therefore be run from the repository root.

A first generation can then be started with:

    pbn generate --config_file config/example.toml

## Features

- Vector-based PDF output
- Multiple versioned reference palettes, restricted to printable Latin text
- Automatic numbering
- Several switches to change difficulty
- Secure image processing
- Command-line generation through `pbn generate`
- TOML-based configuration
- Complete command-line configuration
- CLI overrides for every configurable TOML value
- Configurable CIELAB color-distance metrics
- Quality-bounded optional region complexity reduction
- Configurable parallel Delta E 2000 quantization
- Configurable outline simplification
- Mandatory compiled geometry predicates for outline overlap validation
- Configurable PBN page margins
- Configurable outline and number colors

## Project Layout

    src/        Production code
    tests/      Test suite
    docs/       Documentation, including docs/adr/ for accepted decisions
    config/     Shipped configuration profiles
    palettes/   Versioned reference palette data, per docs/palette-format.md
    examples/   Example input images and generated PDFs
    tools/      Developer utilities

Generated example PDFs are stored in `examples/output/` rather than in the
project root.

The example input images are not photographs. Their origin and reuse
considerations are documented in
[`examples/input/README.md`](examples/input/README.md).

## Configuration

The generator can be configured through command-line parameters, an optional
TOML configuration file or a combination of both.

There are no program-internal configuration defaults. The rule and its
consequences are recorded in
[`docs/adr/0030-no-program-internal-configuration-defaults.md`](docs/adr/0030-no-program-internal-configuration-defaults.md).

Every required configuration value must therefore be supplied either through
the CLI or through a TOML configuration file.

An example configuration is provided in:

    config/example.toml

This file serves as a starting point for your own projects.

Instead of modifying the example directly, copy it to a new file, for example:

    config/my-project.toml

This keeps the example configuration unchanged and allows you to maintain
multiple project-specific configurations.

### Configuration File

A configuration file can define the input image, palette, generation settings,
input limits, PDF output settings and palette legend settings.

The current example configuration is:

    [input]

    palette = "reference8"
    palette_version = 1
    input_image = "examples/input/example.png"


    [generation]

    region_complexity_reduction_enabled = true
    max_regions = 350
    maximum_merge_cost = 0.300
    merge_cost_color_weight = 0.40
    merge_cost_affected_area_weight = 0.25
    merge_cost_border_weight = 0.15
    merge_cost_geometry_weight = 0.20
    merge_cost_enclosure_strength = 0.50
    merge_cost_compactness_strength = 0.15
    minimum_region_size_mm = 2.0
    color_distance = "delta_e_2000"

    parallel_quantization_enabled = true
    parallel_quantization_break_even_workload = 557056
    parallel_quantization_max_workers = 8
    outline_simplification_enabled = false
    outline_simplification_tolerance_px = 1.0


    [input_limits]

    # Trusted local profile. A public interface uses a stricter profile;
    # see ADR-0016.
    maximum_pixel_count = 50000000
    maximum_width = 20000
    maximum_height = 20000
    processing_pixel_count = 1600000


    [output]

    page = "A4"
    orientation = "landscape"
    placement = "fit"
    margin_mm = 5.0
    output_pdf = "examples/output/example.pdf"
    font_size_pt = 3
    line_width_pt = 0.1
    line_color = "#000000"
    number_color = "#000000"


    [pdf_legend]

    page = "A4"
    orientation = "portrait"
    margin_mm = 5.0
    pixels_per_inch = 96.0
    points_per_inch = 72.0
    color_field_px = 30.0
    column_count = 4
    rows_per_page = 17
    start_x_mm = 20.0
    header_y_mm = 284.0
    version_y_mm = 284.0
    table_y_mm = 265.0
    column_width_pt = 118.0
    name_offset_pt = 30.0
    row_height_pt = 42.5
    entry_font_name = "Helvetica"
    entry_number_font_name = "Helvetica-Bold"
    entry_font_size_pt = 9
    entry_line_height_pt = 9.0

A TOML configuration file may be complete or partial.

Missing TOML values can be supplied directly through the command line.

### Output Configuration

The `[output]` section controls the PBN page and its rendered content.

`page` and `orientation` define the physical PBN page.

`placement` controls how the input image is placed on that page.

`margin_mm` defines the printer-safe margin around the generated PBN content
in millimeters. Outlines and numbers are constrained to the printable area
inside this margin.

For example:

    [output]

    margin_mm = 5.0

The same value can be supplied or overridden through the CLI:

    --margin-mm 5.0

`font_size_pt` controls the size of the region numbers in points.

`line_width_pt` controls the width of the region outlines in points.

`line_color` controls the color used for region outlines.

`number_color` controls the color used for region numbers.

Both color values use the exact `#RRGGBB` hexadecimal format. Uppercase and
lowercase hexadecimal digits are accepted.

For example:

    [output]

    font_size_pt = 3
    line_width_pt = 0.1
    line_color = "#000000"
    number_color = "#000000"

The corresponding CLI parameters are:

    --font-size-pt 3
    --line-width-pt 0.1
    --line-color "#000000"
    --number-color "#000000"

### Region Complexity Configuration

Region processing uses two separate concepts:

1. mandatory physical paintability;
2. optional quality-bounded region complexity reduction.

`minimum_region_size_mm` defines mandatory physical paintability. It specifies
the minimum physical diameter of a circle that must fit completely inside a
region.

Mandatory paintability processing is always active. Optional complexity
settings cannot disable, weaken or replace the `minimum_region_size_mm`
constraint.

Optional complexity reduction is controlled through these required generation
configuration values:

    region_complexity_reduction_enabled
    max_regions
    maximum_merge_cost
    merge_cost_color_weight
    merge_cost_affected_area_weight
    merge_cost_border_weight
    merge_cost_geometry_weight
    merge_cost_enclosure_strength
    merge_cost_compactness_strength

`region_complexity_reduction_enabled` controls only the optional cost-based
complexity-reduction stage.

When it is `false`, optional complexity reduction is skipped. Mandatory
paintability processing based on `minimum_region_size_mm` remains active.

`max_regions` defines the target upper region count for optional complexity
reduction.

It is a target rather than an exact required result. The reducer does not force
additional merges solely to reach `max_regions`.

A valid result may therefore contain more regions than `max_regions` when no
further merge satisfies the configured quality boundary.

`maximum_merge_cost` defines that quality boundary.

Optional complexity reduction stops when either:

1. the current region count is less than or equal to `max_regions`; or
2. the cheapest available optional merge exceeds `maximum_merge_cost`.

Zero accepted optional merges are valid when no candidate satisfies the
quality boundary.

The four merge-cost component weights are:

    merge_cost_color_weight
    merge_cost_affected_area_weight
    merge_cost_border_weight
    merge_cost_geometry_weight

They must be finite, non-negative values and their sum must equal `1.0`.

The two detail-protection strengths are:

    merge_cost_enclosure_strength
    merge_cost_compactness_strength

They must be finite values between `0.0` and `1.0`, inclusive.

The current evaluated policy used by `config/example.toml` is:

    [generation]

    region_complexity_reduction_enabled = true
    max_regions = 350
    maximum_merge_cost = 0.300
    merge_cost_color_weight = 0.40
    merge_cost_affected_area_weight = 0.25
    merge_cost_border_weight = 0.15
    merge_cost_geometry_weight = 0.20
    merge_cost_enclosure_strength = 0.50
    merge_cost_compactness_strength = 0.15
    minimum_region_size_mm = 2.0

`maximum_merge_cost = 0.300` is the shipped quality boundary for the
merge-cost formulation and the component weights and protection strengths
shown above.

These values are normal generation configuration values. They are not hidden
Core defaults.

All region-complexity policy values remain required even when
`region_complexity_reduction_enabled` is `false`. When optional complexity
reduction is disabled, the optional policy does not influence generation
behavior, while mandatory `minimum_region_size_mm` processing continues
normally.

The corresponding CLI parameters are:

    --region-complexity-reduction-enabled true
    --max-regions 350
    --maximum-merge-cost 0.300
    --merge-cost-color-weight 0.40
    --merge-cost-affected-area-weight 0.25
    --merge-cost-border-weight 0.15
    --merge-cost-geometry-weight 0.20
    --merge-cost-enclosure-strength 0.50
    --merge-cost-compactness-strength 0.15
    --minimum-region-size-mm 2.0

Explicit CLI values override the corresponding TOML values.

For example, when the TOML file already contains a complete complexity policy,
only the region-count target can be overridden:

    pbn generate \
        --config_file config/my-project.toml \
        --max-regions 275

The remaining complexity-control values continue to come from the TOML file.
Region-count control is represented by `max_regions` and is always bounded
by `maximum_merge_cost`.

### Input Limit Configuration

The `[input_limits]` section bounds what the generator accepts and how much
work an accepted input causes. It is the section a deployment processing
untrusted input tunes, and ADR-0016 defines what it protects.

All four values are required:

    maximum_pixel_count
    maximum_width
    maximum_height
    processing_pixel_count

`maximum_pixel_count`, `maximum_width` and `maximum_height` decide whether an
image is accepted at all. They are checked against the declared dimensions in
the file header, before any pixel data is allocated, so an oversized input is
refused without being decoded.

`processing_pixel_count` does not reject anything. An accepted image whose
pixel count exceeds it is reduced proportionally before normalized pixel data
is produced. An image already at or below it keeps its dimensions.

`processing_pixel_count` must not exceed `maximum_pixel_count`. A profile that
violates this is refused as a configuration error before any input is read.

For example:

    [input_limits]

    maximum_pixel_count = 50000000
    maximum_width = 20000
    maximum_height = 20000
    processing_pixel_count = 1600000

The same values can be supplied or overridden through the CLI:

    --maximum-input-pixel-count 50000000
    --maximum-input-width 20000
    --maximum-input-height 20000
    --processing-pixel-count 1600000

The two shipped profiles differ in this section and nowhere else.
`config/example.toml` is a trusted local profile. `config/untrusted.toml` is
the reference profile for a caller-facing deployment and refuses larger
inputs, in exactly three values:

    maximum_pixel_count   40000000  against  50000000
    maximum_width            10000  against     20000
    maximum_height           10000  against     20000

`processing_pixel_count` is the same in both, because the work an accepted
image causes does not depend on how much the deployment is willing to accept.

What the profile does is bound what is accepted. What it does not do is
bound what an accepted input then costs: this project enforces no limit on
its own wall-clock time or memory, and choosing `config/untrusted.toml` does
not change that. ADR-0016 places those limits at the integration boundary,
and a deployment has to impose them itself with `ulimit`, a job object or a
container. `docs/integration-contract.md` gives the measured figures to size
them with.

### Outline Simplification Configuration

Outline simplification is controlled through two required generation
configuration values:

    outline_simplification_enabled
    outline_simplification_tolerance_px

`outline_simplification_enabled` controls whether generated region outlines
are simplified.

`outline_simplification_tolerance_px` defines the simplification tolerance in
input-image pixels.

For example:

    [generation]

    outline_simplification_enabled = true
    outline_simplification_tolerance_px = 1.0

The same values can be supplied or overridden through the CLI:

    --outline-simplification-enabled true
    --outline-simplification-tolerance-px 1.0

### Color Distance Configuration

`color_distance` is an active and required generation parameter. It selects
the color-distance metric used when matching normalized image colors to the
configured reference palette.

Supported values are:

- `delta_e_76` - Euclidean distance in the CIELAB color space.
- `delta_e_2000` - CIEDE2000 color difference with perceptual corrections for
  lightness, chroma and hue.

The configured metric can change which palette color is selected for a source
color and can therefore affect the resulting quantized image and region
structure.

The project does not provide a configuration default for this value. It must
be supplied explicitly through TOML or the CLI.

The example configuration uses:

    color_distance = "delta_e_2000"

Implementation details for the supported color-distance metrics are documented
in:

    docs/algorithms/delta-e-76.md
    docs/algorithms/delta-e-2000.md

### Parallel Quantization Configuration

Parallel quantization is controlled through three required generation
configuration values:

    parallel_quantization_enabled
    parallel_quantization_break_even_workload
    parallel_quantization_max_workers

`parallel_quantization_enabled` controls whether the automatic parallel
quantization policy may use worker processes.

When it is `false`, quantization always uses the sequential path regardless of
the configured color-distance metric, workload, palette size or worker
settings.

When it is `true`, parallel quantization is currently eligible only for
`delta_e_2000`.

`delta_e_76` remains sequential even when parallel quantization is enabled.

For eligible Delta E 2000 quantization, the estimated workload is:

    unique RGB color count * palette color count

`parallel_quantization_break_even_workload` defines the system-specific
workload at which the calibrated parallel path becomes eligible.

`parallel_quantization_max_workers` limits the number of worker processes that
may be used. The effective worker count is additionally bounded by available
CPU resources and the number of independent work units.

These values are required configuration values. They must be supplied through
TOML or the CLI.

For example:

    [generation]

    color_distance = "delta_e_2000"
    parallel_quantization_enabled = true
    parallel_quantization_break_even_workload = 557056
    parallel_quantization_max_workers = 8

The break-even workload and maximum worker count are system-specific. The
values above are examples and should be replaced with recommendations produced
by the quantization calibration tool for the target system.

### One-Time Quantization Calibration

Parallel quantization performance depends on the target system.

Before using parallel Delta E 2000 quantization on a new target system, run
the quantization calibration tool once to determine suitable values for:

    parallel_quantization_break_even_workload
    parallel_quantization_max_workers

Run the calibration from the repository root:

    python tools/benchmark_quantization.py --runs 3 --max-workers 16

`--runs` controls how many measurements are collected for each calibration
point.

`--max-workers` defines the largest worker count that the calibration may
evaluate. The actual worker counts are bounded by the CPU resources available
on the target system.

The calibration uses deterministic synthetic quantization workloads and
Delta E 2000. It evaluates palette-size scaling and worker-count scaling to
determine when process-based quantization provides a meaningful benefit.

At the end of the calibration, the tool reports recommendations in this form:

    recommended_parallel_quantization_break_even_workload=557056 (minimum_speedup=1.25x)
    recommended_parallel_quantization_max_workers=8 (minimum_incremental_speedup=1.05x, stable_points=3)

The numeric values depend on the target system. The values shown above are
examples.

Transfer the reported values into the `[generation]` section of the TOML
configuration:

    [generation]

    color_distance = "delta_e_2000"
    parallel_quantization_enabled = true
    parallel_quantization_break_even_workload = 557056
    parallel_quantization_max_workers = 8

The same recommendations can be supplied directly through the CLI:

    --color-distance delta_e_2000
    --parallel-quantization-enabled true
    --parallel-quantization-break-even-workload 557056
    --parallel-quantization-max-workers 8

Explicit CLI values override corresponding TOML values according to the normal
configuration precedence rules.

Calibration does not modify configuration files and does not automatically
apply its recommendations. Transfer the reported values explicitly into the
configuration or CLI values used for generation.

Calibration should be repeated when moving generation to a different target
system or after a hardware or runtime change that can materially affect
process-based quantization performance.

### Disabling Parallel Quantization

Parallel quantization can be disabled explicitly through TOML:

    [generation]

    parallel_quantization_enabled = false
    parallel_quantization_break_even_workload = 557056
    parallel_quantization_max_workers = 8

With `parallel_quantization_enabled = false`, generation uses sequential
quantization unconditionally.

The break-even workload and maximum worker count remain required configuration
values even while parallel quantization is disabled, but they do not influence
execution-path selection while the enable flag is `false`.

Parallel quantization can also be disabled through the CLI:

    --parallel-quantization-enabled false \
    --parallel-quantization-break-even-workload 557056 \
    --parallel-quantization-max-workers 8

When a TOML file already supplies the two numeric values, only the enable flag
needs to be overridden:

    pbn generate \
        --config_file config/my-project.toml \
        --parallel-quantization-enabled false

Because explicit CLI values have priority, this disables parallel quantization
even when the TOML file enables it.

### Palette Legend Configuration

The `[pdf_legend]` section controls the palette legend independently from the
PBN page.

The legend page and orientation are configured through:

    page
    orientation

The printer-safe legend margin is configured independently through:

    margin_mm

The remaining values control legend layout, typography and spacing:

    pixels_per_inch
    points_per_inch
    color_field_px
    column_count
    rows_per_page
    start_x_mm
    header_y_mm
    version_y_mm
    table_y_mm
    column_width_pt
    name_offset_pt
    row_height_pt
    entry_font_name
    entry_number_font_name
    entry_font_size_pt
    entry_line_height_pt

The PBN margin and palette legend margin are independent configuration values.

For example:

    [output]

    margin_mm = 5.0

    [pdf_legend]

    margin_mm = 5.0

The corresponding CLI parameters are:

    --margin-mm 5.0
    --legend-margin-mm 5.0

### Loading a Configuration

Configuration files are loaded using the `load_config()` function.

You **do not** modify any file inside the `src/` directory.

Instead, create your own Python script that uses the library.

For example, create a file called:

    generate.py

Inside this file, load your configuration:

    from pathlib import Path

    from pbn.infrastructure import load_config

    config = load_config(
        Path("config/my-project.toml"),
    )

    print(config)

The path passed to `load_config()` determines which configuration file is
loaded.

For example:

    Path("config/example.toml")

loads the example configuration, while:

    Path("config/my-project.toml")

loads your own project-specific configuration.

### Example Workflow

A typical library workflow looks like this:

1. Copy `config/example.toml` to `config/my-project.toml`.
2. Adjust the configuration values for your project.
3. Run the one-time quantization calibration when parallel Delta E 2000
   quantization will be used on a new target system.
4. Transfer the reported parallel quantization recommendations into the
   configuration.
5. Load the configuration using `load_config()`.
6. Pass the resulting `GeneratorConfig` object to the generator.

The library classes have no defaults of their own either. A constructor or
method that takes a value the configuration owns requires it, so a call
states the policy it runs under and cannot silently differ from the profile
next to it. See
[ADR-0030](docs/adr/0030-no-program-internal-configuration-defaults.md).

## Command Line

The project also provides the `pbn` command-line application.

The main generation command is:

    pbn generate

The CLI resolves configuration values before generation.

Explicit command-line values always have the highest priority.

A TOML configuration file is optional and acts only as a fallback source for
values that were not explicitly supplied through the CLI.

There are no program-internal defaults, on the command line or in the
library. The effective configuration must be complete before generation can
start.

### Generate from a Configuration File

A complete configuration file can be used without additional generation
parameters:

    pbn generate --config_file config/example.toml

For example:

    pbn generate --config_file config/my-project.toml

The configuration file can provide the input image, output path, palette,
generation parameters, input limits, PDF settings and palette legend settings.

### Generate from CLI Parameters Only

A configuration file is not required when every required configuration value
is supplied directly through the command line.

A complete CLI-only configuration corresponding to the current
`config/example.toml` is:

    pbn generate \
        --input examples/input/example.png \
        --palette reference8 \
        --palette-version 1 \
        --region-complexity-reduction-enabled true \
        --max-regions 350 \
        --maximum-merge-cost 0.300 \
        --merge-cost-color-weight 0.40 \
        --merge-cost-affected-area-weight 0.25 \
        --merge-cost-border-weight 0.15 \
        --merge-cost-geometry-weight 0.20 \
        --merge-cost-enclosure-strength 0.50 \
        --merge-cost-compactness-strength 0.15 \
        --minimum-region-size-mm 2.0 \
        --color-distance delta_e_2000 \
        --parallel-quantization-enabled true \
        --parallel-quantization-break-even-workload 557056 \
        --parallel-quantization-max-workers 8 \
        --outline-simplification-enabled false \
        --outline-simplification-tolerance-px 1.0 \
        --maximum-input-pixel-count 50000000 \
        --maximum-input-width 20000 \
        --maximum-input-height 20000 \
        --processing-pixel-count 1600000 \
        --page A4 \
        --orientation landscape \
        --placement fit \
        --margin-mm 5.0 \
        --output examples/output/example.pdf \
        --font-size-pt 3 \
        --line-width-pt 0.1 \
        --line-color "#000000" \
        --number-color "#000000" \
        --legend-page A4 \
        --legend-orientation portrait \
        --legend-margin-mm 5.0 \
        --legend-pixels-per-inch 96.0 \
        --legend-points-per-inch 72.0 \
        --legend-color-field-px 30.0 \
        --legend-column-count 4 \
        --legend-rows-per-page 17 \
        --legend-start-x-mm 20.0 \
        --legend-header-y-mm 284.0 \
        --legend-version-y-mm 284.0 \
        --legend-table-y-mm 265.0 \
        --legend-column-width-pt 118.0 \
        --legend-name-offset-pt 30.0 \
        --legend-row-height-pt 42.5 \
        --legend-entry-font-name Helvetica \
        --legend-entry-number-font-name Helvetica-Bold \
        --legend-entry-font-size-pt 9 \
        --legend-entry-line-height-pt 9.0

If any required value is missing and no configuration file can supply it,
generation stops with a configuration error.

### Combine CLI and TOML Configuration

A partial command-line configuration can be combined with a TOML file.

For example:

    pbn generate \
        --config_file config/my-project.toml \
        --output examples/output/override.pdf \
        --page A3

The CLI values are used directly.

Only values that are missing from the CLI are obtained from the TOML
configuration.

CLI values always take precedence over corresponding TOML values.

### Command-Line Parameters

The `generate` command supports the following general parameters:

    --input
    --output
    --page
    --orientation
    --placement
    --margin-mm
    --palette
    --palette-version
    --region-complexity-reduction-enabled
    --max-regions
    --maximum-merge-cost
    --merge-cost-color-weight
    --merge-cost-affected-area-weight
    --merge-cost-border-weight
    --merge-cost-geometry-weight
    --merge-cost-enclosure-strength
    --merge-cost-compactness-strength
    --minimum-region-size-mm
    --color-distance
    --parallel-quantization-enabled
    --parallel-quantization-break-even-workload
    --parallel-quantization-max-workers
    --outline-simplification-enabled
    --outline-simplification-tolerance-px
    --maximum-input-pixel-count
    --maximum-input-width
    --maximum-input-height
    --processing-pixel-count
    --font-size-pt
    --line-width-pt
    --line-color
    --number-color
    --config_file

Palette legend configuration can be supplied with:

    --legend-page
    --legend-orientation
    --legend-margin-mm
    --legend-pixels-per-inch
    --legend-points-per-inch
    --legend-color-field-px
    --legend-column-count
    --legend-rows-per-page
    --legend-start-x-mm
    --legend-header-y-mm
    --legend-version-y-mm
    --legend-table-y-mm
    --legend-column-width-pt
    --legend-name-offset-pt
    --legend-row-height-pt
    --legend-entry-font-name
    --legend-entry-number-font-name
    --legend-entry-font-size-pt
    --legend-entry-line-height-pt

The command-line parameters correspond directly to configuration values.

The complete mapping is:

| TOML section | TOML value | CLI parameter |
| --- | --- | --- |
| `[input]` | `palette` | `--palette` |
| `[input]` | `palette_version` | `--palette-version` |
| `[input]` | `input_image` | `--input` |
| `[generation]` | `region_complexity_reduction_enabled` | `--region-complexity-reduction-enabled` |
| `[generation]` | `max_regions` | `--max-regions` |
| `[generation]` | `maximum_merge_cost` | `--maximum-merge-cost` |
| `[generation]` | `merge_cost_color_weight` | `--merge-cost-color-weight` |
| `[generation]` | `merge_cost_affected_area_weight` | `--merge-cost-affected-area-weight` |
| `[generation]` | `merge_cost_border_weight` | `--merge-cost-border-weight` |
| `[generation]` | `merge_cost_geometry_weight` | `--merge-cost-geometry-weight` |
| `[generation]` | `merge_cost_enclosure_strength` | `--merge-cost-enclosure-strength` |
| `[generation]` | `merge_cost_compactness_strength` | `--merge-cost-compactness-strength` |
| `[generation]` | `minimum_region_size_mm` | `--minimum-region-size-mm` |
| `[generation]` | `color_distance` | `--color-distance` |
| `[generation]` | `parallel_quantization_enabled` | `--parallel-quantization-enabled` |
| `[generation]` | `parallel_quantization_break_even_workload` | `--parallel-quantization-break-even-workload` |
| `[generation]` | `parallel_quantization_max_workers` | `--parallel-quantization-max-workers` |
| `[generation]` | `outline_simplification_enabled` | `--outline-simplification-enabled` |
| `[generation]` | `outline_simplification_tolerance_px` | `--outline-simplification-tolerance-px` |
| `[input_limits]` | `maximum_pixel_count` | `--maximum-input-pixel-count` |
| `[input_limits]` | `maximum_width` | `--maximum-input-width` |
| `[input_limits]` | `maximum_height` | `--maximum-input-height` |
| `[input_limits]` | `processing_pixel_count` | `--processing-pixel-count` |
| `[output]` | `page` | `--page` |
| `[output]` | `orientation` | `--orientation` |
| `[output]` | `placement` | `--placement` |
| `[output]` | `margin_mm` | `--margin-mm` |
| `[output]` | `output_pdf` | `--output` |
| `[output]` | `font_size_pt` | `--font-size-pt` |
| `[output]` | `line_width_pt` | `--line-width-pt` |
| `[output]` | `line_color` | `--line-color` |
| `[output]` | `number_color` | `--number-color` |
| `[pdf_legend]` | `page` | `--legend-page` |
| `[pdf_legend]` | `orientation` | `--legend-orientation` |
| `[pdf_legend]` | `margin_mm` | `--legend-margin-mm` |
| `[pdf_legend]` | `pixels_per_inch` | `--legend-pixels-per-inch` |
| `[pdf_legend]` | `points_per_inch` | `--legend-points-per-inch` |
| `[pdf_legend]` | `color_field_px` | `--legend-color-field-px` |
| `[pdf_legend]` | `column_count` | `--legend-column-count` |
| `[pdf_legend]` | `rows_per_page` | `--legend-rows-per-page` |
| `[pdf_legend]` | `start_x_mm` | `--legend-start-x-mm` |
| `[pdf_legend]` | `header_y_mm` | `--legend-header-y-mm` |
| `[pdf_legend]` | `version_y_mm` | `--legend-version-y-mm` |
| `[pdf_legend]` | `table_y_mm` | `--legend-table-y-mm` |
| `[pdf_legend]` | `column_width_pt` | `--legend-column-width-pt` |
| `[pdf_legend]` | `name_offset_pt` | `--legend-name-offset-pt` |
| `[pdf_legend]` | `row_height_pt` | `--legend-row-height-pt` |
| `[pdf_legend]` | `entry_font_name` | `--legend-entry-font-name` |
| `[pdf_legend]` | `entry_number_font_name` | `--legend-entry-number-font-name` |
| `[pdf_legend]` | `entry_font_size_pt` | `--legend-entry-font-size-pt` |
| `[pdf_legend]` | `entry_line_height_pt` | `--legend-entry-line-height-pt` |

### Configuration Source Precedence

Explicit CLI values always have the highest priority.

For every required configuration value, resolution follows this order:

1. Use the explicitly supplied CLI value when present.
2. Otherwise use the corresponding TOML value when a configuration file is
   needed and available.
3. If neither source supplies the value, report a configuration error.

No program-internal defaults are used.

If every required value is already supplied through the CLI, the TOML
configuration file is not loaded, even when `--config_file` was also
specified.

For example:

    pbn generate \
        <complete CLI configuration> \
        --config_file missing.toml

does not require `missing.toml`, because all effective values already come
from the CLI.

If one or more CLI values are missing, the TOML file is used only as a
fallback source for those missing values.

For example, if the configuration contains:

    [output]

    page = "A4"
    output_pdf = "examples/output/example.pdf"

and the CLI contains:

    --page A3

the effective page value is `A3`.

The TOML value for `page` is not used because the explicit CLI value wins.

An invalid TOML value can therefore be irrelevant when the same configuration
value is explicitly supplied with a valid CLI value.

For example:

    [output]

    page = 123

combined with:

    --page A3

uses the valid CLI value `A3`.

The invalid TOML value for `page` is not part of the effective configuration.

The reverse does not apply. An invalid CLI value is never replaced by a valid
TOML value.

For example:

    [output]

    page = "A4"

combined with:

    --page A5

fails configuration validation because the explicit CLI value has priority.

A syntactically invalid TOML file cannot be repaired by CLI values when the
file is required as a fallback source, because the TOML document itself
cannot be parsed reliably.

### Input Images

The generator validates and normalizes input images before they enter the
generation pipeline.

The supported image formats are:

- BMP;
- JPEG;
- PNG;
- WEBP.

Image format is determined from the file content rather than trusted solely
from the file extension.

RAW, DNG and TIFF input are not supported.

A JPEG carrying auxiliary frames is accepted through the narrow JPEG-specific
exception defined by ADR-0016. Recent phones may attach a gain map or depth map
through an MPF index, causing the imaging library to report the file as `MPO`
rather than `JPEG`.

Such a file is accepted only when its filename claims JPEG and its MPF index
declares a JPEG primary image. Only the primary frame is used; auxiliary frames
are never decoded.

Invalid, unsupported or unreadable image input is reported as an image error
by the CLI.

### Palettes

**Listing what can be selected.** `pbn palettes` reports the palettes a
generation may select, one per line:

    amsterdamStandardRoyalTalents24 v1  Amsterdam Standard Series 24 (Royal Talens, 24 colors)
    faberCastellPolychromos60 v1  Polychromos 60 (Faber-Castell, 60 colors)

With `--json` it writes one object on standard output instead:

    {"palettes": [{"color_count": 24,
                   "display_name": "Amsterdam Standard Series 24",
                   "id": "amsterdamStandardRoyalTalents24",
                   "manufacturer": "Royal Talens",
                   "version": 1}],
     "status": "succeeded"}

Every listed palette loads, because listing loads it. A document that
does not load is skipped rather than reported, so one broken palette
does not hide the working ones.

A missing palette directory is a failure with exit code 70, not an empty
listing. The directory is relative to the working directory, so an empty
result would make running from the wrong place indistinguishable from a
deployment with no palettes installed. An existing but empty directory
does report an empty listing, which is the true statement.

A palette is a JSON document under `palettes/`, named
`<id>-v<version>.json`. It declares an identifier, a manufacturer, a
display name, a version, and up to 256 colors, each with a number, a
name and an RGB triple. The `palette` and `palette_version` values
select one; a caller cannot supply a document.

The description above is an orientation.
[`docs/palette-format.md`](docs/palette-format.md) defines the format
completely: the exact shape of a document, every field and every bound
the loader enforces. A palette that satisfies it loads.

**Palette text is restricted to characters the legend can print.** That
is the WinAnsi character set of the built-in fonts the legend is drawn
with, minus the control characters, covering the Latin alphabet with its
accents plus the common punctuation and currency signs. `Grün`,
`Bleu Céruleum` and `Niño` are accepted; Cyrillic, Greek, CJK and emoji
are not. The format document states how many characters that is and
holds the number against the renderer.

The restriction exists because the PDF library does not refuse a
character it cannot draw. It substitutes a symbol from an unrelated
font, without an error and without a trace in the output, and a legend
of substituted symbols no longer states which pencil a number means. A
palette document containing one is therefore rejected when it is loaded,
naming the offending code points:

    colors[0].name contains characters the generated legend cannot
    render: U+041F, U+0443.

Supporting a wider script is not a matter of lifting the check. It needs
an embedded font that can draw it, which is a decision this project has
not taken.

### PDF Output

The `generate` command produces a PDF document containing the generated
paint-by-numbers template and its configured palette legend.

The output path is controlled by the effective `output_pdf` value.

It can be supplied through TOML:

    [output]

    output_pdf = "examples/output/example.pdf"

or directly through the CLI:

    pbn generate \
        --config_file config/example.toml \
        --output examples/output/example.pdf

The configured output path is used for the generated PDF.

The PBN page geometry is controlled independently through `page` and
`orientation`, while the legend geometry is controlled through
`pdf_legend.page` and `pdf_legend.orientation`.

Their corresponding CLI parameters are:

    --page
    --orientation
    --legend-page
    --legend-orientation

The PBN page and palette legend have independent printer-safe margins.

The PBN margin is controlled through:

    [output]
    margin_mm = 5.0

The palette legend margin is controlled through:

    [pdf_legend]
    margin_mm = 5.0

Their corresponding CLI parameters are:

    --margin-mm
    --legend-margin-mm

The PBN outline and number colors are controlled independently through
`line_color` and `number_color`.

Their corresponding CLI parameters are:

    --line-color
    --number-color

Both color values must use the exact `#RRGGBB` hexadecimal format.

The generator writes PDF output only. The outlines and labels are held in a
format-independent vector document before export; that model is an
implementation detail and is never serialized to any other format. ADR-0027
records why PDF is the only output.

Generated files should be placed in an appropriate output directory rather
than in the project root.

### Progress Reporting

The CLI reports progress while generating a PDF.

The current progress stages include:

    Loading input image.
    Generating paint-by-numbers document.
    Exporting PDF document.

Progress messages are written to the command-line error stream so that normal
command output remains separate from progress reporting.

### CLI Help

General help is available with:

    pbn --help

Help for the generation command is available with:

    pbn generate --help

The CLI also supports:

    pbn --version

to display the installed project version.

## Getting Started

For command-line generation, start with:

    pbn generate --config_file config/example.toml

When using parallel Delta E 2000 quantization on a new target system, run the
one-time quantization calibration first and transfer its recommendations into
the generation configuration.

### Geometry Acceleration

Outline overlap validation uses compiled geometry predicates. The geometry
library is a mandatory runtime dependency and is installed with the project.

Normal generation requires the accelerated implementation. If the geometry
library is missing or cannot be loaded, generation fails rather than silently
falling back to the pure Python implementation.

The pure Python implementation remains in the Core as executable reference
behavior for differential tests and developer diagnostics. It is not a
production fallback.

The accelerated implementation must preserve the overlap semantics defined by
the reference implementation. Representative benchmarks showed substantial
end-to-end improvements, and the measurements are recorded in
`docs/geometry-acceleration-evaluation.md`, together with the equivalence
requirements and the conditions that require revalidating them. The measured
ratio differs materially between machines, so that document records
representative measurements rather than one speedup factor.

ADR-0015 defines the architectural decision.

## Integrating

The generator is a Python library with a command line interface, per the
vision. A front end in any language starts a process; a Python caller
imports the package.

    pbn generate --input photo.jpg --output template.pdf \
                 --config_file config/untrusted.toml --json

With `--json` the outcome is one object on standard output; progress and
diagnostics stay on standard error. Exit codes distinguish a failure the
request caused from one the configuration or the operation caused.

`docs/integration-contract.md` states the whole contract, including what
a front end has to provide that this project deliberately does not:
bounds on time and memory, concurrency, rate limiting and cleanup.

## License

Copyright (C) 2026 kiwibenis.

The software is released under the GNU Affero General Public License,
version 3 only (`AGPL-3.0-only`). The full text is in [`LICENSE`](LICENSE).

Additional terms under sections 7(b) and 7(c) of the license apply. Their
wording is in [`ADDITIONAL-TERMS.md`](ADDITIONAL-TERMS.md). Every Python source
file under `src`, `tests` and `tools` carries a three-line header naming the
license and pointing at that file, because section 7 requires additional terms
to be stated in the relevant source files or a notice to say where they are.

Section 13 applies when the Program is modified and users interact remotely
with that modified version through a computer network. In that case, the
modified version must prominently offer those users access to its Corresponding
Source as required by the license.

The license covers the code and the documentation. Two things in this
repository it does not cover.

The example input images in `examples/input/` are not photographs, and no
copyright is claimed over them. Their origin is documented in
[`examples/input/README.md`](examples/input/README.md).

The reference palettes reproduce color numbers and color names published by
their manufacturers. `docs/reference-data/` documents every shipped palette:
the published chart its numbers and names follow, and the separate status of
its RGB values, which are reproducible reference values for the pipeline and
not manufacturer specifications. Polychromos and Faber-Castell are trademarks of
Faber-Castell AG; Amsterdam and Royal Talens are trademarks of Koninklijke
Talens B.V. This project is not affiliated with, endorsed by or sponsored by
either company, and the trademarks are used only to identify which product a
palette describes.

## Status

🚧 Under development
