# ADR-0012 - Normalized User Inputs

## Status

Accepted

## Context

The application receives values originating outside the generator.

Those values may come from command-line arguments, configuration, files or
another integrating application.

External representations shall not become the vocabulary of Core business
logic.

The Core should be able to operate on validated project-owned values without
having to understand file formats, parser objects, interface syntax or other
external representation details.

Images are a particularly important case because decoding and validation
require Infrastructure behavior before a normalized image can safely be used by
generation.

The detailed untrusted-image boundary is governed by ADR-0016.

## Decision

External input shall be validated and normalized before Core business logic
depends on it.

The layer in which validation occurs depends on the responsibility of the
input.

Interface-specific syntax may be parsed at the interface boundary.

Application configuration may be validated and resolved by the Application
layer.

Inputs that require an external parser, decoder or other third-party
implementation shall cross an Infrastructure boundary before their normalized
project-owned representation is supplied to Core behavior.

Core APIs shall use project-owned domain models, project-owned value types or
appropriate primitive immutable values rather than third-party parser or
decoder objects.

Validation shall reject an invalid external representation rather than allowing
the Core to infer, repair or reinterpret it implicitly.

Normalization shall remove representation details that are not part of the
generator's domain semantics.

For image input, normal Application generation shall use the mandatory image
loading boundary defined by ADR-0016.

The result of that boundary shall be `InputImage`.

The Core shall not receive:

- raw image files;
- decoder-specific image objects;
- unchecked image metadata;
- third-party image-library types.

The supported image formats, resource limits, decoder restrictions, format
detection and JPEG auxiliary-frame exception are governed by ADR-0016 rather
than by this ADR.

Dependency and domain-model boundaries remain governed by ADR-0003 and
ADR-0008.

Introducing a normal Core use case that depends directly on an unvalidated
external representation or third-party input object requires an architectural
decision.

## Consequences

Core business logic operates on validated project-owned representations rather
than on interface or parser details.

Different interfaces may perform their own syntax handling without creating
different Core semantics.

Validation responsibility can reside in the layer that owns the relevant
boundary instead of forcing every kind of user input through Infrastructure.

Image decoding remains an Infrastructure concern while normal generation
receives only `InputImage`.

Image-specific security and format policy has one architectural source of truth
in ADR-0016.

The Core remains easier to test deterministically because tests can construct
normalized project-owned values directly without reproducing external parsers
or file formats.