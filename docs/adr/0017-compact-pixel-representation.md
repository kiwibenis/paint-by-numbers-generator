# ADR-0017 - Compact Pixel Representation

## Status

Accepted

## Context

Images contain one value per pixel, so their storage representation has a
direct effect on memory consumption and on the cost of per-pixel processing.

Representing every pixel as a separate Python domain object adds substantial
object and container overhead even though the underlying information is small:
an input RGB pixel needs three byte values, while a quantized pixel only needs
to identify one entry in a bounded palette.

The project still needs `RGB` and `PaletteColor` as domain vocabulary. Compact
storage therefore must not require the rest of the Core to adopt
implementation-specific array-library types.

ADR-0003 keeps third-party runtime libraries outside the Core, and ADR-0008
requires project-owned domain models at architectural boundaries.

Region membership has different access patterns from image storage and is
governed separately by ADR-0018.

## Decision

`InputImage` shall store normalized RGB pixel data as `bytes`.

The layout shall be row-major with exactly three bytes per pixel in red, green
and blue order.

`InputImage` shall own the conversion between that compact representation and
the `RGB` domain value used by callers that require an individual color.

`QuantizedImage` shall store:

- the palette referenced by the image;
- one palette index per pixel as `bytes`.

The quantized image shall therefore support at most 256 palette entries.

A palette that cannot be addressed by one byte shall be rejected rather than
silently changing the pixel representation.

`QuantizedImage` shall own the conversion between stored indices and
`PaletteColor` domain values.

Code on per-pixel hot paths should operate directly on the compact scalar
representation when doing so does not change domain semantics.

The compact image representation shall use standard-library storage types and
shall not introduce a third-party numerical-array type into the Core.

The representation is a storage decision only. It shall not change color
semantics, quantization results, ordering or generated output.

Region membership is not governed by this ADR. ADR-0018 defines the compact
representation of `Region.pixels`.

Changing the number of bytes used for normalized RGB storage, widening the
quantized palette index beyond one byte or introducing an external array type
into these Core models requires an architectural decision.

## Consequences

Image storage grows linearly with pixel count with a small and explicit
per-pixel representation.

`InputImage` requires three stored bytes per pixel.

`QuantizedImage` requires one stored index byte per pixel in addition to its
palette.

Domain callers can continue to work with `RGB` and `PaletteColor` values even
though those objects are not stored once per pixel.

Per-pixel code may use direct byte indexing where object reconstruction would
be unnecessary overhead.

The one-byte quantized representation makes the 256-entry palette bound part
of the image model and of any boundary that transports palette indices.

The Core remains free of third-party numerical-array types.

A future move to another compact representation remains possible, but its
memory, dependency and boundary implications must be evaluated explicitly.