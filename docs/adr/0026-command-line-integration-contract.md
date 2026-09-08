# ADR-0026 - The Command Line Interface as the Integration Contract

## Status

Accepted

## Context

The project is a reusable Python library and also supports integration from
applications written in other languages.

Python callers can use the library directly. A non-Python caller needs a
portable boundary that does not require importing Python implementation
details.

The command line interface provides that process boundary.

A usable process contract must let a caller distinguish outcomes without
parsing human-readable diagnostics, and it must keep caller-safe result data
separate from operator-facing progress and diagnostics.

ADR-0019 defines the project-level distinction between public error
information, diagnostic information and request attribution.

## Decision

The command line interface shall be the supported integration contract for
callers that do not use the Python library directly.

The process contract shall be documented and tested as a public interface.

Exit codes shall distinguish:

- success;
- a failure caused by the request;
- a failure caused by configuration;
- a failure caused by the operation.

The exit-code values shall follow the `sysexits` convention.

Machine-readable mode shall produce exactly one result object on standard
output for a completed command outcome.

For generation, a successful machine-readable result shall identify the
produced output document.

A machine-readable failure shall expose:

- the project error type;
- its public message as defined by ADR-0019;
- its `caused_by_request` attribution.

Standard output shall carry result data and shall not contain progress or
operator diagnostics.

Standard error shall carry progress and diagnostic information.

Diagnostic messages may contain paths and internal details and shall not be
treated as caller-safe output.

Human-readable mode may omit a structured success object when the command's
result is already the requested side effect, such as writing a document.

Commands whose result is data intended for the caller, such as palette
listing, may write that result to standard output in their human-readable form.

Python callers shall continue to use the library and its exception hierarchy
rather than being required to invoke the process contract.

Changing exit-code meanings, machine-readable result shape, stream semantics or
the role of the CLI as the non-Python integration boundary requires an
architectural decision.

Nothing in this contract bounds runtime or memory consumption.

ADR-0016 keeps wall-clock and address-space enforcement outside the generator.
An integrating caller that requires such bounds shall apply them around the
process it starts.

## Consequences

Non-Python callers have a portable integration boundary with explicit outcome
semantics.

Callers do not need to parse diagnostic prose to classify a failure.

Caller-safe machine-readable output remains separated from potentially
sensitive operator diagnostics.

Exit codes, result-object shape and stream roles become compatibility
obligations and require deliberate review when changed.

The Python library can expose richer exception detail than the process
contract without weakening the non-Python integration boundary.

Resource supervision remains a deployment responsibility rather than part of
the CLI contract.