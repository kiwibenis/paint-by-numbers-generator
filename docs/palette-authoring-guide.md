# Palette Authoring Guide

## Purpose

This guide defines the workflow for adding and maintaining reference palettes
in the Paint by Numbers Generator.

A reference palette is not merely a list of visually plausible colors.

It is versioned project reference data used directly by:

- palette quantization;
- region color assignment;
- generated paint-by-numbers numbering;
- PDF palette legends;
- reproducibility of previously generated documents.

Palette authoring therefore requires both:

1. machine-readable palette data under `palettes/`;
2. documented provenance under `docs/reference-data/`.

The authoritative storage format is defined in
[`palette-format.md`](palette-format.md).

The architectural rules are defined primarily by:

- [ADR-0006 - Reference Palette Strategy](adr/0006-reference-palette-strategy.md);
- [ADR-0007 - Palette Versioning](adr/0007-palette-versioning.md);
- [ADR-0013 - Project Language](adr/0013-project-language.md);
- [ADR-0017 - Compact Pixel Representation](adr/0017-compact-pixel-representation.md).

This guide describes the current authoring workflow. It does not redefine
those decisions.

## Reference Palette Artifacts

A shipped reference palette consists of at least two repository artifacts:

```text
palettes/<palette-id>-v<version>.json

docs/reference-data/<reference-document>.md
```

The JSON file is the machine-readable source used by generation.

The reference-data document explains where the palette identity, manufacturer
data, color numbers, color names, assortment membership and RGB reference
values came from.

One reference-data document may cover multiple closely related palette files
when they share one source policy and one product family.

For example, several palette sizes from one manufacturer may be documented
together when the smaller palettes are defined subsets of the same larger
range.

Every shipped palette file must be named by at least one document under
`docs/reference-data/`.

## Palette Types

The repository currently supports two legitimate kinds of reference palette.

### Manufacturer-Backed Palette

A manufacturer-backed palette represents a real commercial color range.

Its identity, color numbers, color names and assortment membership must be
based on authoritative manufacturer information.

Examples of suitable manufacturer sources include:

- an official manufacturer color chart;
- an official manufacturer product page;
- an official assortment or product catalogue;
- another manufacturer-published document that directly identifies the
  relevant colors.

Manufacturer-backed palettes must use the manufacturer's own color identifiers
and names.

Do not replace manufacturer numbering with a local sequential numbering scheme.

Do not rename colors merely to make them more convenient for the project.

### Official Project-Owned Palette

An official project-owned palette may be defined directly by the project when
it serves a clear project-controlled purpose such as:

- examples;
- tests;
- documentation;
- manually understandable reference behavior.

Its manufacturer is the project itself, and its color numbers, color names and
RGB reference values are official reference data defined by that manufacturer.

A project-owned palette must be explicitly documented as project-owned and
must identify the project-controlled manufacturer value that owns its
reference data.

It must not imply that its numbers, names or RGB values represent a third-party
commercial product.

Project-owned reference data is still versioned and immutable once released.

## Source Policy

Palette authoring distinguishes between two categories of source data:

```text
manufacturer identity data

digital RGB reference data
```

They have different evidentiary requirements.

### Manufacturer Identity Data

For a manufacturer-backed palette, the manufacturer is the primary source for:

- manufacturer name;
- product or palette identity;
- official color numbers;
- official color names;
- membership of colors in the relevant assortment.

The authoring process must verify these values against manufacturer-published
material.

Third-party retail listings, community databases and arbitrary palette
websites must not override manufacturer information for these fields.

If several manufacturer sources disagree, the reference-data document must
identify the conflict and state which authoritative source is used.

The selected value must remain an actual manufacturer-defined value.

### Digital RGB Reference Data

The RGB values stored by this project are reproducible digital reference
values used by the color-processing pipeline.

They must not automatically be described as official manufacturer RGB values.

Many physical art materials do not have one authoritative sRGB representation.
Their appearance can depend on properties such as:

- substrate;
- opacity;
- film thickness;
- illumination;
- printing process;
- display profile.

A manufacturer color chart may therefore be authoritative for color identity
while being unsuitable as an absolute RGB specification.

The provenance document must state clearly whether the manufacturer actually
publishes the RGB values used by the project.

If not, the values must be described as project reference values rather than
manufacturer specifications.

## RGB Source Priority

For manufacturer-backed palettes, use the following priority:

1. official manufacturer color numbers;
2. official manufacturer color names;
3. documented digital RGB reference values;
4. documented community RGB values only when no better source is available.

The first two items define the identity of the physical color.

The latter two provide the digital reference value used by the generator.

A community RGB source is acceptable only as a documented fallback. Its use
must be explicit in the corresponding reference-data document.

Do not silently present a community value as manufacturer data.

## Requirements for RGB Reference Values

Every RGB value must be reproducible from documented evidence.

Acceptable forms include:

- a source that directly publishes an RGB triple;
- a source that publishes an exact hexadecimal sRGB value;
- another documented digital representation that can be converted
  deterministically to the stored RGB value;
- a project-derived value whose derivation from cited source data is explicit
  and reproducible.

When hexadecimal data is used, its conversion to RGB must be exact.

For example:

```text
#8E9498
```

corresponds to:

```text
red   = 142
green = 148
blue  = 152
```

If one source contains conflicting representations, such as an RGB value that
does not match its hexadecimal value, do not choose one silently.

The reference-data document must record:

- the conflicting values;
- the representation selected by the project;
- the reason for selecting it;
- the final stored RGB value.

A visual estimate made by eye without a reproducible derivation is not suitable
reference data.

## Project-Derived RGB Values

A project-derived RGB value is permitted only when its derivation is
documented well enough to reproduce the result.

The documentation must distinguish clearly between:

```text
source fact
```

and:

```text
project derivation
```

A derived value must not be described as an official manufacturer RGB
specification unless the manufacturer actually provides that value.

The derivation should use the smallest reasonable amount of interpretation.

When the available evidence is insufficient to establish a defensible digital
reference value, do not invent one merely to complete the palette.

The palette should remain unshipped until suitable reference data is available.

## Palette Identity

Each palette has:

```text
id
manufacturer
display_name
version
```

The combination of:

```text
id + version
```

uniquely identifies one immutable palette artifact.

### Palette Identifier

The runtime palette catalogue accepts identifiers matching the syntax
in [`palette-format.md`](palette-format.md).

The identifier becomes part of the file name and of the external palette
selection contract.

Choose an identifier that is:

- stable;
- descriptive;
- independent from display formatting;
- suitable for long-term use in configuration files.

Examples already used by the project include:

```text
reference8
faberCastellPolychromos60
faberCastellPolychromos120
amsterdamStandardRoyalTalents90
```

Do not encode a version into the identifier.

The version is represented separately.

### Manufacturer

For a commercial palette, use the manufacturer name that identifies the actual
product source.

For an official project-owned palette, use the project-controlled manufacturer
value that owns the reference data and document explicitly that the palette is
project-owned.

### Display Name

`display_name` is the human-readable palette name shown to callers and in
generated output.

It should distinguish palette variants clearly.

For example, different assortment sizes should not all use the same display
name when callers need to distinguish them.

## Versioning

The file naming rule, the requirement that the file name match the metadata,
and the immutability of a released version are defined in
[`palette-format.md`](palette-format.md), which remains authoritative for
those storage rules.

File-path examples in this guide illustrate the authoring workflow. They do not
redefine which file names or versions the storage format accepts.

## Correcting a Released Palette

Immutability is easy to state and easy to violate under time pressure,
because correcting a wrong value in place looks like the smaller change.

It is not. A previously generated document identifies the palette it used by
identifier and version, and its numbers only mean something against that
exact data. Overwriting version `1` silently changes what every existing
printed template refers to.

A correction therefore ships as a new version beside the old one:

```text
palettes/examplePalette-v1.json
palettes/examplePalette-v2.json
```

Both remain valid artifacts. Existing documents keep identifying version `1`,
and new generation selects version `2` explicitly.

The one situation where this does not apply is a palette that has never been
released. Before publication there is nothing to stay reproducible against,
and a defective file is better corrected than versioned around. Once
published, the rule is absolute.

Whichever route is taken, the reference-data document under
`docs/reference-data/` has to record what changed and on what evidence, in
the same change.

## Schema and Bounds

The document shape, every field and every bound the loader enforces are defined
in [`palette-format.md`](palette-format.md), which is complete for them.

Numeric and character-set bounds are not restated here. This guide once carried
its own copies of those rules, and a rule written down twice is a rule that can
eventually become two different rules.

File-path examples elsewhere in this guide show where authoring artifacts
belong and how the workflow uses them. `palette-format.md` remains
authoritative for whether a palette document and its file name are valid.

Read that document before writing a palette file. What follows here is what it
deliberately does not answer: which values belong in those fields.

## Manufacturer Color Numbers

A manufacturer-backed palette must use the manufacturer's official color
number.

If a manufacturer identifies its colors with values the format cannot hold,
do not invent replacement numbers. That palette does not fit the current
schema and requires a deliberate format or architectural change before it can
be represented correctly. Substituting a number that fits would make the
generated template disagree with the tin a painter buys, which is the one
thing the number exists to prevent.

## Color Names

Manufacturer-backed palettes use official manufacturer color names.

Do not:

- translate an official name merely for convenience;
- simplify a name because it is long;
- invent a local name;
- remove a meaningful manufacturer qualifier.

ADR-0013 requires project-controlled text to use English, but authoritative
external names may remain in their original language when translation would
change or obscure their meaning.

## Text the Legend Cannot Render

Which characters a palette may use is a format rule, stated with its reason in
[`palette-format.md`](palette-format.md).

The authoring decision is what to do when a name does not fit it. A palette
name written in a script the current legend cannot render must not be silently
transliterated solely to make the loader accept it. If no authoritative
renderable form exists, supporting that palette requires a renderer or output
change rather than falsifying the source data.

## Unique Color Numbers

Uniqueness within one palette is a format rule and is enforced when the
document is loaded.

What the format cannot check is agreement between files: for related palette
variants, the same manufacturer number should identify the same physical
color.

## Unique RGB Values

Every shipped palette must use a distinct RGB value for every color entry.
This is not checked when a document is loaded, for the reason
[`palette-format.md`](palette-format.md) gives, so it is an authoring
obligation rather than a format one.

Two entries with one identical RGB value are indistinguishable to the
quantizer.

Given:

```text
color A -> RGB X
color B -> RGB X
```

the nearest-color search receives an exact tie for those entries.

One of the palette numbers can then become unreachable even though both still
appear in the legend.

The repository therefore verifies that shipped palettes do not contain
duplicate RGB values.

Do not solve a duplicate by making an arbitrary one-channel change.

The differing value must be supported by documented source evidence or a
documented reproducible derivation.

## Palette Families and Subsets

When several files represent different assortment sizes from the same product
family, shared colors must remain internally consistent.

For every shared manufacturer number, use the same:

```text
number
name
RGB reference value
```

unless authoritative source evidence establishes that the products genuinely
define that color differently.

A smaller assortment should therefore normally be a true subset of the larger
reference palette rather than an independently maintained conflicting copy.

Document the subset relationship in `docs/reference-data/`.

Add a regression test when the relationship is important to maintaining the
reference data.

## Stable Ordering

Keep palette entries in a stable, understandable order.

Prefer:

1. the manufacturer's published order when it is meaningful;
2. otherwise manufacturer color-number order.

Once released, the order is part of the immutable artifact, because the
legend is printed in it.

## Reference-Data Documentation

Every shipped palette must have matching provenance documentation under:

```text
docs/reference-data/
```

The documentation must name the exact palette file path.

For example:

```text
palettes/examplePalette-v1.json
```

This relation is mechanically checked.

A palette file without reference documentation is invalid repository state.

A reference-data document that names a palette file that does not exist is also
invalid repository state.

The documents currently shipped are worth reading before writing a new one,
because they show how the same policy applies to three different situations:

- [`reference-data/faberCastellPolychromos60.md`](reference-data/faberCastellPolychromos60.md)
  and
  [`reference-data/faberCastellPolychromos120.md`](reference-data/faberCastellPolychromos120.md),
  a manufacturer palette and the larger range it is a strict subset of;
- [`reference-data/amsterdamStandardRoyalTalents.md`](reference-data/amsterdamStandardRoyalTalents.md),
  one document covering four nested assortments, including a record of a
  defect found in the RGB data and how the corrected values were derived;
- [`reference-data/reference8.md`](reference-data/reference8.md), an official
  project-owned palette whose reference data is defined by Paint-by-Numbers
  Generator and which has no external source.

## Reference-Data Document Structure

A new reference-data document should normally contain the following sections.

### Purpose

Identify:

- palette ID;
- version;
- represented product or project purpose;
- exact JSON file or files covered by the document.

### Source Selection

Explain the source policy used for the palette.

Separate manufacturer identity data from RGB reference data.

### Manufacturer Data

For a commercial palette, document the authoritative manufacturer sources used
for:

- product identity;
- assortment membership;
- color numbers;
- color names.

Include sufficiently precise source references to reproduce the verification.

For an official project-owned palette, document that the project itself is the
manufacturer and defines the corresponding identity data.

### RGB Reference Data

State:

- where the RGB values came from;
- whether those values are manufacturer-published;
- whether another documented digital source was used;
- whether community values were required as fallback;
- whether any project derivation was required.

Do not imply manufacturer authority where none exists.

### Project Decisions

Include this section only when interpretation is actually required.

Examples include:

- conflicting fields in one source;
- several authoritative sources using different current names;
- a documented deterministic conversion;
- a derived value needed to keep two manufacturer-defined colors distinct.

State the final decision and enough evidence to reproduce it.

Do not use this section as a development history.

Only the decision relevant to the current shipped artifact belongs here.

### Data Quality

Record relevant properties such as:

- expected color count;
- unique manufacturer numbers;
- unique RGB values;
- known subset relationships;
- other palette-specific invariants.

### Validation

Name the tests that protect any palette-specific decisions or relationships.

Generic repository tests do not need to be explained at length, but the
document should identify palette-specific regression coverage when it exists.

### Trademarks

For a manufacturer-backed palette, include an appropriate non-affiliation
statement when commercial product and trademark names are used for
identification.

Do not imply manufacturer endorsement.

## Reference-Data Document Template

A minimal manufacturer-backed document can use this structure:

```markdown
# <Palette Display Name> Reference Palette

## Purpose

This document defines the reference data used by the Paint by Numbers
Generator for palette `<palette-id>`, version `<version>`.

The JSON file used by the application is:

`palettes/<palette-id>-v<version>.json`

## Source Selection

The project distinguishes manufacturer identity data from digital RGB
reference data.

## Manufacturer Data

<Identify the authoritative manufacturer sources for product identity,
assortment membership, color numbers and color names.>

## RGB Reference Data

<Identify the RGB source and state whether the values are or are not official
manufacturer specifications.>

## Project Decisions

<Include only when a current value requires interpretation or derivation.
Remove this section when no such decision exists.>

## Data Quality

<Describe expected color count, uniqueness and relevant family relationships.>

## Validation

<Identify palette-specific regression tests when applicable.>

## Trademarks

<Identify trademarks and state that the project is not affiliated with,
endorsed by or sponsored by the manufacturer when appropriate.>
```

A single document may name several palette files when it genuinely documents
one shared family.

## Adding a New Palette

Use the following workflow.

### 1. Establish the Palette Identity

Before creating the JSON file, decide:

```text
palette id
manufacturer
display name
version
represented assortment
```

For a first released artifact, the version is normally:

```text
1
```

Confirm that the identifier does not conflict with an existing palette.

### 2. Collect Manufacturer Evidence

For a manufacturer-backed palette, collect authoritative evidence for:

```text
product identity
color membership
color numbers
color names
```

Resolve any source disagreement before constructing the final JSON data.

Do not use a third-party source to override manufacturer-defined identity data.

For an official project-owned palette, define these values explicitly as
manufacturer-owned project reference data instead of inventing an external
source.

### 3. Establish RGB Reference Values

Determine the documented digital RGB reference source.

For every color, ensure that the stored value can be traced to either:

- a documented source;
- an explicitly documented reproducible derivation.

Validate the completed RGB data against the storage-format rules in
[`palette-format.md`](palette-format.md).

Check for duplicate RGB values before considering the palette complete.

### 4. Create the JSON File

Create:

```text
palettes/<palette-id>-v<version>.json
```

Use the exact schema from
[`palette-format.md`](palette-format.md).

The file name, metadata identifier and metadata version must agree.

Do not add Python registration code for an ordinary new palette.

`PaletteManager` discovers loadable JSON palette files from `palettes/`.

Additional manufacturers can therefore normally be added as reference data
without changing production Python code.

### 5. Create the Provenance Document

Create or extend an appropriate document under:

```text
docs/reference-data/
```

Name the exact palette file in that document.

Document the evidence used for both:

```text
manufacturer identity
RGB reference data
```

Do this in the same logical palette-authoring change.

Do not ship undocumented reference data.

### 6. Add Palette-Specific Regression Tests

The generic palette tests already validate repository-wide rules.

Add specific tests when the new palette has facts that deserve permanent
protection, such as:

- an exact expected color count;
- important manufacturer numbers or names;
- an explicit source-resolution decision;
- a subset relationship between palette sizes;
- a derived RGB value;
- another palette-specific invariant.

Palette-specific tests should verify the current reference artifact rather than
recording the history that produced it.

### 7. Verify Catalogue Discovery

From the repository root, confirm that the new palette appears in:

```text
pbn palettes
```

Also verify the supported machine-readable catalogue:

```text
pbn palettes --json
```

The catalogue loads palette files rather than merely listing filenames.

A palette that does not load is therefore not a valid selectable palette, and
the reverse holds too: the catalogue and `--palette` decide what a palette
file is called by the same rule, so a palette listed here can be selected.
They once decided it separately, and the catalogue offered names the
selection refused.

### 8. Validate a Real Generation

Run at least one representative generation using the new palette.

Confirm that:

- the palette can be selected by ID and version;
- quantization completes;
- palette numbers appear correctly in generated regions;
- the legend identifies the expected palette version;
- color names render correctly;
- the generated legend contains the expected colors.

A palette that only passes JSON parsing but cannot produce a usable legend is
not complete.

## Existing Generic Validation

The current repository already contains generic coverage for palette authoring.

### `tests/test_palette_content_validation.py`

Protects the palette-document schema, including:

- exact accepted keys;
- required fields;
- field types;
- text lengths;
- color count;
- RGB channel bounds;
- version validity;
- malformed JSON handling;
- palette document size;
- loading of all shipped palette documents.

### `tests/test_palette_loader.py`

Protects loading semantics and palette-specific reference values already
recorded by the repository.

It also contains consistency checks for existing related palette families.

### `tests/test_palette_rgb_uniqueness.py`

Checks every shipped palette for duplicate RGB values.

It also verifies reachability through the real quantizer for reference values
where that behavior has explicit regression coverage.

### `tests/test_reference_data_documentation.py`

Checks both directions of the palette/documentation relationship:

```text
every shipped palette is documented

every documented palette file exists
```

### `tests/test_palette_text_is_renderable.py`

Verifies that the characters accepted by palette validation are actually
renderable by the fonts used by the PDF legend.

### `tests/test_palette_identifier_validation.py`

Protects the accepted palette identifier and version boundary and its path
confinement behavior.

## Full Project Validation

After adding or changing palette reference data, run the complete project
validation:

```text
ruff check src tests tools
python -m black --check .
mypy
pytest -q
```

Palette data participates directly in production generation, so adding a
palette is not exempt from the normal project validation workflow.

## Reviewing Palette Data

Before release, review the palette independently from its source preparation.

The reviewer should be able to answer:

```text
What manufacturer-backed or official project-owned palette does this represent?

Which source establishes the palette membership?

Are the color numbers authoritative?

Are the color names authoritative?

Where did each RGB reference value come from?

Are any values project-derived?

Can every project-derived value be reproduced?

Does the JSON filename match its metadata?

Are all color numbers unique?

Are all RGB values unique?

Are related palette variants internally consistent?

Can all legend text be rendered?

Does the palette appear in the supported catalogue?

Does a representative generated PDF use the palette successfully?
```

If any answer depends only on undocumented knowledge held by the author, the
palette is not ready to ship.

## Corrections

A released palette version is immutable.

When a correction is required:

1. preserve the existing JSON file unchanged;
2. create the next palette version;
3. apply the correction only to the new version;
4. document the source and current decision;
5. add or update regression coverage for the corrected reference data;
6. verify that both historical and new versions remain loadable when both are
   intentionally shipped.

Do not modify a released palette file merely because no current configuration
selects it.

Its identity may already be embedded in generated documents.

## Manufacturer Updates

A manufacturer may change:

- product membership;
- color names;
- color formulations;
- product numbering.

Do not silently apply those changes to an existing palette version.

First determine whether the project intends to represent:

```text
the existing documented assortment
```

or:

```text
the manufacturer's newer assortment
```

If the underlying reference data changes, create a new palette version or a
new palette identity as appropriate.

The selected identity must describe one reproducible artifact.

## Project-Owned Palette Rules

Official project-owned palettes do not require external manufacturer sources,
because the project itself is their manufacturer and authority.

Their reference-data documentation must instead define:

- why the palette exists;
- the project-controlled manufacturer that owns its values;
- what its numbers mean;
- how its color names and RGB reference values are defined;
- whether it represents any third-party product.

Project-owned palettes must not reuse commercial product naming in a way that
suggests third-party manufacturer backing.

Their RGB values still require explicit project definitions and remain
immutable within a released version.

They are subject to the same:

- JSON schema;
- color-count limit;
- text-renderability limit;
- RGB uniqueness requirement;
- versioning rules;
- reference-data documentation requirement.

## Authoring Checklist

A new shipped palette is complete only when all of the following are true:

- the palette identity is stable and valid;
- the represented assortment is clearly defined;
- manufacturer-backed identity data comes from authoritative manufacturer
  sources;
- project-owned identity data, when applicable, is explicitly defined by its
  project-controlled manufacturer;
- official manufacturer color numbers are preserved;
- official manufacturer color names are preserved;
- RGB reference values are documented and reproducible;
- project-derived values, if any, have explicit derivations;
- the palette contains no duplicate color numbers;
- the palette contains no duplicate RGB values;
- related palette variants agree on shared colors;
- all text can be rendered by the current PDF legend;
- the JSON file follows `docs/palette-format.md`;
- the filename matches palette ID and version;
- a matching reference-data document exists;
- palette-specific decisions have regression tests where appropriate;
- the palette appears in `pbn palettes`;
- the palette appears in `pbn palettes --json`;
- a representative PDF generation succeeds;
- the complete project validation passes;
- a released palette version will remain immutable.

## Related Documentation

For the authoritative JSON format and versioning conventions, see:

- [`palette-format.md`](palette-format.md).

For current shipped palette provenance, see:

- [`reference-data/`](reference-data/).

For architectural palette strategy, see:

- [ADR-0006 - Reference Palette Strategy](adr/0006-reference-palette-strategy.md);
- [ADR-0007 - Palette Versioning](adr/0007-palette-versioning.md).

For the palette-size representation bound, see:

- [ADR-0017 - Compact Pixel Representation](adr/0017-compact-pixel-representation.md).

For project-language rules and authoritative external names, see:

- [ADR-0013 - Project Language](adr/0013-project-language.md).

For the supported external palette catalogue, see:

- [`integration-contract.md`](integration-contract.md).

For user-facing palette selection, see:

- [`../README.md`](../README.md).