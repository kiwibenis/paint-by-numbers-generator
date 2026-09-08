# Security Validation

## Purpose

This document records the current security boundaries and validation practices
of Paint by Numbers Generator.

It describes:

- the security responsibilities implemented by the generator;
- the trust boundaries around configuration, image input, palettes,
  dependencies and generated output;
- mechanically enforced source-level invariants;
- the automated validation that protects those boundaries;
- the responsibilities intentionally left to integrating applications;
- conditions that require security revalidation.

It records the current project state.

Detailed architecture decisions remain binding in the accepted ADRs. Measured
runtime, memory and dependency-security state are maintained in dedicated
documents because those values change independently from the security model.

The primary binding decisions are:

- [ADR-0002 - Security Principles](adr/0002-security-principles.md);
- [ADR-0003 - Dependency Boundaries](adr/0003-dependency-boundaries.md);
- [ADR-0016 - Untrusted Input Boundary](adr/0016-untrusted-input-boundary.md);
- [ADR-0019 - Error Disclosure Boundary](adr/0019-error-disclosure-boundary.md);
- [ADR-0021 - Dependency Version Bounds](adr/0021-dependency-version-bounds.md);
- [ADR-0026 - Command-Line Integration Contract](adr/0026-command-line-integration-contract.md);
- [ADR-0027 - PDF Is the Only Output](adr/0027-pdf-is-the-only-output.md).

## Security Model

The generator follows a secure-by-default model.

External data is validated before it reaches Core business logic.

The normal trust flow is:

```text
external configuration / image / palette selection
                |
                v
interface and Infrastructure boundaries
                |
                | validate
                | normalize
                | translate failures
                v
project-owned Application and Core values
                |
                v
deterministic generation
                |
                v
Infrastructure PDF serialization
```

Security requirements apply regardless of whether generation is invoked
through:

- the command line;
- the Python API;
- a future graphical application;
- another integrating application.

An alternate interface must not obtain weaker validation by bypassing the
command-line layer.

## Responsibility Boundary

The project protects the generator boundary.

It does not attempt to implement complete deployment isolation.

### Provided by the Generator

The project currently provides:

- configuration parsing and validation;
- mandatory image loading and normalization;
- declared image-dimension limits;
- a processing-resolution limit;
- a restricted image-decoder surface;
- content-based image-format verification;
- rejection of unsupported or mismatched formats;
- path confinement for project-constructed palette paths;
- project-owned error translation;
- caller-safe error disclosure;
- dependency vulnerability scanning in continuous integration;
- fail-closed handling for required runtime dependencies;
- a single controlled production file-write location;
- mechanically checked source-level security invariants.

### Required from an Integrating Application

The project intentionally does not provide:

- per-generation wall-clock enforcement;
- per-generation address-space enforcement;
- process isolation;
- container or sandbox management;
- request authentication or authorization;
- concurrency limits;
- request rate limiting;
- queue management;
- upload lifecycle management;
- generated-document serving;
- generated-document expiration or cleanup;
- deployment-level path safety for arbitrary paths chosen by an integrator.

These responsibilities belong to the caller or deployment environment.

The process integration boundary and deployment expectations are documented in:

- [`integration-contract.md`](integration-contract.md).

## Configuration Safety

Project configuration is parsed with the Python standard-library `tomllib`
parser.

Production source does not use executable configuration formats.

Configuration-derived values are validated before generation.

Invalid configuration is rejected rather than silently converted into a
different valid value.

The configuration flow therefore distinguishes:

```text
parse
    |
    v
structural normalization
    |
    v
semantic validation
    |
    v
GeneratorConfig
```

Only validated project-owned configuration values are passed into normal
generation.

Configuration parsing must not execute code supplied through a configuration
file.

## Source-Level Security Invariants

Several security properties are mechanically checked against the complete
production source tree.

The current checks are implemented in:

```text
tests/test_preserved_invariants.py
```

These checks make accidental weakening of important source properties visible
during normal test execution.

### Dynamic Code Execution

Production source must not invoke:

```text
eval
exec
compile
__import__
```

for runtime behavior.

The project therefore does not interpret external or configuration-derived
values as Python code.

### Command Execution

Production source does not import `subprocess`.

The source-level validation also rejects shell-related and direct process
execution calls such as:

```text
system
popen
execv
execve
fork
forkpty
spawnl
spawnv
```

No production call may contain a `shell` keyword argument.

This mechanically protects the ADR-0002 rule that project-controlled process
execution must not use a shell.

### Unsafe Deserialization

Production source does not import the checked general-purpose serialization
modules:

```text
pickle
marshal
shelve
dbm
```

External configuration is parsed through `tomllib`.

### Network Access

The current production generator does not require network access.

The source-level invariant rejects imports of the checked networking modules
and libraries, including:

```text
socket
ssl
urllib
http
requests
httpx
ftplib
smtplib
poplib
imaplib
telnetlib
xmlrpc
```

The generator therefore does not acquire external runtime input over a network.

Network-facing concerns belong to an integrating application.

### XML Parsing

Production source contains no XML parser.

Parser modules under:

```text
xml.etree
xml.dom
xml.sax
xml.parsers
```

are mechanically rejected.

The generator therefore does not expose an XML parsing surface as part of
normal generation.

### Native Library Loading

Production source does not directly import `ctypes`.

Required native or compiled functionality is reached only through declared
runtime dependencies behind the project's Infrastructure boundaries.

### Developer Tool Isolation

Developer tools under:

```text
tools/
```

are not production dependencies.

Production code under:

```text
src/
```

must not import them.

Developer measurement tools may therefore use capabilities that the shipped
generator deliberately avoids without making those capabilities reachable
from production code.

## Mandatory Image Boundary

Every normal generation path loads image data through the mandatory image
loading boundary defined by ADR-0016.

The Application depends on the project-owned image-loading port rather than on
Pillow directly.

The concrete decoder remains in Infrastructure.

The value crossing into generation is:

```text
InputImage
```

rather than a Pillow image or another decoder-owned object.

The Core therefore does not receive:

- input paths;
- file handles;
- Pillow image instances;
- decoder metadata;
- auxiliary image frames.

This makes validation part of the generation contract rather than an optional
interface concern.

## Supported Image Formats

The accepted image formats are exactly:

```text
BMP
JPEG
PNG
WEBP
```

The project does not support:

```text
TIFF
RAW
DNG
MPO as an independent format
```

Reintroducing RAW or TIFF requires an architectural decision.

An unsupported filename extension is rejected before normal decoding begins.

The extension expresses the format claimed by the caller.

It does not select the decoder.

The imaging library detects the actual format from file content, after which
the detected format is compared with the claimed supported format.

A mismatch is rejected except for the narrowly defined JPEG auxiliary-frame
case.

## Decoder Surface

The image decoder registry is restricted to the formats required by the
project.

Unsupported imaging-library decoders are removed from the reachable registry
where the library permits it.

This is stronger than an extension allowlist.

An attacker cannot make an unsupported parser reachable merely by renaming a
file to use a supported extension.

The decoder restriction is part of the project's dependency assumptions and
must be revalidated when the imaging library changes materially.

Current dependency-specific evidence is maintained in:

- [`dependency-security.md`](dependency-security.md).

## Image Dimension Limits

Every image load requires explicit limits for:

```text
maximum width
maximum height
maximum pixel count
processing pixel count
```

Declared image dimensions are checked before unbounded normalized pixel
materialization.

An image exceeding a hard input bound is rejected.

An accepted image above the configured processing resolution is reduced before
the normalized pixel representation used by generation is materialized.

The processing target is configuration, not a hidden program constant.

This distinction is intentional:

```text
hard input bounds
    -> reject input

processing pixel count
    -> normalize accepted input to bounded generation resolution
```

The current trusted and untrusted configuration profiles use the same
validation controls.

They may use different values.

A profile must not disable a security control.

The current profiles are:

```text
config/example.toml
config/untrusted.toml
```

The configuration files are the authoritative source for their current numeric
values.

## Decompression Bomb Protection

The image-loading boundary integrates the imaging library's decompression-bomb
protection with the project's configured pixel limits.

A decompression-bomb condition is treated as a failure rather than a warning
that allows generation to continue.

Dimension limits are checked before normalized pixel data is fully
materialized.

The security boundary therefore does not rely on compressed upload size as a
proxy for decoded cost.

Measured evidence showing why upload size is insufficient is maintained in:

- [`input-bound-measurements.md`](input-bound-measurements.md);
- [`adversarial-input-measurements.md`](adversarial-input-measurements.md).

## JPEG Auxiliary Frames

Some JPEG photographs contain MPF metadata and auxiliary frames.

The imaging library may report such a photograph as `MPO`.

The project permits one narrow detected-format mismatch so that supported
ordinary JPEG photographs remain usable.

The exception applies only when:

1. the filename claims `.jpg` or `.jpeg`;
2. the imaging library reports `MPO`;
3. the exposed MPF metadata contains a first image entry;
4. the first image declares JPEG image data;
5. the first image is declared as the baseline primary image.

Only frame zero contributes to the normalized `InputImage`.

The loader does not seek to or iterate over the auxiliary frames.

The exception does not make `.mpo` a supported input format.

Malformed or unrecognized metadata that fails the required conditions is
rejected.

The project deliberately relies on the metadata exposed by the imaging library
and does not maintain a second raw MPF parser.

## Palette Path Confinement

Reference palettes are project-owned data stored under:

```text
palettes/
```

A caller selects a palette using a palette identifier and version.

The identifier is validated before it is used to construct a project-owned
path.

The identifier must not be able to escape the palette directory through:

- an absolute path;
- path traversal;
- unsupported path characters;
- another path-construction trick.

The resulting project-owned palette path remains confined to its intended
directory.

The catalogue applies the same confinement to the entries it discovers. Its
paths come from reading the directory rather than from an identifier, so the
rule above did not reach them: a symlink inside `palettes/` pointing outside
was listed as a selectable palette and then refused by the selection, which
resolves the path. Both now resolve, so what the catalogue offers is confined
in the same sense as what the selection accepts.

An entry the file system cannot resolve counts as outside. `Path.resolve`
answers a symlink loop with `RuntimeError` rather than `OSError`, and that
escaped the project's error hierarchy entirely, reaching a caller as a
traceback rather than an exit code.

This guarantee applies specifically to paths constructed by the project from
request-controlled identifiers, and to entries the catalogue reads from the
palette directory.

It does not claim that an arbitrary path supplied directly by an integrating
application is safe.

The division is described in:

- [`integration-contract.md`](integration-contract.md).

## Palette Document Validation

Palette files are external reference documents crossing through
Infrastructure.

They are validated before becoming project-owned palette domain values.

Validation covers the palette structure and the constraints required by the
generator.

Malformed palette data is rejected rather than partially accepted.

Palette display text is also restricted to characters that can be represented
by the PDF legend fonts.

Unsupported text is rejected during palette loading instead of being silently
rendered as replacement symbols.

The palette format is documented in:

- [`palette-format.md`](palette-format.md).

Concrete palette provenance is maintained under:

- [`reference-data/`](reference-data/).

## Error Containment

Malformed external input must not expose arbitrary third-party exceptions
through the normal project boundary.

Infrastructure components translate external implementation failures into the
project's exception hierarchy where that boundary owns the external
integration.

Broad exception handling is permitted only at a translation or containment
boundary.

It must not silently swallow failures or continue with partial results.

The production source is mechanically checked so that broad exception handlers
contain a `raise`.

This does not prove that every possible error is classified correctly, but it
prevents the specific failure mode of silently consuming an arbitrary
exception.

## Error Disclosure

Project errors separate information for two audiences.

Every project error provides:

```text
diagnostic_message
public_message
caused_by_request
```

### Diagnostic Message

The diagnostic message is for operators.

It may contain:

- paths;
- supplied values;
- internal processing details.

It must be treated as sensitive operator information.

### Public Message

The public message is safe for an untrusted caller.

It must not expose request-independent deployment information such as:

- internal paths;
- stack traces;
- internal state.

A request-caused error may include enough request-derived information for the
caller to correct its input when that disclosure does not reveal independent
deployment state.

### Attribution

`caused_by_request` tells an interface whether the failure belongs to the
request or to the operation.

Interfaces must use that property rather than maintain their own duplicated
exception-type mapping.

The CLI integration contract exposes the public message and attribution in its
machine-readable result.

Operator diagnostics remain on the diagnostic channel.

The complete process contract is documented in:

- [`integration-contract.md`](integration-contract.md).

## Fail-Closed Behavior

Security-sensitive failures do not silently select a less constrained
execution path.

Examples include:

```text
invalid configuration
    -> reject

unsupported or invalid image
    -> reject

hard image limit exceeded
    -> reject

invalid palette identifier
    -> reject

invalid palette document
    -> reject

missing mandatory geometry dependency
    -> fail generation

failed mandatory validation
    -> fail generation
```

The project does not convert such failures into a different configuration or
an optional weaker implementation merely to allow generation to continue.

The mandatory accelerated geometry path is one concrete example.

Its current validation is documented in:

- [`geometry-acceleration-evaluation.md`](geometry-acceleration-evaluation.md).

## Dependency Security

Runtime dependencies are part of the project's attack surface.

Declared upper version bounds are not treated as permanent security
guarantees.

A version bound that prevents adoption of a required security fix must be
changed and the new dependency version validated.

Known vulnerability findings are not intended to be suppressed merely because
the fixed release falls outside the current declared version range.

### Continuous Integration

The current CI workflow contains a separate dependency-audit job.

It installs the production dependency set and runs:

```text
pip-audit --skip-editable --progress-spinner off
```

A known vulnerability causes the audit job to fail.

The audit runs through the normal CI workflow and the workflow also has a
scheduled execution so that a newly published advisory can be detected even
when the repository has not changed.

### Dependency Upgrades

A major dependency-range change requires:

- the complete automated test suite;
- verification of project-specific assumptions about that dependency.

For the imaging library this includes:

- decoder-registry restriction;
- content-based format detection;
- the supported-format boundary.

When a Python package bundles an independently versioned native component, the
native version must be considered separately where it affects project security
or compatibility.

The dated current dependency state is maintained in:

- [`dependency-security.md`](dependency-security.md).

## File-System Writes

The production source currently has one project-owned file-system write site.

It is located in:

```text
src/pbn/cli/main.py
```

Generation and export produce the requested document data before the CLI writes
it to the configured output path.

The source-level invariant checks that:

- no other production module performs one of the recognized file-system write
  operations;
- the permitted writing module contains exactly one recognized write.

This deliberately narrows the production file-system side-effect surface.

The check is mechanical and does not claim to prove arbitrary path safety.

The output path itself remains a deployment location chosen through the
supported configuration and integration boundary.

## Generated Output

The generator supports PDF as its only generated artifact format.

The Core produces the format-independent:

```text
VectorDocument
```

and Infrastructure serializes that document to PDF.

External values do not become an alternate executable template or markup
format.

Tests verify the expected generated PDF structure and output boundary.

How a resulting PDF is:

- stored;
- exposed;
- downloaded;
- rendered;
- expired;
- deleted;

is outside the generator and remains the responsibility of the integrating
application.

## Resource Consumption

Validated image dimensions and processing resolution bound the input entering
generation.

They do not create a hard wall-clock or address-space limit for the complete
process.

The generator intentionally does not:

```text
terminate itself after a timeout
apply its own address-space limit
run generation in an internal isolation worker
```

A caller processing untrusted input must enforce resource limits around the
generator process using mechanisms appropriate to its platform and deployment.

The current measured runtime and memory behavior is maintained in:

- [`adversarial-input-measurements.md`](adversarial-input-measurements.md).

Representative input-loading measurements are maintained in:

- [`input-bound-measurements.md`](input-bound-measurements.md).

Suggested deployment sizing and the process boundary are maintained in:

- [`integration-contract.md`](integration-contract.md).

Those figures are intentionally not duplicated here because they depend on:

- processing resolution;
- hardware;
- project configuration;
- current implementation.

## Trusted and Untrusted Profiles

Trusted and untrusted operation use the same validation mechanisms.

The difference is configuration.

The project ships:

```text
config/example.toml
config/untrusted.toml
```

Both provide all image-limit controls required by ADR-0016.

The untrusted profile uses stricter values.

A trusted profile therefore does not bypass the mandatory image boundary, and
an untrusted profile does not activate a separate generation implementation.

This prevents security behavior from diverging into two unrelated code paths.

## Security Validation Coverage

Security validation is distributed across focused tests.

Representative current coverage includes:

```text
tests/test_preserved_invariants.py
tests/test_untrusted_input_contract.py
tests/test_image_input_enforcement.py
tests/test_image_failure_containment.py
tests/test_image_decoder_policy.py
tests/test_image_format_detection.py
tests/test_jpeg_auxiliary_frames.py
tests/test_limit_profiles.py
tests/test_palette_identifier_validation.py
tests/test_palette_content_validation.py
tests/test_palette_text_is_renderable.py
tests/test_error_disclosure.py
tests/test_cli_contract.py
tests/test_pdf_output_structure.py
```

The test suite is authoritative for the complete current inventory.

This document intentionally does not record a test count.

Counts change as the project evolves and do not represent a security boundary.

## What the Tests Prove

The automated coverage combines different kinds of evidence.

### Structural Checks

Structural tests verify properties such as:

- prohibited imports are absent;
- prohibited dynamic execution calls are absent;
- XML parser imports are absent;
- configuration uses `tomllib`;
- production code does not import developer tools;
- broad exception handlers re-raise;
- production file writes remain constrained.

### Boundary Tests

Boundary tests exercise behavior such as:

- image limits;
- supported and unsupported image formats;
- detected-format mismatches;
- decoder restriction;
- JPEG auxiliary-frame handling;
- malformed-image failure containment;
- palette identifier confinement;
- error disclosure;
- CLI result classification.

### Differential and Integration Tests

Other security-relevant behavior is validated at integration boundaries,
including:

- required geometry dependency behavior;
- generated PDF structure;
- dependency assumptions during upgrades.

No single test proves the complete security model.

The security model is the combination of architectural rules, focused
behavioral tests, source-level invariants and deployment responsibilities.

## Measurement Is Not Enforcement

Developer measurement tools characterize expensive inputs.

They are not runtime security controls.

In particular:

```text
tools/measure_input_bounds.py
tools/measure_adversarial_input.py
```

exist to measure behavior so that limits can be chosen and deployment controls
can be sized.

The tools do not make generation safe merely by existing.

Security enforcement remains divided between:

```text
generator
    validates and normalizes input

integrator
    bounds the process and request lifecycle
```

## Reporting Vulnerabilities

The repository's vulnerability-reporting process is documented in:

- [`../SECURITY.md`](../SECURITY.md).

Suspected vulnerabilities should follow that reporting process rather than
being disclosed through a public issue before investigation.

The security policy also defines the currently supported security-maintenance
scope for the pre-1.0 project.

## Revalidation Requirements

Security validation must be revisited after a material change to:

- accepted image formats;
- decoder-registry behavior;
- image-loading dependencies;
- image-dimension controls;
- processing-resolution semantics;
- the JPEG auxiliary-frame exception;
- configuration parsing;
- request-controlled path construction;
- palette identifier syntax;
- palette document parsing;
- project error disclosure;
- the CLI integration contract;
- runtime dependency ranges;
- required compiled dependencies;
- output serialization;
- project-owned file-system writes;
- the boundary between production source and developer tools;
- external process-execution behavior;
- any source-level invariant mechanically protected by
  `tests/test_preserved_invariants.py`.

A change that intentionally weakens or changes a binding ADR rule requires a
new architectural decision before implementation.

## Current Status

The current security-validation state is:

```text
secure-by-default architecture:
    accepted

mandatory image loading boundary:
    enforced

normalized project-owned InputImage:
    enforced

supported image formats:
    BMP, JPEG, PNG, WEBP

RAW and TIFF:
    unsupported

general MPO input:
    unsupported

JPEG primary-frame exception:
    narrowly supported

decoder registry restriction:
    enforced

hard image dimension and pixel limits:
    enforced

processing-resolution normalization:
    enforced

trusted/untrusted controls:
    same mechanisms, different configured values

palette identifier path confinement:
    enforced

external library failure translation:
    enforced at normal boundaries

public/diagnostic error separation:
    enforced

request attribution:
    enforced

fail-closed required dependencies:
    enforced

dependency vulnerability audit:
    CI-enforced and scheduled

dynamic external code execution:
    mechanically prohibited in production source

production shell execution:
    mechanically prohibited

unsafe general-purpose deserialization:
    mechanically excluded from production source

production XML parsing:
    mechanically excluded

production network access:
    mechanically excluded

production developer-tool imports:
    mechanically excluded

project-owned file writes:
    mechanically constrained to one production site

generator wall-clock limit:
    intentionally not provided

generator address-space limit:
    intentionally not provided

deployment concurrency and rate limits:
    integrator responsibility

generated-document serving and lifecycle:
    integrator responsibility
```

## Related Documentation

For the binding security principles, see:

- [`adr/0002-security-principles.md`](adr/0002-security-principles.md).

For dependency boundaries, see:

- [`adr/0003-dependency-boundaries.md`](adr/0003-dependency-boundaries.md).

For untrusted image processing, see:

- [`adr/0016-untrusted-input-boundary.md`](adr/0016-untrusted-input-boundary.md).

For public versus diagnostic error disclosure, see:

- [`adr/0019-error-disclosure-boundary.md`](adr/0019-error-disclosure-boundary.md).

For dependency-version policy, see:

- [`adr/0021-dependency-version-bounds.md`](adr/0021-dependency-version-bounds.md).

For the process integration contract and deployment responsibilities, see:

- [`integration-contract.md`](integration-contract.md).

For current adversarial resource measurements, see:

- [`adversarial-input-measurements.md`](adversarial-input-measurements.md).

For representative input-loading measurements, see:

- [`input-bound-measurements.md`](input-bound-measurements.md).

For dated dependency-security evidence, see:

- [`dependency-security.md`](dependency-security.md).

For geometry dependency validation, see:

- [`geometry-acceleration-evaluation.md`](geometry-acceleration-evaluation.md).

For the overall system architecture, see:

- [`architecture-overview.md`](architecture-overview.md).

For vulnerability reporting, see:

- [`../SECURITY.md`](../SECURITY.md).

For remaining planned work, see:

- [`../ROADMAP.md`](../ROADMAP.md).