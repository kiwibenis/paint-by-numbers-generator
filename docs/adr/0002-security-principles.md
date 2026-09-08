# ADR-0002 - Security Principles

## Status

Accepted

## Context

The project processes external files, configuration and request-controlled
values.

Image decoders and other runtime dependencies may encounter malformed input,
resource-exhaustion attempts or values intended to escape an expected path or
data boundary.

Security rules therefore need to apply throughout the project rather than only
at a particular user interface.

More specific architectural decisions define the concrete untrusted-input,
error-disclosure and dependency boundaries.

## Decision

The project shall follow a secure-by-default approach.

Project-controlled code shall not use `eval()` or `exec()` to interpret
external or configuration-derived values.

Subprocess execution shall not use `shell=True`.

External input shall be validated before it reaches business logic.

Invalid configuration shall be rejected rather than silently repaired into a
different value.

Project-owned file handling shall use explicit path objects and shall validate
request-controlled identifiers before using them to construct paths.

A request-controlled identifier used in project-owned path construction shall
not be able to escape its intended location.

Paths supplied directly by an integrating application remain the
responsibility of that integrator. Input validation shall not be represented as
making an attacker-selected pathname safe.

Third-party runtime libraries shall remain behind the dependency boundaries
defined by ADR-0003.

Third-party objects shall not become Core business models.

Exceptions raised by external libraries shall not escape normal project
boundaries merely because the project does not recognize their concrete type.
Where a boundary translates external failures, it shall translate them into
the project's exception hierarchy while preserving diagnostic cause
information where appropriate.

Broad exception handling is permitted only at a boundary whose responsibility
is to translate or contain arbitrary external implementation failures. It
shall not be used to hide programming errors or continue with partial results.

Caller-safe and operator-facing error information shall follow ADR-0019.

Untrusted image processing shall follow the mandatory boundary and deployment
responsibilities defined by ADR-0016.

Security controls shall fail closed. A missing required dependency, invalid
input, invalid configuration or failed validation shall not silently select a
less constrained execution path.

## Consequences

Security requirements apply independently of whether generation is reached
through the command line, the Python API or another integrating application.

The Core remains separated from file parsers and other external implementation
types.

Boundary code carries additional validation and error-translation
responsibility.

Integrating applications retain responsibility for deployment concerns that
the generator cannot enforce portably, including the safety of paths they
choose and external process resource limits.

Fail-closed behavior may reject work that could technically continue through a
different implementation path, but avoids silently weakening an accepted
security or architectural boundary.