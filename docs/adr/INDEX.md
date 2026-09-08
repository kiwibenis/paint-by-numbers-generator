# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the
Paint by Numbers Generator.

ADRs describe the architectural baseline that currently governs the project.
The Git history records how that baseline evolved.

## Format

Every ADR follows the same structure:

```text
# ADR-000X - Title

## Status

Accepted

## Context

Describe the architectural problem or motivation.

## Decision

Describe the chosen solution.

## Consequences

Describe the expected impact of the decision.
```

An ADR may use `Draft` as its status while a decision is still being prepared.

Only accepted ADRs are part of the binding architectural baseline.

## Pre-1.0 Lifecycle

The project is currently under active pre-1.0 development.

During this phase, the ADR set is maintained as a consolidated description of
the current architecture rather than as an immutable chronological record of
every intermediate decision.

An accepted ADR may therefore be revised when later work refines, corrects or
completes the same architectural decision.

When several ADRs form a chain in which later records only refine, correct,
replace or reverse parts of an earlier decision, the final decision should be
consolidated into the ADR that most naturally owns that architectural
responsibility.

After consolidation, a redundant ADR may be removed when all architectural
rules that remain binding have been preserved in the surviving ADRs.

The Git history remains the authoritative record of the removed or rewritten
intermediate decisions.

Consolidation shall not be used to hide a genuine change in intended system
behaviour. If the desired architecture differs from the implemented
architecture, that is an architectural or implementation change and must be
handled explicitly rather than presented as documentation cleanup.

A genuinely new and independent architectural decision shall still receive a
new ADR instead of being inserted into an unrelated existing ADR.

Deleted ADR numbers shall not be reused, and surviving ADRs shall not be
renumbered. Gaps in the ADR sequence are therefore valid.

Before an ADR is removed or its responsibility is moved elsewhere, repository
references to that ADR shall be identified and updated to the surviving
architectural source of truth.

Before the first stable release, this lifecycle policy shall be reviewed and a
policy for post-release architectural evolution shall be defined explicitly.

## Guidelines

- Keep ADRs concise.
- Describe the current architectural decision rather than reconstructing its
  complete chronological history.
- Preserve enough context to explain why the current decision exists.
- Focus on architecture rather than transient implementation details.
- Keep measurements and other time-sensitive evidence in dedicated
  documentation when they do not form part of the architectural contract.
- Use clear, factual language.
- Reference another ADR only when the architectural dependency remains
  relevant in the current baseline.
- Keep the roadmap and other project documentation aligned with the accepted
  ADR set.

## Naming

Use the following filename convention:

```text
0001-layered-architecture.md
0002-security-principles.md
0003-dependency-boundaries.md
...
```

Do not prefix filenames with `ADR-`.

The document title shall always use:

```text
# ADR-000X - Title
```

where `000X` matches the filename.