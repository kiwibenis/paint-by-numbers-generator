# ADR-0019 - Error Disclosure Boundary

## Status

Accepted

## Context

Project failures serve two different audiences.

An operator diagnosing a failed generation needs detailed information such as
paths, values and internal processing steps.

A caller that supplied untrusted input must not automatically receive those
details, because they may disclose information about the environment or
configuration that did not originate from that caller.

An interface also needs a stable way to determine whether a failure was caused
by the request or by the operation so that it can classify the outcome without
reconstructing that rule from individual exception types.

The command-line integration contract of ADR-0026 exposes this distinction
across the process boundary.

## Decision

Every project error shall provide separate diagnostic and public information.

The diagnostic message is the message supplied when the exception is
constructed.

It is intended for an operator and may include paths, supplied values and
internal processing details.

The public message shall be defined by the error class.

It is intended for an untrusted caller and shall not interpolate
request-independent environment details, paths, stack traces or internal
state.

Every project error shall also declare whether the failure was caused by the
request.

Interfaces shall derive request-versus-operation attribution from that
property rather than from their own duplicated list of exception types.

The base project error shall default conservatively:

- a generic public message;
- attribution to the operation rather than to the request.

A subclass that requires different public disclosure or attribution shall
declare that behavior explicitly.

An error caused by caller input may disclose enough information for the caller
to correct that input when doing so does not reveal independent project or
deployment state.

Where useful caller information conflicts with protecting deployment state,
protecting deployment state takes precedence.

Public failure modes do not need to be globally indistinguishable. A caller may
for example distinguish broad categories such as an oversized image and an
unsupported image when both distinctions concern only the request it supplied.

The process contract defined by ADR-0026 shall expose the public message and
request attribution in machine-readable failure output.

Operator diagnostics shall remain separate from that machine-readable public
result.

Adding a project error type requires defining its disclosure and attribution
behavior.

## Consequences

Public error handling can be shared across interfaces without auditing every
raise site for accidental environment disclosure.

Process integrations can classify failures without parsing diagnostic prose or
maintaining their own mapping of exception classes.

Diagnostic messages remain useful to operators and may contain information that
must not be returned to an untrusted caller.

Each error class carries additional disclosure metadata that must remain
consistent with the underlying failure.

Public messages are intentionally less detailed than diagnostic messages.

A logging system that records diagnostic messages must itself be treated as
sensitive because those messages may contain file-system paths and other
operator information.

A check that guards against a state the project's own processing cannot
produce belongs in the hierarchy like any other failure. Such a check is
written for a condition that is not expected to occur, which is exactly why
its failure path is never exercised, and a failure path that leaves the
hierarchy leaves it silently. `InvariantViolationError` carries these:
attributed to the operation, because a caller cannot correct a defect by
changing what it sent.