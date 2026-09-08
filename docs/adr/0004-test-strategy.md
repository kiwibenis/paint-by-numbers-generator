# ADR-0004 - Test Strategy

## Status

Accepted

## Context

The project evolves through changes to algorithms, domain representations,
infrastructure boundaries and public integration behavior.

Many important properties are not visible from an individual implementation
unit. Determinism, sequential-versus-parallel equivalence, serialization
boundaries, configuration behavior and architectural invariants can regress
while a local implementation still appears correct.

Tests therefore form part of the project's change discipline and provide the
evidence required to refactor or replace implementations safely.

## Decision

Behavior introduced or changed by the project shall be covered by automated
tests at the narrowest useful boundary.

Public functionality shall have automated test coverage.

A bug fix shall include a regression test when the failure can be reproduced
deterministically.

Tests shall verify observable behavior rather than unnecessarily depending on
private implementation details.

Architectural invariants that can regress mechanically shall be tested where
practical.

Examples include:

- deterministic output and ordering;
- equivalence between reference and accelerated implementations;
- equivalence between sequential and parallel execution;
- dependency and layer boundaries;
- configuration validation;
- supported input-format boundaries;
- failure and error-disclosure contracts;
- compact representation invariants.

Infrastructure integrations shall have focused tests for the project-owned
contract they implement.

Reference implementations retained for differential validation shall remain
directly testable.

Performance claims shall be supported by dedicated benchmarks or measurement
tooling rather than by making ordinary unit tests depend on unstable timing
thresholds.

A logical implementation change shall not be considered complete while its
relevant automated tests are failing.

Tests may be refactored together with production code when the observable
contract remains unchanged, but a refactor shall not weaken the behavior being
verified merely to make the changed implementation pass.

## Consequences

Regression evidence remains close to the behavior that motivated a change.

Architectural rules can be enforced mechanically where suitable instead of
depending only on documentation review.

Reference, sequential, parallel and accelerated implementations can evolve
without silently diverging.

The test suite grows with the supported behavior and therefore adds
maintenance cost.

Performance measurements remain separate from correctness tests, reducing
platform-dependent test instability.