# Amsterdam Standard Series Reference Palettes

## Purpose

This document defines the reference data used by the Paint by Numbers
generator for the four Amsterdam Standard Series palettes, each at version
`1`:

    palettes/amsterdamStandardRoyalTalents24-v1.json
    palettes/amsterdamStandardRoyalTalents36-v1.json
    palettes/amsterdamStandardRoyalTalents48-v1.json
    palettes/amsterdamStandardRoyalTalents90-v1.json

They describe selections from the Royal Talens Amsterdam Standard Series
acrylic range.

One document covers all four, because they are not independent lists. Each
smaller palette is a strict subset of the next larger one:

    24 colours  is a subset of  36 colours
    36 colours  is a subset of  48 colours
    48 colours  is a subset of  90 colours

Every shared number carries an identical name and identical RGB values across
the four files, so they never disagree about a colour.

## Source Selection

The project distinguishes between manufacturer data and digital colour
reference data, in the same way as the Polychromos palettes.
`faberCastellPolychromos60.md` states the policy in full.

### Manufacturer data

Royal Talens is the primary source for the palette identity, the manufacturer,
the colour numbers, the colour names and the membership of the Standard Series
range.

The official Amsterdam colour charts are published here:

https://www.royaltalens.com/pages/amsterdam-colour-chart

The Standard Series chart on that page is the reference for the numbers and
names in these files. The numbers are the manufacturer's own and are not
consecutive; in the 90-colour palette they run from `104` to `840` with gaps.

The 90 entries were checked against that chart column by column:

- all 90 numbers appear in the chart;
- 82 names are identical;
- 4 differ only by the footnote marker the chart prints after the Reflex
  colours;
- 2 differ only in the apostrophe character, in `King's Blue` and
  `Payne's Grey`;
- 1 name was a genuine discrepancy and was corrected.

Colour `267` was named `Azo Yellow Lemon`. The chart's English column reads
`Azo yellow`; the qualifier appears only in the Dutch and German columns, as
`Lemon azogeel` and `Azogelb zitrone`, so the earlier name mixed languages.
The shipped name is `Azo Yellow`.

### RGB reference data

Royal Talens is not treated as the source of the RGB values.

The RGB values in the JSON files are documented digital reference values. They
are reproducible RGB inputs for the colour-processing pipeline and must not be
interpreted as official manufacturer RGB specifications. Acrylic paint in
particular cannot be represented faithfully by a single sRGB triple: the same
paint differs by film thickness, ground, and whether it is applied
transparently or opaquely.

The published chart is not a usable source for absolute RGB values either. Its
swatches are printed CMYK fields, and converting them without a colour profile
yields values that are systematically darker and less saturated than the
shipped ones. Compared channel by channel across all 90 entries, the largest
channel difference has a median of 29 and only 8 of 90 entries fall within 12.

The chart is therefore used only for the difference between two swatches
printed under identical conditions, which it does measure reliably, and never
for an absolute value. That is what the correction below rests on.

The priority order recorded in `faberCastellPolychromos60.md` applies
unchanged.

## The Three Corrected Pairs

An earlier revision of these files gave three pairs of colours one RGB value
each:

    104 Zinc White              and  105 Titanium White
        rgb(255, 255, 255)           in the 36, 48 and 90 palettes

    272 Transparent Yellow Med. and  275 Primary Yellow
        rgb(255, 237, 0)             in the 90 palette

    398 Naphthol Red Light      and  399 Naphthol Red Deep
        rgb(189, 53, 52)             in the 90 palette

A pair with one RGB value is one colour to the quantizer: the nearest-colour
search is a tie and the earlier entry wins every time, so `105`, `272` and
`399` could never appear on a generated template while still being printed in
the legend. A painter buying those three tubes would never use them.

Nothing had been published against those files and no template existed, so
they were corrected in place rather than superseded by a version `2`. The
values below are what version `1` ships.

### How the corrected values were derived

Each pair keeps the earlier value on the member the range treats as primary,
and moves the other by the difference measured between the two swatches in the
published chart. The chart supplies only that difference, so no absolute value
from a foreign source enters the palette.

    105 Titanium White           (255, 255, 255)  kept
    104 Zinc White               (251, 250, 250)  chart: 104 darker than 105

    275 Primary Yellow           (255, 237,   0)  kept
    272 Transparent Yellow Med.  (255, 232,   0)  chart: 272 greener than 275

    398 Naphthol Red Light       (189,  53,  52)  kept
    399 Naphthol Red Deep        (128,  42,  48)  chart: 399 much darker

`105 Titanium White` is the opaque brilliant white, `275 Primary Yellow` is a
primary, and `398` is the light variant the deep one is measured against.

### Whether the separations are large enough to be meaningful

Measured in Delta E 2000, the metric the generator itself uses, the corrected
separations are:

    398 / 399   dE 13.30
    272 / 275   dE  1.45
    104 / 105   dE  1.08

Two of those are small in absolute terms. They are nevertheless within what
this palette already treats as two distinct colours, because it ships pairs
that are closer together:

    276 / 257   Azo Orange and Reflex Orange              dE 0.26
    396 / 315   Naphthol Red Medium and Pyrrole Red       dE 1.24
    369 / 348   Primary Magenta and Permanent Red Purple  dE 1.40

The corrected pairs are therefore not a finer distinction than the palette
already makes elsewhere.

## Data Quality

Every palette entry contains a number, a name and an RGB value.

Within each file the numbers, the names and the RGB values are unique, so
every entry is reachable by the quantizer.

The palette is versioned and immutable. Now that these files are published,
corrections must result in a new palette version rather than modifying an
already released version.

## Validation

The palette loader validates the palette identifier and version against the
filename and converts the RGB values into the domain colour representation.

`tests/test_palette_loader.py` asserts the six corrected values and the name
of colour `267` against the shipped files.

`tests/test_palette_rgb_uniqueness.py` asserts that no shipped palette
contains a duplicate RGB value, and that each of the six values quantizes to
its own number against the real quantizer.

`tests/test_reference_data_documentation.py` asserts that every shipped
palette has a document in this directory and that every document names a
palette file that exists.

## Trademarks

Amsterdam and Royal Talens are trademarks of Koninklijke Talens B.V. This
project is not affiliated with, endorsed by or sponsored by Royal Talens. The
names are used only to identify which product these palettes describe.
