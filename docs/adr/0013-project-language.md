# ADR-0013 - Project Language

## Status

Accepted

## Context

The project contains source code, documentation, tests, configuration,
command-line interfaces, examples and other development artifacts.

Using different languages across these project-controlled artifacts makes the
project less consistent and increases the effort required for maintenance,
review and collaboration.

The project therefore needs a single language convention for
project-controlled content.

External content, such as official manufacturer names or other externally
defined reference data, may require its original language and must not be
translated solely to satisfy this convention.

## Decision

English is the mandatory language for all project-controlled content.

This includes, but is not limited to:

- source code comments and docstrings;
- class, function, method and variable names;
- tests and test names;
- configuration keys and configuration interfaces;
- command-line messages and help text;
- error messages;
- project documentation;
- Architecture Decision Records;
- roadmap and vision documents;
- examples and example code;
- development and tooling artifacts;
- Git commit messages.

External or authoritative content shall remain in its original language when
translation would alter or obscure its meaning.

Examples include:

- official manufacturer names;
- official product or color names;
- externally defined identifiers;
- source data whose values are required for reproducibility.

This language convention applies to all new project-controlled content and to
existing project-controlled content when it is modified.

## Consequences

The project has a consistent language across its controlled artifacts.

Documentation, source code and development workflows are easier to review and
maintain.

New contributors have a clear language convention to follow.

External authoritative names and reference data can retain their original
form without violating the project language convention.

Existing project-controlled content may require translation when it is
modified or when the project performs a documentation consistency pass.