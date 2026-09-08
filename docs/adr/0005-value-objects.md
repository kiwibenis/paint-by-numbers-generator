# ADR-0005 - Immutable Value Objects

## Status

Accepted

## Context

The application passes domain values between many processing stages.

Mutable shared state would make generation behavior harder to reason about and
would increase the risk that one processing stage changes data observed by
another stage.

Several domain values are also used in sets, dictionaries, caches and
deterministic comparisons, where stable value semantics are important.

## Decision

Domain value objects shall be immutable.

State-bearing domain value objects implemented as dataclasses shall use:

```text
@dataclass(frozen=True, slots=True)
```

They shall not expose setters.

They shall not contain mutable default values.

A changed domain value shall be represented by creating a new value rather than
mutating an existing instance.

Collections stored inside immutable domain values shall themselves use
immutable representations when they form part of the value's state.

Compact scalar storage such as `bytes`, tuples and `frozenset` is compatible
with this decision and may be used when another ADR defines that
representation.

Typical immutable domain values include:

- `RGB`;
- `Lab`;
- `PaletteColor`;
- `Region`;
- `Outline`;
- `InputImage`;
- `QuantizedImage`;
- `VectorDocument`.

Immutability describes observable domain state. It does not require every
service, builder, cache or local implementation detail to be a value object.

Introducing mutable state into an existing domain value requires an
architectural decision when callers could observe or depend on that mutation.

## Consequences

Domain state is predictable after construction.

Values can safely cross processing stages without defensive copying solely to
protect against mutation.

Suitable value objects remain hashable and can be used in sets, dictionaries
and caches.

Changes to domain state require explicit replacement, which can allocate more
objects than in-place mutation.

Compact representations defined by ADR-0017 and ADR-0018 remain compatible
with domain immutability.