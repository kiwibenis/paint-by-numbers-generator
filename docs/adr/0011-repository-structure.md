# ADR-0011 - Repository Structure

## Status

Accepted

## Context

The repository contains production source code, tests, documentation,
configuration, reference data, examples, automation and developer tooling.

A responsibility-based repository structure improves navigation and prevents
unrelated project concerns from accumulating in arbitrary locations.

The repository also contains root-level project metadata and tool
configuration. The architectural rule is therefore not that every repository
concern must be a directory, but that each persistent location has a clear
responsibility.

## Decision

The repository shall be organized by responsibility.

The primary repository locations are:

- `src/` for production application source code;
- `tests/` for automated tests, test support code and fixtures;
- `docs/` for project documentation;
- `docs/adr/` for Architecture Decision Records;
- `config/` for shipped configuration profiles and examples;
- `examples/` for user-facing example input and generated example artifacts;
- `palettes/` for versioned reference palette data;
- `tools/` for developer-only diagnostics, benchmarks, measurements and other
  maintenance utilities;
- `.github/` for GitHub-specific repository automation and workflow metadata;
- `.vscode/` for repository-shared Visual Studio Code configuration where such
  configuration is useful to contributors.

Project-wide metadata and configuration may remain at the repository root when
a dedicated directory would not improve its responsibility boundary. This
includes files such as:

- `pyproject.toml`;
- `README.md`;
- `VISION.md`;
- `ROADMAP.md`;
- `LICENSE`;
- `ADDITIONAL-TERMS.md`;
- Git repository configuration files.

The list above describes the current responsibility boundaries. It is not an
exhaustive prohibition against adding another repository location.

A new top-level directory shall only be introduced when it represents a
persistent responsibility that does not fit clearly into an existing
location.

Developer-only tooling shall remain outside `src/` so that measurement,
diagnostic and maintenance code does not become part of the shipped
application merely because it is useful during development.

Production source shall not import from `tools/`.

Documentation that describes project architecture or behavior shall remain
separate from temporary generated measurements and local development
artifacts.

Local build output, temporary files, profiling output and other
machine-specific artifacts shall not become part of the repository structure
unless they are intentionally retained as project evidence or fixtures.

## Consequences

Production code, tests, documentation, reference data and developer tooling
have distinct repository locations.

Developer tools can evolve independently without enlarging the runtime package.

Repository automation and editor configuration have explicit homes rather than
being forced into application directories.

Root-level project metadata remains easy to discover.

The structure can grow without requiring this ADR to enumerate every future
file, while new persistent top-level responsibilities still require deliberate
placement.

Contributors can infer the intended location of new files from their
responsibility rather than from an exhaustive static directory list.