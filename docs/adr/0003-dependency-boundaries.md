# ADR-0003 - Dependency Boundaries

## Status

Accepted

## Context

The project depends on external libraries for implementation concerns such as
image decoding, document serialization and accelerated geometry operations.

Allowing those dependencies to spread through the application would couple
business logic to concrete implementations and make replacement, testing and
maintenance more difficult.

The layered architecture of ADR-0001 therefore requires an explicit boundary
between project-owned logic and third-party implementations.

## Decision

External runtime libraries shall be confined to the Infrastructure layer.

The Core shall not directly import or depend on third-party runtime libraries.

The Application layer shall depend on project-owned ports, models and services
rather than on concrete third-party implementations.

Infrastructure may implement Application ports or other project-owned
boundaries by using external libraries.

Values crossing from Infrastructure toward the Core shall use project-owned
models or primitive immutable representations rather than third-party types.

Values crossing toward Infrastructure shall likewise be expressed through
project-owned interfaces and models. Infrastructure is responsible for
translating those values into whatever representation a concrete library
requires.

CLI code shall compose Application and Infrastructure components but shall not
move third-party implementation details into the Core or Application
contracts.

Tests and developer tooling may use external libraries directly when required
to exercise or measure Infrastructure behavior. That does not make those
libraries part of the Core architecture.

Introducing a third-party runtime dependency directly into the Core or into an
Application contract requires an architectural decision.

## Consequences

Business logic remains independent from concrete external libraries.

Third-party implementation changes are localized to Infrastructure and their
composition boundaries.

Application ports remain testable with project-owned fakes and test doubles.

External libraries can be replaced without changing Core business semantics as
long as the replacement preserves the relevant project-owned contract.

Some translation code is required at Infrastructure boundaries, but that cost
prevents implementation-specific types and behavior from spreading through the
project.