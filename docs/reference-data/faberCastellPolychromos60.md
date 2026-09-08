# Polychromos 60 Reference Palette

## Purpose

This document defines the reference data used by the Paint by Numbers
generator for palette `faberCastellPolychromos60`, version `1`.

The palette contains the 60 colours of the Faber-Castell Polychromos tin of
60, product number `110060`.

The JSON file is the machine-readable source used by the application:

`palettes/faberCastellPolychromos60-v1.json`

## Source Selection

The project distinguishes between manufacturer data and digital colour
reference data.

### Manufacturer data

Faber-Castell is the primary source for:

- palette identity
- manufacturer
- colour numbers
- colour names
- membership in the Polychromos 60-colour assortment

The official Faber-Castell product page identifies product `110060` as a
Polychromos colour pencil tin of 60 and provides the Polychromos swatch card
and colour table. https://www.faber-castell.com/-/media/Faber-Castell-new/PDF/en/Farbtabelle-AG-ENG-0214.ashx?sc_lang=en-Glob

The official Faber-Castell colour chart documents the Polychromos colour
numbers and names, including:

- `131 Coral`
- `233 Cold Grey IV`

https://www.faber-castell.com/-/media/Faber-Castell-new/PDF/en/Colourchart-Polychromos-Artists-colour-pencils.ashx?sc_lang=en-Glob

Faber-Castell also documents that colour `131` underwent a name change in
2019 and is currently named `Coral`.

### RGB reference data

Faber-Castell is not treated as the source of the RGB values in this
repository.

The RGB values in the JSON file are documented digital reference values.
They are used as reproducible RGB inputs for the colour-processing pipeline
and must not be interpreted as official manufacturer RGB specifications.

The project follows this priority:

1. Official manufacturer colour numbers.
2. Official manufacturer colour names.
3. Documented RGB reference values.
4. Community RGB values as fallback where no better documented value is
   available.

## Manual Project Decisions

### Colour 131

The palette uses:

- number: `131`
- name: `Coral`

This is also the current Faber-Castell name. The project deliberately uses
the current manufacturer name rather than an historical name.

### Colour 233

The reference source contained conflicting representations for colour `233`
Cold Grey IV:

- HEX: `#8E9498`
- conflicting RGB entry: `(142, 178, 152)`

The project explicitly rejects the conflicting RGB entry.

The manually selected project value is:

- number: `233`
- name: `Cold Grey IV`
- HEX: `#8E9498`
- RGB: `(142, 148, 152)`

This conversion is mathematically consistent with the hexadecimal value and
is an explicit project decision. It is not presented as an official
Faber-Castell RGB specification.

## Data Quality

Every palette entry must contain:

- number
- name
- rgb

The current reference palette contains exactly 60 unique colour entries with
unique numbers, unique names and unique RGB values.

Every entry of this palette is also present in `faberCastellPolychromos120`
version `1` with an identical name and identical RGB values. The 60-colour
palette is a strict subset of the 120-colour palette rather than an
independently maintained list.

The palette is versioned and immutable. Corrections to the reference data
must result in a new palette version rather than modifying an already
released version.

## Validation

The palette loader validates the palette identifier and version against the
filename and converts the RGB values into the domain colour representation.

Tests for the current reference palette are located in:

`tests/test_palette_loader.py`

`tests/test_reference_data_documentation.py` asserts that every shipped
palette has a document in this directory and that every document names a
palette file that exists.

## Trademarks

Polychromos and Faber-Castell are trademarks of Faber-Castell AG. This project
is not affiliated with, endorsed by or sponsored by Faber-Castell. The names
are used only to identify which product this palette describes.