# ADR-0007 - Palette Versioning

## Status

Accepted

## Context

Paint-by-numbers documents identify colors by the numbers defined by their
reference palette.

A palette legend should remain reusable for every document generated with the
same palette data.

If reference palette data changes in place, previously generated documents may
no longer correspond to the palette legend or color values with which they were
created.

Palette identity must therefore include a version rather than relying only on
a palette name or identifier.

## Decision

A reference palette shall be a versioned immutable artifact.

The combination of:

- palette identifier;
- palette version;

shall uniquely identify one palette artifact.

Color numbers are defined by the palette and shall remain stable within a
palette version.

Generated paint-by-numbers content shall use the color numbers defined by the
selected palette version.

Normal generation shall carry the selected palette identifier and palette
version in the project-owned generated document representation.

`VectorDocument` shall therefore contain the palette identifier and palette
version for documents produced by the generation pipeline.

Palette legends shall identify the palette version they represent.

A released palette version shall be immutable.

A correction or other change to released palette data, including:

- color numbers;
- color names;
- RGB reference values;
- palette metadata;

shall require a new palette version rather than modifying the released version
in place.

The storage and reference-data requirements for palettes remain governed by
ADR-0006.

Changing palette identity so that identifier and version no longer uniquely
identify the reference data, or permitting released palette versions to be
modified in place, requires an architectural decision.

## Consequences

Palette color numbers remain stable for all documents generated with the same
palette version.

A palette legend can be reused for documents generated with that version.

Generated document data retains enough palette identity to associate it with
the reference data used during generation.

Corrections do not silently change the meaning of previously generated
documents.

Reference-data maintenance may create multiple historical versions of the same
palette, but those versions preserve reproducibility.