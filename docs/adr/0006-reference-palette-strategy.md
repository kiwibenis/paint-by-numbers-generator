# ADR-0006 - Reference Palette Strategy

## Status

Accepted

## Context

The quality of the Paint by Numbers generator depends directly on the quality
of its reference palettes.

All color-related processing, including quantization, color matching and
legend generation, relies on the palette as its primary source of truth.

Incorrect or inconsistent palette data would affect the complete processing
pipeline.

## Decision

Reference palettes are treated as immutable reference data.

Each palette shall:

- use JSON as storage format;
- contain version information;
- contain metadata describing the palette;
- contain one unique entry for every available color;
- use official manufacturer color numbers;
- use official manufacturer color names;
- contain documented RGB reference values.

Palette data is stored separately from application code.

## Consequences

Reproducible color processing.

Reference data can evolve independently from application code.

Additional manufacturers can be added without changing Python code.

Palette data requires maintenance and careful validation.