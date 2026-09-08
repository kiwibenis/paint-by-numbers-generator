# ADR-0001 - Layered Architecture

## Status

Accepted

## Context

The project is intended to remain maintainable, testable and extensible while
supporting both direct Python use and external interfaces such as the command
line.

Generation contains deterministic domain behavior, use-case orchestration,
external-library integration and interface-specific concerns.

Keeping those responsibilities separate prevents business semantics from
becoming coupled to a particular interface, storage mechanism or third-party
implementation.

## Decision

The application shall use four conceptual architectural layers:

- CLI;
- Application;
- Core;
- Infrastructure.

The Core owns the project's domain models, deterministic generation semantics
and business rules.

Core responsibility is architectural rather than directory-based. Core code may
be organized into responsibility-specific packages when that produces a clearer
source structure; it is not required to reside physically under one directory
named `core`.

The Core shall not depend on CLI or Infrastructure concerns.

The Application layer owns use-case orchestration.

Application code may:

- coordinate Core operations;
- resolve execution policy from validated configuration;
- define ports required by a use case;
- select between equivalent Core execution strategies;
- assemble the inputs required by Core services.

The Application layer shall not contain concrete third-party integrations.

Infrastructure owns concrete external integrations such as image decoding,
document serialization, process execution and compiled geometry adapters.

Infrastructure may implement Application ports and translate between external
representations and project-owned models.

The CLI is an interface and composition boundary.

CLI code may:

- parse command-line input;
- compose Application and Infrastructure components;
- invoke Application use cases;
- present progress, results and failures according to the CLI contract.

The CLI shall not define generation business semantics.

Dependency boundaries involving third-party runtime libraries are governed by
ADR-0003.

Project-owned domain-model boundaries are governed by ADR-0008.

A change that moves generator business semantics into an interface or concrete
Infrastructure implementation, or makes the Core depend on an outer layer,
requires an architectural decision.

## Consequences

The same Core behavior can be used by the command line, Python callers and
future interfaces.

Use-case orchestration can evolve independently from deterministic generation
semantics.

External libraries and operating-system mechanisms remain replaceable behind
project-owned boundaries.

The source tree can organize Core responsibilities by domain concern without
making package layout itself define the architecture.

Maintaining these boundaries requires some explicit ports, adapters and
translation code.