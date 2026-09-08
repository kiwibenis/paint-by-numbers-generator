# Developer Guide

## Purpose

This guide defines the development workflow for the Paint by Numbers Generator.

It describes how contributors should:

- set up a local development environment;
- determine the authoritative source for a change;
- review architectural constraints before implementation;
- choose where new code and documentation belong;
- implement and test changes;
- use developer tooling under `tools/`;
- validate the repository;
- maintain Architecture Decision Records;
- update project documentation;
- create commits.

This guide describes development practice.

It does not replace accepted Architecture Decision Records. Accepted ADRs remain
the binding architectural source of truth.

## Source-of-Truth Hierarchy

Before changing architecture, structure or implementation, consult project
information in this order:

1. accepted ADRs under `docs/adr/`;
2. [`VISION.md`](../VISION.md);
3. [`ROADMAP.md`](../ROADMAP.md);
4. [`README.md`](../README.md);
5. current source code.

Higher-priority sources override lower-priority sources.

For example:

```text
accepted ADR
    overrides
ROADMAP.md
    overrides
current implementation
```

Source code describes the implementation that currently exists.

It does not override an accepted architectural decision merely because the
implementation has not yet been brought into alignment with that decision.

Focused documentation under `docs/` records current behavior, measurements,
algorithms and operating knowledge. It must remain consistent with the
authoritative hierarchy above.

## Architectural Baseline

The accepted architectural baseline consists of the accepted ADRs under:

```text
docs/adr/
```

ADR lifecycle and maintenance rules are documented in:

```text
docs/adr/INDEX.md
```

Before an architectural, structural or implementation change:

1. identify the affected responsibility;
2. review the relevant accepted ADRs;
3. review the corresponding planned work in `ROADMAP.md`;
4. inspect the current implementation;
5. choose the smallest logical change that satisfies the higher-priority
   sources.

Do not implement a solution that conflicts with an accepted ADR.

When the desired change requires violating or replacing an accepted
architectural rule, resolve the architectural decision first.

The implementation must not silently redefine the architecture.

For a high-level description of the current system boundaries, see:

- [`architecture-overview.md`](architecture-overview.md).

## Repository Structure

The current repository is organized by responsibility according to
[ADR-0011](adr/0011-repository-structure.md).

The primary locations are:

```text
src/          production application source
tests/        automated tests, fixtures and test support
docs/         project documentation
docs/adr/     Architecture Decision Records
config/       shipped configuration profiles
examples/     user-facing example inputs and generated artifacts
palettes/     versioned reference palette data
tools/        developer-only diagnostics, benchmarks and measurements
.github/      repository automation
```

Project-wide metadata and configuration may remain at repository root.

Examples include:

```text
pyproject.toml
README.md
VISION.md
ROADMAP.md
SECURITY.md
LICENSE
ADDITIONAL-TERMS.md
```

`ADDITIONAL-TERMS.md` holds the attribution term that applies under section 7
of the license. Every `.py` file under `src/`, `tests/` and `tools/` opens
with a three-line header naming the license and pointing at that file, which
is what section 7 requires of an additional term. A new module inherits the
header from the file beside it, and `tests/test_license_headers.py` holds
every file to it, so one written without the header fails the build rather
than shipping without the notice.

Before proposing a new repository path, inspect the current repository tree.

Use existing responsibility boundaries whenever possible.

Do not invent a parallel directory for work that already has an established
home.

A new top-level directory should represent a persistent responsibility that
does not fit an existing location.

## Production and Developer Tooling

Production code lives under:

```text
src/
```

Developer-only tooling lives under:

```text
tools/
```

Production source must not import from `tools/`.

A utility does not become production functionality merely because it is useful
during development.

If behavior is required by normal generation, place the behavior in the
appropriate production layer and expose it through normal project boundaries.

If code exists only to:

- benchmark;
- measure;
- inspect;
- diagnose;
- evaluate;
- calibrate;

it normally belongs under `tools/`.

## Local Development Setup

The project requires Python 3.12 or 3.13.

Clone the repository and enter the repository root:

```text
git clone https://github.com/kiwibenis/paint-by-numbers-generator.git
cd paint-by-numbers-generator
```

Create a virtual environment:

```text
python -m venv .venv
```

On Windows PowerShell:

```text
.\.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```text
source .venv/bin/activate
```

Upgrade pip and install the development environment:

```text
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The development dependency set currently includes:

- Black;
- Ruff;
- mypy;
- pytest;
- pytest-cov;
- pre-commit;
- type stubs required by the project;
- developer-only numerical dependencies used by tooling.

Reference palettes are currently loaded relative to the repository root.

Commands that use the shipped palettes should therefore be run from the
repository root.

A normal generation smoke test can be started with:

```text
pbn generate --config_file config/example.toml
```

This smoke test does not replace the required project validation.

## Python and Formatting Rules

Python code must remain:

- formatted according to the project's Black configuration;
- compatible with the project's Ruff configuration;
- compatible with strict mypy checking;
- consistent with PEP 8 where not superseded by the project's configured
  formatter or linting rules.

Current tool configuration is defined in:

```text
pyproject.toml
```

The current Black configuration uses:

```text
line length:
    88

target versions:
    Python 3.12
    Python 3.13

required Black major version:
    26
```

Black formatting can be checked locally with:

```text
python -m black --check .
```

The current Ruff configuration uses:

```text
line length:
    88

minimum target version:
    Python 3.12
```

mypy is configured in strict mode.

Do not weaken formatting, linting or type-checking configuration merely to make
a change pass.

When a rule must genuinely change, treat that as an explicit project-wide
tooling decision.

## Project Language

Project-controlled content is written in English according to
[ADR-0013](adr/0013-project-language.md).

This applies to:

- source code;
- identifiers;
- comments;
- docstrings;
- tests;
- configuration keys;
- CLI text;
- error messages;
- documentation;
- ADRs;
- development tools;
- commit messages.

Authoritative external content may retain its original language when
translation would change or obscure its meaning.

Examples include official manufacturer names and official color names in
reference palette data.

## Development Workflow

Prefer one small, self-contained logical change at a time.

The normal workflow is:

```text
architectural context
        |
        v
relevant ADRs
        |
        v
ROADMAP.md
        |
        v
current implementation
        |
        v
smallest logical change
        |
        v
implementation
        |
        v
focused tests
        |
        v
refactor if needed
        |
        v
full validation
        |
        v
documentation / roadmap alignment
        |
        v
commit
```

### 1. Understand the Context

Identify:

- what behavior is changing;
- which layer owns it;
- which domain models or boundaries are affected;
- whether the change is user-facing, architectural, internal or
  developer-only.

Do not begin from an assumed file path.

Inspect the current repository structure and implementation first.

### 2. Review Relevant ADRs

Read the ADRs governing the affected responsibility.

Common starting points include:

- ADR-0001 for layer responsibilities;
- ADR-0003 for dependency boundaries;
- ADR-0004 for testing;
- ADR-0005 and ADR-0008 for domain models;
- ADR-0011 for repository placement;
- ADR-0014 for CPU parallel execution;
- ADR-0015 for geometry acceleration;
- ADR-0016 for untrusted image input;
- ADR-0017 and ADR-0018 for compact representations;
- ADR-0019 for error disclosure;
- ADR-0026 for CLI integration behavior;
- ADR-0027 for the PDF-only output boundary.

Review the relevant accepted ADR files under `docs/adr/`.

Use `docs/adr/INDEX.md` for ADR lifecycle and maintenance rules.

Do not assume the examples above are exhaustive.

### 3. Review the Roadmap

Check whether the change is already planned.

`ROADMAP.md` tracks remaining planned work, not completed implementation
history.

A completed roadmap item should normally be removed once its durable result is
represented in the appropriate current-state documentation.

Do not accumulate completed implementation checklists in the roadmap.

### 4. Choose the Smallest Logical Change

Prefer changes that can be understood, tested and committed independently.

Do not combine unrelated work merely because the same files are nearby.

Examples of separate logical changes include:

```text
feature implementation

documentation describing the completed feature

unrelated refactoring

dependency maintenance
```

They should normally remain separate commits when practical.

### 5. Implement

Extend existing architecture rather than bypassing it.

Important general rules include:

- Core owns deterministic generation semantics;
- Application owns use-case orchestration and execution policy;
- Infrastructure owns concrete external integrations;
- CLI owns interface and composition concerns;
- external runtime-library types must not leak into Core contracts;
- developer tooling must not become a production dependency;
- domain values should follow the established immutable model conventions;
- deterministic ordering and tie-breaking must remain explicit.

Follow the existing local code conventions unless a higher-priority source
requires a change.

### 6. Add or Update Tests

Testing follows
[ADR-0004](adr/0004-test-strategy.md).

Changed behavior should be tested at the narrowest useful boundary.

Public functionality requires automated coverage.

A reproducible bug fix should include a regression test.

Prefer tests of observable behavior over tests that depend unnecessarily on
private implementation details.

Architectural invariants should be mechanically tested when practical.

Examples include:

- deterministic ordering;
- reference-versus-accelerated equivalence;
- sequential-versus-parallel equivalence;
- layer boundaries;
- configuration behavior;
- supported input boundaries;
- error-disclosure behavior;
- compact representation invariants.

Do not weaken an existing test solely to accommodate a changed implementation
when the underlying behavior is still required.

### 7. Refactor Only After Behavior Is Correct

Once the implementation and focused tests are correct, refactor when doing so
improves:

- clarity;
- dependency direction;
- naming;
- duplication;
- maintainability.

Do not mix speculative refactoring into a feature change when it is not needed
to implement that feature.

A behavior-preserving refactor should use the `refactor` commit type rather
than being presented as a feature.

## Required Project Validation

Before considering a logical implementation step complete, run exactly what
CI runs:

```text
ruff check src tests tools
python -m black --check .
mypy
pytest -q
```

These are the four commands from `.github/workflows/ci.yml`. Running a
narrower set locally does not make a change complete, it only moves the
failure to CI.

`mypy` takes no path argument on purpose. The trees it checks are named in
`pyproject.toml` under `files`, so the command covers `src`, `tests` and
`tools` the same way locally and in CI.

`python -m ruff check . --fix` and `python -m black .` apply the automatic
corrections when a check fails.

The change is not complete while relevant validation is failing.

The repository CI performs its own checks across the configured supported
environments. Local validation does not justify ignoring a CI failure.

## Continuous Integration

The current GitHub Actions workflow is:

```text
.github/workflows/ci.yml
```

CI currently exercises the project on:

```text
Python 3.12
Python 3.13
```

The main check job covers:

- Ruff linting;
- Black formatting;
- strict static type checking;
- automated tests.

Black runs in check mode and fails CI when committed Python source is not
formatted according to the project configuration.

A separate audit job checks production dependencies for known
vulnerabilities.

The dependency audit also runs on a schedule because a vulnerability advisory
can appear without a repository change.

A CI failure should be investigated as a project failure rather than dismissed
merely because local generation appears to work.

## Tests, Benchmarks, Measurements and Evaluations

These categories serve different purposes.

They must not be treated as interchangeable evidence.

### Automated Tests

Location:

```text
tests/
```

Purpose:

```text
Does the project satisfy a required behavior or invariant?
```

Tests should be deterministic and suitable for repeatable automated
validation.

Ordinary tests must not depend on unstable wall-clock timing thresholds.

### Benchmarks

Typical location and naming:

```text
tools/benchmark_*.py
```

Purpose:

```text
How fast is a behavior or implementation under a defined workload?
```

Examples include complete generation, quantization and region-processing
benchmarks.

Benchmarks support performance decisions.

They do not replace correctness tests.

A benchmark showing that an implementation is faster does not prove that its
output is equivalent.

Performance-sensitive implementation changes therefore normally require both:

```text
correctness evidence
+
performance evidence
```

### Measurements

Typical location and naming:

```text
tools/measure_*.py
```

Purpose:

```text
What resource, representation or system characteristic does the current
implementation exhibit?
```

Examples include:

- memory consumption;
- image-input cost;
- worker serialization;
- adversarial resource behavior.

Measurements provide evidence for limits, configuration and architectural
decisions.

They are not runtime enforcement merely because a measurement exists.

### Evaluations

Typical location and naming:

```text
tools/evaluate_*.py
```

Purpose:

```text
How does a quality policy, heuristic or algorithm behave on representative
data?
```

Evaluation tools may inspect:

- visual-quality proxies;
- region preservation;
- merge behavior;
- quantization collisions;
- calibration thresholds.

An evaluation result may justify a production policy, but the evaluation
algorithm itself does not automatically belong in production.

### Tool Tests

A developer tool may have corresponding automated tests under `tests/`.

Those tests verify that the tool itself computes or reports its measurement
correctly.

They do not turn the measured performance or quality result into a normal unit
test threshold.

## Performance Work

Performance optimization should begin with current evidence.

Use:

1. complete end-to-end measurements to establish whether there is a real
   problem;
2. focused profiling or benchmarks to locate the cost;
3. the smallest optimization that addresses that cost;
4. correctness tests to prove semantic equivalence;
5. end-to-end measurement again to verify that the whole generator improved.

Do not retain an optimization merely because an isolated helper became faster.

Downstream effects may outweigh an isolated speedup.

Current performance methodology and retained measurements are documented in:

- [`performance-measurements.md`](performance-measurements.md).

## Diagnostic and Measurement Artifacts

Local profiles, temporary generated data and exploratory output should remain
local unless the project deliberately retains them as:

- regression fixtures;
- reproducible reference evidence;
- current measurement documentation.

Do not add temporary profiling output to the repository merely because it was
useful during investigation.

Durable conclusions belong in the appropriate documentation.

Git history records the development sequence.

## Documentation Responsibilities

Documentation is separated by responsibility according to
[ADR-0009](adr/0009-project-documentation.md).

Use:

```text
README.md
```

for project purpose, installation and user-facing usage.

Use:

```text
VISION.md
```

for long-term goals.

Use:

```text
ROADMAP.md
```

for remaining planned work.

Use:

```text
docs/adr/
```

for binding architectural decisions.

Use focused documents under:

```text
docs/
```

for current technical explanations, algorithms, measurements, calibration,
integration guidance and developer guidance.

Do not use the roadmap as an implementation history.

Do not preserve superseded intermediate measurements merely to narrate how the
current result was reached.

When decision rationale remains important to understanding the current system,
retain the relevant rationale without reconstructing unnecessary chronology.

## ADR Lifecycle

The ADR lifecycle is defined in:

```text
docs/adr/INDEX.md
```

### ADR Status

An ADR may be:

```text
Draft
```

while a decision is still being prepared.

Only:

```text
Accepted
```

ADRs belong to the binding architectural baseline.

Do not implement an architectural change as though a Draft ADR were already an
accepted project rule unless the implementation itself is explicitly part of
evaluating that draft.

### When to Create an ADR

Create a new ADR when the project makes a genuinely new and independent
architectural decision.

Examples include decisions about:

- architectural layers;
- external dependency boundaries;
- supported execution models;
- persistent domain representations;
- public integration contracts;
- generated artifact types.

Do not create an ADR for an ordinary local implementation detail.

### Updating Existing ADRs During Pre-1.0 Development

The project is currently pre-1.0.

During this phase, the ADR set is maintained as a consolidated description of
the current architecture.

An accepted ADR may therefore be revised when later work:

- refines;
- corrects;
- completes;

the same architectural responsibility.

When several ADRs would otherwise describe successive versions of the same
decision, consolidate the final rule into the ADR that naturally owns that
responsibility.

Git history retains the prior wording.

### Removing Redundant ADRs

A redundant ADR may be removed only when all still-binding architectural rules
have been preserved elsewhere.

Before removing it:

1. identify repository references to that ADR;
2. update those references to the surviving source of truth;
3. verify that no intended architectural rule disappears.

Do not use ADR cleanup to hide an actual change in intended system behavior.

### ADR Numbering

Deleted ADR numbers are not reused.

Surviving ADRs are not renumbered.

Gaps in the ADR sequence are valid.

A new independent ADR receives a new unused number.

### ADR Structure

Use:

```text
# ADR-000X - Title

## Status

Draft

## Context

...

## Decision

...

## Consequences

...
```

When accepted, change its status to:

```text
Accepted
```

Keep ADRs concise and focused on current architectural rules.

Measurements and time-sensitive evidence should normally live in dedicated
documentation rather than being embedded permanently into an ADR.

## Documentation After Implementation

After completing a logical change, determine whether documentation must change.

Typical questions are:

```text
Did user-facing behavior change?
    -> README.md may need updating.

Did planned work become complete or change?
    -> ROADMAP.md may need updating.

Did architecture change?
    -> an ADR must already reflect the decision.

Did current technical behavior or measured evidence change?
    -> the corresponding docs/ document may need updating.

Did palette reference data change?
    -> docs/reference-data/ and the palette authoring rules apply.
```

Do not update unrelated documentation solely to make a commit appear larger or
more complete.

## Commit Convention

Commits follow
[ADR-0010](adr/0010-commit-convention.md).

Every commit uses:

```text
<type>: <short description>
```

Valid types are:

```text
docs
feat
fix
refactor
test
perf
build
ci
style
chore
```

Examples:

```text
feat: add deterministic gpu quantization policy
fix: preserve palette tie ordering
docs: add developer guide
perf: reduce overlap candidate allocations
```

Each commit represents one logical change.

Separate documentation, refactoring and feature work when practical.

Choose the most descriptive applicable type.

Commit messages are written in English.

## Commit Workflow

Once one logical change is complete and validated:

```text
git add .
git commit -m "<type>: <short description>"
git push
```

Do not combine unrelated unfinished work into the same commit.

Do not use a vague commit description when the logical change can be named
precisely.

## Dependency Changes

Runtime dependencies affect architecture, security and compatibility.

Before introducing a new runtime dependency:

- verify that it belongs within the existing dependency boundaries;
- review ADR-0003;
- review ADR-0021;
- confirm that an existing dependency or standard-library implementation does
  not already satisfy the requirement;
- add focused tests around the project-owned contract;
- evaluate security and compatibility implications.

External runtime libraries belong in Infrastructure.

Do not introduce a third-party runtime dependency directly into Core merely
because it simplifies an implementation.

Current dependency-security evidence is documented in:

- [`dependency-security.md`](dependency-security.md).

## Security-Sensitive Changes

For changes involving:

- untrusted files;
- paths;
- parsers;
- external libraries;
- error disclosure;
- process execution;
- resource bounds;

review the relevant security ADRs before implementation.

The current security model and its mechanical validation are documented in:

- [`security-validation.md`](security-validation.md).

Do not weaken fail-closed behavior or public-error boundaries as an incidental
implementation shortcut.

## Reference Palettes

Changes to reference palettes follow:

- ADR-0006;
- ADR-0007;
- [`palette-format.md`](palette-format.md);
- [`palette-authoring-guide.md`](palette-authoring-guide.md).

Palette data is versioned reference data rather than ordinary editable
configuration.

Do not modify a released palette version in place.

## Before Finishing a Change

A logical change is ready to commit when:

- the implementation matches the relevant accepted ADRs;
- the change is consistent with `VISION.md` and `ROADMAP.md`;
- new files are in the correct repository responsibility;
- affected behavior has focused automated tests;
- deterministic behavior is preserved where required;
- relevant validation passes;
- refactoring required for maintainability is complete;
- user-facing documentation is updated when necessary;
- current technical documentation is updated when necessary;
- `ROADMAP.md` is updated when planned work changed;
- the commit represents one logical change;
- the commit message follows ADR-0010.

## Related Documentation

For current architecture:

- [`architecture-overview.md`](architecture-overview.md).

For ADR lifecycle and maintenance rules:

- [`adr/INDEX.md`](adr/INDEX.md).

For testing:

- [ADR-0004](adr/0004-test-strategy.md).

For repository structure:

- [ADR-0011](adr/0011-repository-structure.md).

For documentation responsibilities:

- [ADR-0009](adr/0009-project-documentation.md).

For commit conventions:

- [ADR-0010](adr/0010-commit-convention.md).

For project language:

- [ADR-0013](adr/0013-project-language.md).

For user-facing setup and usage:

- [`../README.md`](../README.md).

For remaining planned work:

- [`../ROADMAP.md`](../ROADMAP.md).