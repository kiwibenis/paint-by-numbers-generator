# ADR-0015 - Geometry Predicate Acceleration

## Status

Accepted

## Context

Pairwise outline overlap validation is a computationally expensive part of
outline processing.

The pure Python implementation defines the required overlap semantics, but
measurements on representative generation workloads showed that predicate
evaluation can dominate complete outline processing. A compiled geometry
library with a spatial index reduced that cost substantially while producing
the same overlap results.

The performance difference is large enough that the reference implementation
and the accelerated implementation do not represent interchangeable production
paths. Silently falling back to the reference implementation would allow the
same generation request to have materially different runtime characteristics
depending only on whether an optional dependency happened to be available.

The pure Python implementation nevertheless remains valuable as an executable
definition of the expected behavior. It provides an independent reference
against which the accelerated implementation can be tested.

The geometry library is native code. Introducing it as a mandatory dependency
therefore increases dependency and native-code exposure. It does not parse
user-supplied files directly; it receives outline coordinates already produced
by the application's generation pipeline.

The library's geometry model also differs from the project's raster geometry
rules in one important respect. Raster outlines that touch themselves at a
single traced point are deliberately tolerated by the project, while a general
geometry library may classify such rings as invalid. Pairwise acceleration must
not therefore transfer ownership of individual outline validity to the
external library.

## Decision

Pairwise overlap detection between distinct region outlines shall use a
compiled geometry library during normal generation.

The geometry library shall be a mandatory runtime dependency.

An installation in which the required geometry library is absent or cannot be
loaded is not a supported degraded mode. Generation shall fail rather than
silently execute the substantially slower reference path.

An absent library shall be distinguishable from a library that is installed
but cannot be loaded, because the failures require different operator action.

The pure Python overlap implementation shall remain in the Core as the
reference behavior. It defines the expected overlap semantics and shall remain
directly executable for tests, differential validation and developer
diagnostics.

The application shall not use the reference implementation as a production
fallback.

Acceleration is confined to pairwise overlap detection between distinct
outlines.

Individual outline and ring validity, including the deliberately tolerated
raster self-touch behavior, remains Core responsibility and shall not be
delegated to the geometry library.

The geometry library shall remain outside the Core in accordance with
ADR-0003.

The Application layer shall expose the overlap-detection dependency through
`OverlapDetectorPort`. The concrete geometry-library implementation shall live
in Infrastructure and shall be supplied to generation through that boundary.

Overlap is defined by positive shared interior area.

Two outlines overlap only when their intersection area exceeds an explicit
positive threshold. Shared boundaries, shared vertices and touching corners
are not overlaps. The implementation shall not rely on an exact floating-point
comparison with zero.

Interior holes shall preserve the semantics of the project's multi-ring
`Outline` model. A hole interior is outside the owning region.

Geometry-library validity shall not become the project's definition of outline
validity.

When the library requires a geometry repair before pairwise area evaluation,
the repair may be used only when it preserves the enclosed area and the
relevant topology. A repair that changes those semantics shall cause the
operation to fail rather than allowing the accelerated implementation to
decide a case differently from the reference implementation.

Once accelerated evaluation has begun, a failure shall fail the operation.
The application shall not retry the same evaluation through the reference
implementation.

The accelerated implementation and the reference implementation shall produce
equivalent overlap results.

Differential tests shall cover at least:

- outlines without holes;
- outlines with one hole;
- outlines with multiple holes;
- regions validly nested inside another region's hole;
- positive-area overlap across hole boundaries;
- tolerated raster self-touch cases;
- deterministic repeated execution;
- randomized representative outline sets.

Changing the mandatory geometry dependency, restoring a production fallback or
changing the overlap semantics requires an architectural decision rather than
an implementation-only change.

## Consequences

Normal generation has one supported overlap-detection path and cannot silently
degrade to a substantially slower implementation.

Outline overlap validation no longer dominates the representative workloads
that motivated the acceleration.

Every installation carries the compiled geometry dependency. This increases
installation complexity and native-code exposure compared with the pure Python
implementation.

An unavailable geometry library now prevents generation instead of degrading
performance.

The pure Python implementation remains shipped code even though normal
generation does not use it. Differential tests are therefore required to keep
the reference implementation and accelerated implementation aligned.

Core geometry semantics remain independent of the external geometry library.
In particular, individual ring validity and tolerated raster self-touch
behavior remain controlled by the Core.

The geometry implementation remains replaceable because the external library
is confined to Infrastructure behind the Application overlap-detection
boundary.

Detailed performance measurements remain supporting evidence rather than part
of the architectural contract. They may be updated as hardware and the
implementation evolve without changing this decision.