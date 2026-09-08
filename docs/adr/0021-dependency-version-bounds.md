# ADR-0021 - Dependency Version Bounds

## Status

Accepted

## Context

Runtime dependencies need version constraints that balance compatibility with
the ability to receive security fixes.

An upper major-version bound prevents an unreviewed major release from entering
an installation. The same bound becomes harmful when a security fix exists
only in a later major release and the project does not revisit the constraint.

A dependency constraint is therefore not permanently conservative merely
because it once described a known-good range. Security advisories and upstream
release lines change independently of this repository.

This matters particularly for dependencies that parse untrusted input or
otherwise form part of the runtime attack surface defined by ADR-0016.

Detailed dependency versions, vulnerability findings and compatibility
measurements are time-sensitive evidence and are recorded separately in
`docs/dependency-security.md`.

## Decision

Runtime dependencies may use upper major-version bounds.

An upper bound shall be treated as a constraint that requires continuing
review rather than as a permanent compatibility guarantee.

A dependency vulnerability scan shall run in continuous integration against
the declared dependency set and shall fail the build when a known
vulnerability is reported.

A vulnerability finding shall not be suppressed merely because the fixed
version lies above a declared upper bound.

When a fix requires a version outside the currently declared range, the
project shall update the range and validate the required version.

If the required version cannot be adopted, that incompatibility is a project
defect to be resolved. The reason preventing adoption shall be documented
rather than hiding the vulnerability finding.

Raising an upper bound across a major release requires evidence that the
project still behaves correctly with the new release.

That evidence shall include:

- the full automated test suite against the new version;
- verification of dependency behavior on which the project relies beyond its
  public high-level API.

For the imaging library, this includes the decoder-registry restriction and
format-detection behavior required by ADR-0016.

For other dependencies, equivalent dependency-specific assumptions shall be
verified where they exist.

When a Python dependency bundles a native library or other independently
versioned runtime component, the bundled version shall be recorded separately
from the wrapper version when that component affects the project's security or
compatibility assumptions.

A wrapper-package upgrade shall not be assumed to upgrade a bundled native
component.

Measured dependency state shall be recorded in dated supporting documentation.

The supporting record shall include enough information to reproduce the
relevant checks, because installed versions, advisories and available upstream
fixes change over time.

Changing the policy to permit ignored vulnerability findings, removing
required compatibility verification for major-version changes or abandoning
dependency vulnerability scanning requires an architectural decision.

## Consequences

The project can retain explicit compatibility bounds without allowing those
bounds to silently prevent required security updates.

Dependency vulnerabilities can make continuous integration fail even when the
affected code path is not known to be reachable by this project. Resolving such
findings may therefore require investigation or an upstream-version update.

Major dependency upgrades require deliberate verification instead of being
accepted automatically.

Dependency-specific assumptions such as decoder-registry behavior become part
of upgrade verification and cannot be inferred solely from a passing import or
package installation.

Bundled native components remain a separate security concern from their Python
wrapper packages. Recording their versions makes that distinction visible but
does not by itself make them independently updateable.

Dated dependency-security documentation will become stale and therefore needs
periodic refresh. That staleness is explicit rather than being hidden inside
the architectural decision.