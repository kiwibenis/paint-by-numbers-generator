# ADR-0018 - Packed Pixel Indices for Region Membership

## Status

Accepted

## Context

A region contains a set of raster coordinates describing which pixels belong
to it.

Region processing performs large numbers of membership and neighborhood
queries for concerns such as adjacency, perimeter calculation, circle fitting,
outline tracing and label placement.

Storing each coordinate as a Python tuple inside a set adds significant memory
and allocation overhead. It also requires constructing coordinate tuples for
many neighbor probes.

Unlike the compact sequential image storage governed by ADR-0017, region
membership needs efficient set lookup rather than dense row-major traversal.

A raster coordinate can be encoded reversibly in one integer when the row
stride is larger than every supported x-coordinate.

## Decision

`Region.pixels` shall be represented as `frozenset[int]`.

Each raster coordinate shall be packed as:

```text
(y << 32) | x
```

which is equivalent to:

```text
y * 2^32 + x
```

The shared row stride shall therefore be:

```text
2^32
```

Packing and unpacking shall be owned by one project module.

Consumers shall not independently define another stride or open-code a
different coordinate representation.

The packing module shall expose the canonical operations required to:

- pack one coordinate;
- unpack one packed index;
- pack a collection of coordinates;
- iterate unpacked coordinates.

Both coordinates are required to be non-negative and no greater than
`2^32 - 1`.

That requirement is a precondition of the packing operation rather than a
runtime check on every packed pixel.

Membership-driven Core algorithms should operate directly on packed indices
and constant neighbor offsets where appropriate.

Algorithms that genuinely require raster coordinates may unpack them at their
boundary.

`Region` shall expose `coordinates()` for callers that require coordinate
pairs without making coordinate tuples the stored representation.

Packing is a storage and lookup decision only. It shall not change region
membership, adjacency semantics, geometry, deterministic ordering or generated
output.

If the supported raster coordinate range ever reaches or exceeds `2^32` in
either dimension, this representation shall be revisited before such images
are accepted.

Changing the packed coordinate scheme or replacing it with another
region-membership representation requires an architectural decision when the
change affects the shared Core representation or its invariants.

## Consequences

A region stores one integer object per member instead of a coordinate tuple and
its component references.

Membership-driven algorithms can derive horizontal and vertical neighbors by
integer arithmetic without allocating temporary coordinate tuples.

The representation is less immediately readable while debugging than explicit
`(x, y)` tuples. `Region.coordinates()` and the shared unpacking helpers
provide the readable form when needed.

All consumers depend on the same packing invariant, so the stride and bit
layout become shared Core representation rules.

Performance benefits depend on hot-path consumers remaining on the packed
representation rather than unpacking complete regions before processing them.

The `2^32` coordinate bound is far above the dimensions permitted by the
current input profiles, but it is nevertheless a hard representation
precondition that future input-limit changes must respect.