# ADR-0010 - Commit Convention

## Status

Accepted

## Context

The Git history is part of the project documentation.

Clear and consistent commit messages improve readability, simplify code
reviews and make architectural evolution easier to understand.

Each commit should represent one logical change.

## Decision

Every commit shall use the following format:

```
<type>: <short description>
```

The following commit types are used throughout the project:

- `docs` – Documentation changes only.
- `feat` – New functionality.
- `fix` – Bug fixes.
- `refactor` – Internal code improvements without changing behaviour.
- `test` – Add or improve tests.
- `perf` – Performance improvements.
- `build` – Build system or dependency changes.
- `ci` – Continuous integration changes.
- `style` – Formatting or style changes without behavioural impact.
- `chore` – Maintenance tasks that do not fit another category.

Each commit shall represent one logical change.

Documentation, refactoring and feature development should be committed
separately whenever practical.

When suggesting commit messages, only one commit message shall be proposed.

The commit message shall always use the most descriptive wording applicable.

## Consequences

The Git history remains consistent and easy to navigate.

Commit messages clearly communicate the purpose of each change.

Architecture, implementation and documentation changes remain clearly
separated.