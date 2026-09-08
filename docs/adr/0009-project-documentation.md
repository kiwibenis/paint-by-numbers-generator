# ADR-0009 - Project Documentation

## Status

Accepted

## Context

The project contains different kinds of documentation serving different
purposes.

Mixing project vision, architecture decisions, implementation planning and
source code history in the same document makes the project difficult to
maintain.

Each document should have a single, well-defined responsibility.

## Decision

Project documentation is separated by responsibility.

The project shall contain:

- `README.md` describing the project and how to use it.
- `VISION.md` describing the long-term vision and project goals.
- `ROADMAP.md` tracking planned implementation work.
- `docs/adr/` documenting accepted architecture decisions.

Source code changes and implementation details are documented through the Git
history.

The roadmap shall remain aligned with the accepted ADRs.

## Consequences

Each document has a single responsibility.

Architecture decisions remain independent from implementation planning.

The project vision remains stable while the roadmap evolves over time.

Project documentation stays structured, maintainable and easy to navigate.