# Security Policy

## Project Status

Paint by Numbers Generator is currently a pre-1.0 project under active
development.

Until a stable release policy is defined, security fixes target the current
`main` branch. Older commits, development snapshots and superseded pre-release
states are not maintained as separate security-support branches.

## Reporting a Vulnerability

Please do not open a public GitHub issue for a suspected security vulnerability.

Use GitHub's private vulnerability reporting feature for this repository so
that the report can be reviewed before public disclosure.

A useful report should include, where applicable:

- the affected commit or release;
- the affected operating system and Python version;
- the security impact;
- the relevant input or configuration;
- steps required to reproduce the issue;
- whether the issue is deterministic;
- any known conditions required to trigger it.

Please minimize reproducer files where possible and do not include unrelated
personal data, credentials, access tokens or other secrets.

## Security-Relevant Areas

Reports are particularly relevant when they concern security boundaries such
as:

- processing of untrusted image input;
- bypasses of configured input limits;
- path traversal or unintended file access;
- unsafe palette or configuration handling;
- generated-output structure manipulation;
- information disclosure through public error output;
- dependency vulnerabilities;
- unexpectedly unbounded resource consumption that bypasses the documented
  input and integration constraints.

Performance problems or generation-quality defects are not security
vulnerabilities by themselves unless they cross a documented security boundary
or enable a security-relevant denial of service.

## Disclosure

Please allow reasonable time to investigate and prepare a fix before publishing
details of a vulnerability.

Once a report has been resolved, disclosure and advisory publication can be
coordinated through GitHub Security Advisories where appropriate.

## Deployment Boundaries

The generator validates and normalizes supported image input, but it does not
provide process isolation, wall-clock enforcement, deployment-level memory
limits, rate limiting or request lifecycle management.

Applications processing untrusted input are responsible for enforcing those
deployment controls around the generator process.

What the generator itself validates, and the evidence behind each boundary,
is documented in:

`docs/security-validation.md`

The integration boundary and expected deployment responsibilities are
documented in:

`docs/integration-contract.md`