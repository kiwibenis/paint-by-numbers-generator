# Region Complexity Reduction

## Purpose

Optional region complexity reduction reduces the number of paint-by-numbers
regions when sufficiently low-risk neighboring merges are available.

The reduction is quality-bounded rather than target-forcing.

Two configuration values control when reduction stops:

- `max_regions` defines the desired upper region-count target;
- `maximum_merge_cost` defines the maximum acceptable cost of an optional
  merge.

The reducer does not force the result to `max_regions`.

A result containing more than `max_regions` is valid when no remaining merge
candidate satisfies the configured quality boundary.

Zero accepted optional merges is also a valid result.

Optional complexity reduction is separate from mandatory paintability
processing. It cannot disable, weaken or replace the global
`minimum_region_size_mm` constraint.

## Position in the Generation Pipeline

Region processing follows this order:

1. quantize the normalized input image to the selected reference palette;
2. detect connected palette-color regions;
3. apply mandatory paintability merging;
4. verify mandatory paintability;
5. optionally apply region complexity reduction;
6. verify paintability again.

The optional reducer therefore receives regions that have already passed
mandatory paintability processing.

`minimum_region_size_mm` is resolved by the Application layer into
`minimum_circle_diameter_px` before Core region processing begins.

The same resolved pixel-space constraint is passed to both mandatory and
optional region processing.

## Architectural Responsibilities

The reduction algorithm is Core behavior.

The Core owns:

- region adjacency;
- directed merge-candidate construction;
- raw merge metrics;
- merge-cost calculation;
- deterministic candidate ranking;
- paintability preservation;
- region merging;
- deterministic result ordering.

The Application layer owns policy construction from validated configuration.

When optional complexity reduction is enabled, the Application:

1. resolves the configured color-distance strategy;
2. builds the configured detail-preserving merge-cost calculator;
3. constructs `RegionComplexityReducer`;
4. binds `max_regions` and `maximum_merge_cost`;
5. supplies the configured reducer to the generation pipeline.

The Core does not read TOML, CLI arguments or `GeneratorConfig`.

The relevant architectural boundaries are defined by:

- [ADR-0001 - Layered Architecture](../adr/0001-layered-architecture.md);
- [ADR-0003 - Dependency Boundaries](../adr/0003-dependency-boundaries.md);
- [ADR-0008 - Domain Models](../adr/0008-domain-models.md).

## Inputs

The Core reducer operates on:

```text
regions
minimum_circle_diameter_px
max_regions
maximum_merge_cost
```

The reducer also receives:

- the configured `ColorDistance` strategy;
- a configured `RegionMergeCostCalculator`.

Normal configured generation uses
`DetailPreservingRegionMergeCostCalculator`.

The color-distance strategy used for merge evaluation is resolved from the
same generation configuration that controls palette quantization.

## Directed Merge Semantics

Merge candidates are directed.

For two adjacent regions `A` and `B`, the reducer may evaluate both:

```text
A -> B
B -> A
```

These are different candidates.

The direction determines:

- which region is the source;
- which region is the target;
- which palette color survives;
- the affected-area ratio;
- the source-border ratio;
- source compactness;
- target-relative geometry change.

When a candidate is accepted:

```text
source -> target
```

the source region is removed.

The target region retains:

- the target region identifier;
- the target palette color.

Its pixels become the union of the source and target pixels.

The reducer therefore never creates an averaged, interpolated or newly selected
palette color during a merge.

## Candidate Eligibility

Initial candidates are created only between adjacent regions.

Adjacency is based on shared raster borders.

For every adjacent source-target pair, the reducer calculates the raw metrics
required by the configured merge-cost model.

A candidate is not accepted merely because two regions are adjacent. It must
also:

- remain within the configured `maximum_merge_cost`;
- preserve the paintability constraint.

## Raw Merge Metrics

Each directed candidate contains the following raw measurements:

```text
color_difference

source_area
target_area
merged_area

affected_area_ratio

shared_border_length

source_perimeter
target_perimeter
merged_perimeter
```

### Color Difference

`color_difference` is calculated between the Lab colors of the source and
target regions using the configured `ColorDistance` strategy.

The supported generation strategies are documented separately under:

- [`delta-e-76.md`](delta-e-76.md);
- [`delta-e-2000.md`](delta-e-2000.md).

### Affected Area Ratio

The affected-area ratio is:

```text
affected_area_ratio =
    source_area / merged_area
```

A larger source therefore represents a larger fraction of the resulting
region.

The metric is directional because swapping source and target changes the
source area.

### Shared Border

The source shared-border ratio is:

```text
source_shared_border_ratio =
    shared_border_length / source_perimeter
```

It measures how much of the source region's boundary is already shared with
the target.

The corresponding target ratio can also be derived from the raw metrics, but
the current merge-cost model uses the source ratio.

### Source Compactness

Source compactness uses normalized isoperimetric compactness:

```text
source_compactness =
    min(
        1,
        4 * pi * source_area / source_perimeter^2
    )
```

Source non-compactness is:

```text
source_non_compactness =
    1 - source_compactness
```

Compact regions approach `1` compactness.

Elongated, narrow or otherwise irregular source regions produce higher
non-compactness.

### Geometry Complexity

Region geometry complexity is represented as:

```text
geometry_complexity =
    perimeter^2 / area
```

The directed geometry change is:

```text
geometry_change =
    merged_geometry_complexity
    - target_geometry_complexity
```

The geometry term therefore evaluates how merging the source changes the
geometry of the target region.

## Base Merge Cost

The base merge cost consists of four normalized penalties:

```text
color_penalty
affected_area_penalty
border_penalty
geometry_penalty
```

Their configured weights are:

```text
color_weight
affected_area_weight
border_weight
geometry_weight
```

The weights are finite and non-negative and must sum to:

```text
1.0
```

### Color Penalty

For color distance `d`:

```text
color_penalty =
    d / (d + 10)
```

The penalty is monotonic with color difference and approaches `1` as the
distance increases.

A zero color difference produces a zero color penalty.

### Affected Area Penalty

The affected-area penalty is:

```text
affected_area_penalty =
    source_area / merged_area
```

This makes larger source regions more expensive to absorb than smaller source
regions, all other signals being equal.

### Border Penalty

The border penalty is:

```text
border_penalty =
    1 - source_shared_border_ratio
```

A source that shares a larger fraction of its perimeter with the target
therefore receives a lower base border penalty.

### Geometry Penalty

Only positive target-relative geometry-complexity changes are penalized.

First:

```text
positive_geometry_change =
    max(0, geometry_change)
```

If the result is zero:

```text
geometry_penalty = 0
```

Otherwise:

```text
geometry_penalty =
    positive_geometry_change
    /
    (
        target_geometry_complexity
        + positive_geometry_change
    )
```

A merge that leaves target geometry equally or less complex therefore receives
no geometry penalty.

### Weighted Base Cost

The base cost is:

```text
base_cost =
    color_weight * color_penalty
    + affected_area_weight * affected_area_penalty
    + border_weight * border_penalty
    + geometry_weight * geometry_penalty
```

Normal configured generation supplies all four weights explicitly through the
validated generation policy.

The reducer does not define a hidden production weighting policy.

## Detail-Preservation Adjustments

Normal configured generation applies two additional protection signals after
the weighted base cost:

1. enclosure protection;
2. compactness protection.

Both increase the cost of candidates that match their respective
detail-preservation signal.

They do not replace the four base penalties.

### Adjustment Function

Both protection stages use the same adjustment function:

```text
adjusted_cost =
    base_cost
    + strength
      * protection_penalty
      * (1 - base_cost)
```

This raises the existing cost toward `1` without replacing its base ordering
information.

### Enclosure Protection

The enclosure penalty is:

```text
enclosure_penalty =
    source_shared_border_ratio
    * color_penalty
    * (1 - affected_area_ratio)
```

The first adjusted cost is:

```text
enclosure_adjusted_cost =
    adjust(
        base_cost,
        enclosure_penalty,
        enclosure_strength
    )
```

The signal becomes stronger when:

- a large fraction of the source perimeter touches the target;
- source and target have a meaningful palette-color difference;
- the source occupies a relatively small fraction of the merged region.

The purpose is to make absorption of small, distinguishable source structures
more expensive when they are strongly surrounded by the target.

### Compactness Protection

The compactness penalty is:

```text
compactness_penalty =
    source_non_compactness
    * color_penalty
    * (1 - affected_area_ratio)
```

The final merge cost is:

```text
final_cost =
    adjust(
        enclosure_adjusted_cost,
        compactness_penalty,
        compactness_strength
    )
```

The signal becomes stronger when:

- the source is geometrically non-compact;
- source and target have a meaningful palette-color difference;
- the source occupies a relatively small fraction of the merged region.

This increases the cost of absorbing narrow, elongated or irregular
distinguishable source structures.

## Final Candidate Cost

`maximum_merge_cost` is compared against the final detail-preserving merge
cost.

It is not compared against the unadjusted base cost.

The stored `RegionMergeCost` retains the four normalized base penalty
components for diagnostics:

```text
color_penalty
affected_area_penalty
border_penalty
geometry_penalty
```

Its `value` is the final cost after enclosure and compactness protection.

## Deterministic Candidate Ordering

All evaluated candidates are ordered by:

```text
(
    final_cost,
    source_id,
    target_id
)
```

The lowest final cost is considered first.

Region identifiers therefore provide deterministic tie-breaking when multiple
candidates have the same cost.

This ordering is independent from dictionary iteration order or the order in
which the original regions were supplied.

## Paintability Preservation

Optional reduction receives the same
`minimum_circle_diameter_px` constraint used by mandatory paintability
processing.

Before accepting a candidate, the reducer verifies that the resulting target
region satisfies this constraint.

If the existing target already fits the required circle, the merge preserves
that paintable area because merging only adds source pixels.

Otherwise the reducer evaluates the complete merged pixel set.

A candidate that cannot satisfy the paintability requirement is skipped.

The generation pipeline verifies paintability again after optional reduction.

Optional complexity reduction can therefore simplify an already paintable
region set but cannot intentionally weaken the global paintability invariant.

## Reduction Loop

The reducer starts from the current active region set.

If:

```text
region_count <= max_regions
```

the input is returned unchanged.

Otherwise:

1. calculate adjacency;
2. build directed candidates between adjacent regions;
3. calculate metrics and final costs;
4. order candidates deterministically;
5. examine candidates from lowest to highest cost;
6. stop if the cheapest remaining cost exceeds `maximum_merge_cost`;
7. otherwise select the first candidate that preserves paintability;
8. merge the source into the target;
9. update affected adjacency and candidate evaluations;
10. repeat while the region count remains above `max_regions`.

The loop stops when either:

```text
region_count <= max_regions
```

or no acceptable candidate remains.

Consequently:

```text
max_regions
```

is a target, not a mandatory output count.

The quality boundary always has authority to stop reduction before that target
is reached.

## Quality Boundary Semantics

`maximum_merge_cost` expresses candidate acceptability.

It does not express:

- a required percentage of regions to remove;
- a required number of accepted merges;
- an image-independent reduction ratio.

Different images may therefore produce materially different reduction amounts
under the same policy.

That is expected behavior.

An image with many low-cost adjacent candidates can be reduced more strongly
than an image whose remaining candidates are structurally expensive.

The algorithm is successful when it refuses further reduction once all
remaining candidates exceed the configured quality boundary.

## Incremental Candidate Maintenance

After a normal merge, the reducer updates adjacency incrementally.

Candidate evaluations involving either the removed source or changed target are
invalidated.

New candidate evaluations are then calculated only for relationships touching
the changed target.

This avoids rebuilding every candidate after every accepted merge.

The optimization does not change candidate semantics or deterministic
ordering.

If the supplied region set contains overlapping pixels, the reducer does not
assume that the incremental adjacency update is valid. It recomputes adjacency
and candidate evaluations from the current active regions instead.

## Result Ordering

The final region tuple is ordered by ascending region identifier.

Accepted merges preserve the target identifier, so result ordering remains
deterministic across repeated executions.

## Developer Trace

Normal generation returns only the reduced region tuple.

For diagnostics, the reducer can additionally expose the actual accepted merge
sequence.

Each accepted `RegionMergeStep` records:

- the directed candidate;
- the raw metrics used for evaluation;
- the calculated merge cost.

The trace describes the merges that were actually accepted, not merely the
initial candidate ranking.

Developer tracing does not change normal reduction semantics.

## Configuration Validation

The Application validates the complete optional-complexity policy before
generation.

The relevant constraints include:

```text
region_complexity_reduction_enabled
    boolean

max_regions
    integer > 0

maximum_merge_cost
    finite
    0.0 <= value <= 1.0

merge-cost component weights
    finite
    non-negative
    sum exactly to 1.0 within validation tolerance

enclosure_strength
compactness_strength
    finite
    0.0 <= value <= 1.0
```

Concrete configuration syntax and CLI parameters are documented in
[`README.md`](../../README.md).

## Current Policy Versus Algorithm Semantics

The algorithm and its configuration policy are separate concerns.

This document defines how a supplied policy is interpreted.

It intentionally does not define one universal:

```text
maximum_merge_cost
max_regions
weight set
protection-strength set
```

as part of Core semantics.

Current shipped policy values are explicit configuration values rather than
hidden algorithm defaults.

Their selection must be supported by quality and performance evidence and must
be recalibrated when a material change to the merge-cost formulation,
quantization behavior or paintability baseline invalidates that evidence.

## Invariants

The current reducer preserves these invariants:

- mandatory paintability processing happens before optional reduction;
- optional reduction cannot disable mandatory paintability;
- only adjacent regions are merge candidates;
- candidates are directed;
- the target palette color survives an accepted merge;
- no new palette color is synthesized;
- `maximum_merge_cost` is a quality boundary;
- `max_regions` is a target rather than a forced result;
- zero optional merges is valid;
- candidate ordering is deterministic;
- ties are resolved by region identifiers;
- accepted merges preserve deterministic result ordering;
- configuration remains outside the Core;
- normal configured generation uses the configured detail-preserving cost
  model.

## Related Documentation

For the surrounding system architecture, see:

- [`../architecture-overview.md`](../architecture-overview.md).

For supported color-distance semantics, see:

- [`delta-e-76.md`](delta-e-76.md);
- [`delta-e-2000.md`](delta-e-2000.md).

For user-facing region-complexity configuration and CLI options, see:

- [`../../README.md`](../../README.md).

For planned or remaining work, see:

- [`../../ROADMAP.md`](../../ROADMAP.md).