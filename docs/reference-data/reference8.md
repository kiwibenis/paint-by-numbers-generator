# Reference 8 Palette

## Purpose

This document defines the reference data used by the Paint by Numbers
generator for palette `reference8`, version `1`.

The JSON file is the machine-readable source used by the application:

`palettes/reference8-v1.json`

## Source Selection

### Manufacturer data

The manufacturer is this project:

```json
"manufacturer": "Paint-by-Numbers Generator"
```

`pbn palettes` prints it with every listing, and a generated legend carries it
like any other manufacturer.

The numbers, the names and the RGB values are this manufacturer's own. There
is no external source and no third-party product data: nothing here was taken
from a published colour chart, unlike the Polychromos and Amsterdam palettes
documented beside this file.

`reference8` is an official project-owned palette. Its reference data is
defined directly by Paint-by-Numbers Generator rather than transcribed from an
external manufacturer or commercial range.

The palette exists so that the documentation, the example configuration and
the test suite have a palette small enough to reason about by hand. It is the
palette `config/example.toml` selects.

### RGB reference data

The eight entries are the corners of the sRGB cube that carry a name in
ordinary use: white, black, the three additive primaries and their three
complements.

| Number | Name | RGB | Hex |
|---:|---|---|---|
| 1 | White | 255, 255, 255 | `#FFFFFF` |
| 2 | Black | 0, 0, 0 | `#000000` |
| 3 | Red | 255, 0, 0 | `#FF0000` |
| 4 | Green | 0, 255, 0 | `#00FF00` |
| 5 | Blue | 0, 0, 255 | `#0000FF` |
| 6 | Yellow | 255, 255, 0 | `#FFFF00` |
| 7 | Cyan | 0, 255, 255 | `#00FFFF` |
| 8 | Magenta | 255, 0, 255 | `#FF00FF` |

They are exact channel extremes rather than measurements of a pigment, which
is what makes the palette checkable by hand: a quantization result can be
worked out without consulting a chart.

## Data Quality

Every palette entry contains a number, a name and an RGB value.

The palette contains exactly eight entries with unique numbers, unique names
and unique RGB values. The numbers run consecutively from `1` to `8` because
this manufacturer assigned them that way, which a manufacturer maintaining a
range that grew over time cannot do.

The palette is versioned and immutable. Corrections must result in a new
palette version rather than modifying an already released version.

## Validation

The palette loader validates the palette identifier and version against the
filename and converts the RGB values into the domain colour representation.

Number uniqueness is enforced for every palette document rather than only for
this one, by `pbn.infrastructure.palette_document`.

`tests/test_reference_data_documentation.py` asserts that every shipped
palette has a document in this directory and that every document names a
palette file that exists.

## Trademarks

The manufacturer name is the project's own. The colour names are the ordinary
English words for the sRGB corners and are taken from no commercial range, so
no product name, colour name or colour number in this palette refers to a
third-party product.