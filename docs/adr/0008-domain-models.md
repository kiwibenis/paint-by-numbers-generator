# ADR-0008 - Domain Models

## Status

Accepted

## Context

The generator exchanges images, colors, palettes, regions, outlines, labels and
generated document data across several processing stages.

External libraries use their own object models for concerns such as image
decoding, geometry operations and document serialization.

Using those third-party objects as the application's business vocabulary would
couple Core behavior to implementation choices and would weaken the dependency
boundary defined by ADR-0003.

The project therefore needs its own stable representation of the concepts on
which generation semantics depend.

## Decision

Business logic shall operate on project-owned domain models.

The Core shall not expose or depend on third-party types.

Data entering the Core through an Infrastructure boundary shall be normalized
into project-owned models or primitive immutable values before it crosses that
boundary.

Infrastructure consuming Core output shall receive project-owned models and
shall translate or serialize them as required by the concrete external
implementation.

Application ports shall express their contracts using project-owned models,
project-owned value types or appropriate primitive values.

Domain models shall represent generator semantics rather than the API shape of
a particular external library.

A model shall not acquire implementation-specific fields solely because a
third-party library exposes them.

Format-independent concepts shall remain format-independent in the domain. For
example, generated vector content is represented by `VectorDocument`; the PDF
serializer that consumes it is an Infrastructure concern governed by ADR-0027.

New domain models may be introduced when the Core gains a new business concept
that cannot be represented clearly by the existing models.

## Consequences

The Core has one project-owned vocabulary for generation behavior.

External library upgrades or replacements do not require business logic to
adopt new third-party object types.

Infrastructure boundaries perform explicit normalization, translation or
serialization.

Application ports remain independent from concrete external implementations.

Some information exposed by an external library may deliberately be discarded
when it is not part of the generator's domain semantics.

Domain models remain reusable across the command-line interface, future
graphical interfaces and other Application consumers.