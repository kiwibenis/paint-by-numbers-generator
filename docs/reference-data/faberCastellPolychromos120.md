# Polychromos 120 Reference Palette

## Purpose

This document defines the reference data used by the Paint by Numbers
generator for palette `faberCastellPolychromos120`, version `1`.

The palette contains the 120 colours of the Faber-Castell Polychromos range.

The JSON file is the machine-readable source used by the application:

`palettes/faberCastellPolychromos120-v1.json`

## Source Selection

This palette follows the same source policy as
`faberCastellPolychromos60`, and that document states the policy in full.

### Manufacturer data

Faber-Castell is the primary source for the palette identity, the
manufacturer, the colour numbers, the colour names and the membership of the
120-colour range.

The official Faber-Castell Polychromos colour chart documents the colour
numbers and names of the full range:

https://www.faber-castell.com/-/media/Faber-Castell-new/PDF/en/Colourchart-Polychromos-Artists-colour-pencils.ashx?sc_lang=en-Glob

The chart lists 120 colours. The numbers are not consecutive: they run from
`101` to `283` with gaps, which is the manufacturer's own numbering rather
than a positional index. The shipped palette carries the same range and the
same count.

### RGB reference data

Faber-Castell is not treated as the source of the RGB values.

The RGB values in the JSON file are documented digital reference values. They
are reproducible RGB inputs for the colour-processing pipeline and must not be
interpreted as official manufacturer RGB specifications. The priority order
recorded in `faberCastellPolychromos60.md` applies unchanged.

## Relationship to the 60-Colour Palette

`faberCastellPolychromos60` version `1` is a strict subset of this palette.
Every number in the 60-colour palette is present here with an identical name
and identical RGB values, so the two files never disagree about a colour.

The manual decisions recorded in `faberCastellPolychromos60.md` for colour
`131 Coral` and colour `233 Cold Grey IV` therefore apply to this palette as
well.

## Data Quality

Every palette entry contains a number, a name and an RGB value.

The palette contains exactly 120 entries with unique numbers, unique names
and unique RGB values. No two colours in this palette share an RGB value, so
every entry is reachable by the quantizer.

The palette is versioned and immutable. Corrections to the reference data
must result in a new palette version rather than modifying an already
released version.

## Validation

The palette loader validates the palette identifier and version against the
filename and converts the RGB values into the domain colour representation.

`tests/test_reference_data_documentation.py` asserts that every shipped
palette has a document in this directory and that every document names a
palette file that exists.

## Trademarks

Polychromos and Faber-Castell are trademarks of Faber-Castell AG. This project
is not affiliated with, endorsed by or sponsored by Faber-Castell. The names
are used only to identify which product this palette describes.
