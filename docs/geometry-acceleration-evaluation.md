# Geometry Acceleration Evaluation

## Purpose

This document records the current evaluation basis for accelerated outline
overlap detection.

It documents:

- the overlap predicate used by normal generation;
- the architectural boundary between Core semantics and accelerated
  Infrastructure;
- the retained pure-Python reference implementation;
- equivalence requirements;
- the current performance evidence;
- deterministic-output validation;
- failure semantics;
- conditions that require revalidation.

It records the current state only.

Implementation experiments and superseded performance measurements are
intentionally not retained here.

The binding architectural decision is
[ADR-0015 - Geometry Predicate Acceleration](adr/0015-geometry-predicate-acceleration.md).

## Current Production Decision

Normal generation uses compiled geometry for pairwise overlap detection between
distinct outlines.

The current Infrastructure implementation is:

```text
src/pbn/infrastructure/shapely_overlap_detector.py
```

and uses Shapely.

The accelerated implementation is mandatory for normal generation.

There is no production fallback to the pure-Python reference predicate.

If the required geometry implementation is unavailable or fails during normal
generation, generation fails rather than silently switching to the slower
reference path.

The pure-Python implementation remains available for:

- differential validation;
- focused correctness tests;
- developer diagnostics.

It is not an alternate production execution mode.

## Architectural Boundary

Overlap semantics belong to the project.

The external geometry implementation does not define the business rule.

The Application depends on:

```text
OverlapDetectorPort
```

rather than on Shapely directly.

The current responsibility split is:

```text
Core
    owns outline and overlap semantics
    owns the reference implementation
    owns individual outline validity rules

Application
    depends on OverlapDetectorPort
    supplies the overlap detector to generation

Infrastructure
    converts project-owned outlines to Shapely geometry
    performs accelerated pairwise overlap detection
    translates external failures into project errors

CLI
    composes the required Infrastructure implementation
```

This follows:

- [ADR-0001 - Layered Architecture](adr/0001-layered-architecture.md);
- [ADR-0003 - Dependency Boundaries](adr/0003-dependency-boundaries.md);
- [ADR-0015 - Geometry Predicate Acceleration](adr/0015-geometry-predicate-acceleration.md).

Shapely objects do not cross into Core domain models.

## Scope of Acceleration

The accelerated boundary applies specifically to:

```text
pairwise overlap detection between distinct outlines
```

It does not replace all Core geometry behavior.

The Core remains responsible for operations including:

- outline tracing;
- ring structure;
- outer-ring and hole semantics;
- individual ring validity;
- individual outline validity;
- topology-preserving outline simplification;
- deterministic reference overlap semantics.

The compiled dependency is therefore a focused predicate accelerator rather
than the owner of the project's geometry model.

## Outline Representation

A project `Outline` contains:

```text
one outer ring
zero or more hole rings
```

The Infrastructure adapter maps one outline to one Shapely polygon:

```text
Outline.points
    -> polygon shell

Outline.hole_rings
    -> polygon holes
```

Ring and vertex order are preserved during this conversion.

Hole interiors remain outside the owning region.

Consequently, a valid region located entirely inside another region's hole is
not considered to overlap the surrounding region.

## Overlap Semantics

Two distinct outlines overlap when they share positive interior area above the
project's numerical tolerance.

The current accelerated implementation uses:

```text
intersection.area > 1e-9
```

after confirming that the polygon pair intersects.

The following are therefore not classified as overlap:

- polygons that do not intersect;
- polygons that only touch at an edge;
- polygons that only touch at a vertex;
- a polygon located entirely inside a hole of another outline.

Positive shared interior area is classified as overlap.

Hole boundaries and outer boundaries participate according to normal polygon
interior semantics.

## Canonical Pair Results

Overlap results are expressed using project region identifiers.

Every reported pair is canonicalized as:

```text
(
    min(region_id_a, region_id_b),
    max(region_id_a, region_id_b)
)
```

The complete result is sorted deterministically.

The observable result therefore does not depend on:

- spatial-index traversal order;
- Shapely query ordering;
- object identity;
- dictionary ordering.

## Accelerated Search

The Infrastructure implementation converts the supplied outlines into Shapely
polygons and builds an `STRtree` spatial index.

The spatial index is used to identify candidate geometry pairs whose spatial
bounds may intersect.

Only those candidate pairs require the more expensive exact intersection
predicate.

For each candidate pair, the implementation:

1. ignores self-pairs and duplicate reverse comparisons;
2. checks whether the polygons intersect;
3. computes the intersection when required;
4. accepts the pair only when shared interior area exceeds the overlap
   tolerance;
5. converts the result back to canonical project region identifiers.

This reduces the number of expensive polygon comparisons required for large
outline sets while preserving the project overlap semantics.

## Why Acceleration Is Required

Pairwise overlap validation can dominate topology-preserving outline
simplification when a generated document contains many large or complex
outlines.

A focused real-workload measurement on:

```text
1,216 reduced outlines
```

recorded:

```text
complete topology simplification:
    433.012157 s

individual outline validation:
    0.868450 s

pairwise overlap validation:
    427.224537 s
```

Pairwise overlap detection therefore accounted for approximately:

```text
99.80% of measured validation time

98.66% of complete topology-simplification runtime
```

in that workload.

The generation parameters that produced those 1,216 outlines are not
recorded here, so the figure is retained as evidence of the concentration
rather than as a reproducible run.

A reproduction with its parameters recorded, on the shipped profile:

```text
python -m tools.benchmark_region_complexity_geometry_validation
```

```text
case=complex, palette=reference8, palette_version=1,
color_distance=delta_e_2000, minimum_region_size_mm=2,
maximum_merge_cost=0.3, target_fraction=0.5

79 reduced outlines

complete topology simplification:
    340.245515 s

individual outline validation:
    1.063530 s

pairwise overlap validation:
    334.019333 s
```

which is:

```text
99.68% of measured validation time

98.17% of complete topology-simplification runtime
```

The two workloads differ by more than an order of magnitude in outline
count, and the concentration is the same in both. The reproduction is the
smaller of the two and is kept for its recorded parameters rather than for
its size.

The relevant performance problem is consequently not individual polygon
validity checking.

It is the repeated relationship test between distinct outlines.

This concentration of runtime is the reason the accelerated boundary targets
pairwise overlap detection specifically.

## Reference Implementation

The project retains a pure-Python overlap implementation as the semantic
reference.

Its purpose is correctness comparison.

The reference path defines observable project behavior independently from the
external geometry library.

The accelerated implementation must agree with the reference implementation
for supported valid project geometry.

This allows the project to optimize the predicate without making a third-party
library the definition of paint-by-numbers topology.

## Differential Validation

Reference and accelerated results are compared directly.

The dedicated differential coverage includes:

```text
tests/test_shapely_overlap_detector_differential.py
```

The Infrastructure contract itself is covered by:

```text
tests/test_shapely_overlap_detector.py
```

The real-workload benchmark comparison is implemented in:

```text
tools/benchmark_region_complexity_geometry_validation.py
```

with corresponding automated coverage in:

```text
tests/test_benchmark_region_complexity_geometry_validation.py
```

The benchmark:

1. constructs the same outline set;
2. evaluates all relevant overlap relationships with the Core reference;
3. evaluates the same relationships through `ShapelyOverlapDetector`;
4. compares the resulting canonical overlap-pair sets;
5. reports the reference duration;
6. reports the accelerated duration;
7. reports the measured speedup;
8. reports whether the results are equivalent.

Performance is relevant only when equivalence is preserved.

A faster result with different overlap semantics is invalid.

## Topology Cases

Validation covers geometry properties that are significant to the domain,
including:

- disjoint outlines;
- positive-area overlap;
- edge touching;
- vertex touching;
- outer rings;
- hole rings;
- valid regions nested inside holes;
- overlap involving multi-ring outlines.

Related topology behavior is also covered by the outline simplifier and
geometry-validator test suites.

The accelerated implementation must preserve the same hole and touching
semantics as the Core reference.

## End-to-End Performance Evidence

The retained production decision is supported by complete generation
measurements rather than only isolated predicate timings.

### Primary Complex-Case Measurement

On one measured system:

| Configuration | Reference predicate | Accelerated predicate | Speedup |
|---|---:|---:|---:|
| Complexity reduction disabled | `367.333 s` | `118.281 s` | `3.11x` |
| Complexity reduction enabled | `925.832 s` | `168.340 s` | `5.50x` |

The improvement is therefore visible in complete document generation.

It is not confined to an isolated overlap benchmark.

### Independent Machine Measurement

An independent measurement on another machine produced:

| Case | Reference predicate | Accelerated predicate | Speedup |
|---|---:|---:|---:|
| `complex_smaller` | `157.177 s` | `38.169 s` | `4.12x` |
| `complex` | `795.106 s` | `79.399 s` | `10.01x` |

The absolute speedup differs materially between systems.

No single geometry speedup factor should therefore be treated as a universal
constant.

The durable conclusion is:

```text
compiled pairwise overlap detection provides a material end-to-end benefit
on complex production workloads
```

and that conclusion was reproduced on more than one machine.

## Hardware Dependence

The measured ratio between reference and accelerated generation is
hardware-dependent.

The pure-Python reference predicate is primarily constrained by sequential
Python execution.

The complete accelerated generation path also contains work such as parallel
quantization that can make stronger use of additional CPU cores.

Different systems can therefore produce materially different whole-pipeline
speedup ratios even when the overlap predicate itself preserves identical
semantics.

Performance documentation should retain representative measurements rather
than present one universal ratio.

## Relationship to Region Complexity Reduction

Optional region complexity reduction can create fewer but geometrically larger
regions.

Those regions can contain:

- larger outer boundaries;
- more hole rings;
- larger bounding boxes;
- more expensive pairwise geometry relationships.

As a result, optional reduction can increase downstream topology-validation
cost even though the number of regions decreases.

The geometry predicate is therefore part of the end-to-end performance
boundary of region complexity reduction.

With the accelerated production predicate the geometry predicate is no longer
the dominant cost of optional reduction.

The complete-generation comparison, the resulting overhead and the accepted
bound are measured and recorded separately, because they depend on the shipped
paintability policy and on the outline-simplification setting rather than on
the predicate alone.

Those measurements are documented in:

- [`performance-measurements.md`](performance-measurements.md);
- [`region-complexity-calibration.md`](region-complexity-calibration.md).

## Deterministic Output Validation

Accelerated predicates must preserve generated output.

The current evaluation confirmed equivalence at multiple levels.

### Outline Level

`OutlineTopologySimplifier.simplify` produced identical outline tuples on the
reference and accelerated paths for:

```text
example_smaller
example
simple_smaller
medium_smaller
complex_smaller
```

### PDF Level

For the complex complete-generation comparison, reference and accelerated PDF
files had identical sizes.

The remaining byte differences were limited to:

```text
/CreationDate
/ModDate
ReportLab /ID
```

The ReportLab document identifier is derived from creation-time information.

PDF page-content streams were byte-identical.

An independent machine reproduced the same result: differences were confined
to the same time-dependent metadata fields.

The accelerated predicate therefore does not introduce observable generated
content differences in the evaluated workflows.

## Failure Semantics

The accelerated geometry implementation is mandatory for normal generation.

Failure must therefore be explicit.

Normal generation must not silently continue through the pure-Python reference
path when:

- Shapely is unavailable;
- the geometry adapter cannot construct a valid required external geometry;
- an external geometry operation fails.

The Infrastructure boundary translates geometry failures into the project's
error model.

This fail-closed behavior is important both architecturally and operationally.

A silent reference fallback would materially change the expected runtime of a
request and would make resource behavior depend on an unavailable production
dependency.

That would conflict with the mandatory-production-path decision in ADR-0015.

## Individual Geometry Validity

Compiled pairwise overlap detection does not transfer ownership of individual
outline validity to Shapely.

Individual ring and outline validity remain Core behavior.

The Infrastructure adapter may reject a polygon that cannot be represented
safely by the external geometry library, but the project's own validity rules
remain independent from that external implementation.

This distinction prevents implementation-specific geometry behavior from
becoming the project's domain definition.

## Performance Measurement Tool

The current focused evaluation can be run through:

```text
python -m tools.benchmark_region_complexity_geometry_validation
```

It is run as a module because it imports from a sibling module under
`tools/`, which a script invocation cannot resolve.

Run without arguments it takes its generation policy from
`config/example.toml`, including the paintability minimum. It previously
defaulted `--minimum-region-size-mm` to `1.0` and applied that to the loaded
profile, so a run without arguments measured half the shipped value.

The tool uses project benchmark inputs and compares the reference and
accelerated overlap-pair results on the same generated outline set.

It reports both:

```text
equivalence
```

and:

```text
performance
```

because both are required for retaining the accelerated implementation.

Performance results from this tool are developer measurements.

They are not used as timing assertions in normal unit tests.

## Correctness Tests

The most relevant current automated coverage includes:

```text
tests/test_shapely_overlap_detector.py
tests/test_shapely_overlap_detector_differential.py
tests/test_benchmark_region_complexity_geometry_validation.py
tests/test_outline_geometry_validator.py
tests/test_outline_geometry_validator_holes.py
tests/test_outline_topology_simplifier.py
tests/test_outline_topology_simplifier_holes.py
tests/test_outline_topology_simplifier_overlap.py
```

The test suite is the authoritative source for the complete current test
inventory.

This document does not record test counts because those values change as the
suite evolves.

## Dependency Boundary

Shapely is a runtime Infrastructure dependency.

Its dependency version and current security state are intentionally not
duplicated here.

Those time-sensitive details are maintained in:

- [`dependency-security.md`](dependency-security.md).

A dependency upgrade that changes geometry behavior must preserve the
`OverlapDetectorPort` contract and the project overlap semantics.

## Revalidation Requirements

Geometry acceleration must be re-evaluated after a material change to:

- the `Outline` domain representation;
- outer-ring or hole semantics;
- overlap semantics;
- numerical overlap tolerance;
- topology-preserving simplification;
- the `OverlapDetectorPort` contract;
- Shapely polygon conversion;
- spatial-index candidate construction;
- the external geometry library when its predicate behavior may have changed;
- a supported Python runtime when the geometry dependency changes materially;
- generation behavior that substantially changes outline-count or
  outline-complexity distributions.

Correctness revalidation must compare accelerated behavior with the Core
reference.

A performance-sensitive change must also be measured end to end when it can
materially affect complete generation.

## Current Status

The current geometry-acceleration state is:

```text
normal production overlap detector:
    ShapelyOverlapDetector

production fallback:
    none

Core reference implementation:
    retained for tests and diagnostics

accelerated search:
    STRtree candidate filtering

overlap rule:
    positive shared interior area above 1e-9

hole semantics:
    preserved

touch-only contact:
    not overlap

deterministic canonical pair ordering:
    preserved

reference/accelerated equivalence:
    validated

generated outline equivalence:
    validated

generated PDF content equivalence:
    validated

material end-to-end speedup:
    validated on multiple machines

production decision:
    accelerated path retained and mandatory
```

## Related Documentation

For the binding architectural decision, see:

- [`adr/0015-geometry-predicate-acceleration.md`](adr/0015-geometry-predicate-acceleration.md).

For the surrounding architecture, see:

- [`architecture-overview.md`](architecture-overview.md).

For current general generation-performance measurements, see:

- [`performance-measurements.md`](performance-measurements.md).

For optional complexity semantics and calibration, see:

- [`algorithms/region-complexity-reduction.md`](algorithms/region-complexity-reduction.md);
- [`region-complexity-calibration.md`](region-complexity-calibration.md).

For current dependency state, see:

- [`dependency-security.md`](dependency-security.md).

For current planned and remaining work, see:

- [`../ROADMAP.md`](../ROADMAP.md).