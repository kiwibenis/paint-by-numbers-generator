# Integration Contract

What this project promises to whoever builds a front end for it, per
ADR-0026. A front end may be written in any language, served by any web
server and deployed in any way; this project does not know what runs it.

Two integration points. Python callers use the library, everyone else
starts a process.

## The process boundary

    pbn generate --input <image> --output <document> --config_file <toml> --json

**Standard output** carries the result and nothing else. With `--json`
it is exactly one object; without it, nothing.

**Standard error** carries progress and diagnostics. The diagnostic
message names paths and internal steps. It is written for an operator
and belongs in a log, never in a response.

### Exit codes

Following the `sysexits` convention.

| Code | Meaning | A front end typically answers |
|---|---|---|
| 0 | A document was produced | 200 |
| 65 | The request caused the failure | a client error |
| 78 | The configuration caused the failure | a server error, and alerts an operator |
| 70 | The operation caused the failure | a server error |

The distinction between 65 and 70 comes from `caused_by_request` on the
error class, not from a list of types. A failure type added later
therefore already maps correctly.

### The object

On success:

```json
{"output": "/path/given/as/--output", "status": "succeeded"}
```

On failure:

```json
{
  "status": "failed",
  "error": {
    "type": "CorruptedImageError",
    "message": "The image could not be decoded.",
    "caused_by_request": true
  }
}
```

`message` is written for a stranger and can be shown as it is. It never
contains a path, a value from the input or a stack trace, which is
asserted by tests. `type` is the same name a Python caller catches.

## The library

```python
from pbn.application import GeneratorApplication
from pbn.exceptions import ImageTooLargeError, PbnError
```

Failures that represent a request or operation outcome in the supported
generation workflow are `PbnError` instances. Each carries:

- `public_message` for whoever made the request;
- `diagnostic_message` for whoever operates the service;
- `caused_by_request`, classifying the failure as request-caused or
  operation-caused.

Programmer contract violations are separate from those project outcomes.
Direct construction or lower-level use of library and domain objects may raise
`TypeError` or `ValueError` when a Python caller supplies an invalid type,
shape or value. Those exceptions describe incorrect use of the Python API.
They do not carry public-versus-diagnostic disclosure metadata and are not part
of the command-line process contract.

A defect in the project's own processing is a project outcome rather than a
programmer argument error. A state the project's processing says cannot occur
raises `InvariantViolationError`, attributed to the operation. Through the
process boundary it therefore becomes exit code 70 and a machine-readable
failure object rather than a traceback and exit code 1. Ten such conditions
were raised as `RuntimeError` and left this contract entirely.

The library says more than the process boundary can: a project exception
carries its cause, and catching `ImageTooLargeError` distinguishes cases
that share an exit code.

## What a front end has to provide

**A bound on time and memory.** This project enforces none. ADR-0016
places wall-clock and address-space enforcement outside the generator,
because the caller that starts the process knows the platform,
deployment model and available resource budget. Bound the process with
`ulimit`, a job object or a container.

The figures to size that bound with, at the 1.6 megapixel processing
resolution, from `docs/adversarial-input-measurements.md`:

| | Worst measured | Suggested bound |
|---|---|---|
| Wall clock | 100.0 s | 200 s |
| Peak memory | 1437 MB | 2048 MB |

Memory scales linearly in the pixel count and carries over to another
resolution. **Runtime does not**: it scales with an exponent up to 1.27,
so a higher resolution needs a new measurement.

The most expensive input measured is a **ten kilobyte file**. A bound on
upload size is not a bound on cost.

**Where the input bound sits, and why it is not the interesting one.**
An input above `maximum_pixel_count` is refused without being decoded.
At the untrusted profile's 40 megapixels, decoding alone would cost
154 MB and 0.6 s, from `docs/input-bound-measurements.md`. That is
about a tenth of the memory bound above and under one percent of the
time bound, so raising or lowering it moves the total very little.

Decoding is linear in the pixel count throughout, roughly 3.9 bytes and
12 nanoseconds per pixel, with no threshold to derive a bound from. Pick
one by how much of the budget a deployment is willing to spend before an
input is known to be usable.

The worst case is not a large upload. Every input is reduced to the
processing resolution, and reduction lowers the unique color count that
drives quantization: 24 megapixels of noise carry 12.8 million distinct
colors and arrive at 418 thousand, while 1.6 megapixels of noise keep
1.5 million. **An input already at the processing resolution is the
expensive one**, which is what the figures in the table above were
measured on.

**Concurrency, queueing and rate limiting.** One generation may reserve
the memory bound above, so the number run at once times that is what the
machine must hold. A client is only identifiable where requests arrive;
this project never sees one.

**How documents are served.** The generated document is a PDF and
nothing else (ADR-0027). It is not markup, so it does not execute in a
page; a front end that offers it as a download or renders it in an
isolated viewer decides that on its own terms. This project neither
serves it nor knows how it will be.

**JPEG with auxiliary frames.** A photograph from a recent phone is an
ordinary JPEG with a gain or depth map attached, which makes the imaging
library report `MPO`. Such a file is accepted when its name claims JPEG
and its index declares a JPEG primary image, and only the primary frame
is read. ADR-0016 defines this narrow JPEG-specific exception. A front
end need do nothing for this and, in particular, need not strip the
extra frames before passing the file on.

**Selecting a palette.** `pbn palettes --json` reports the identifiers,
versions, names and color counts a generation may select, as one object
on standard output. A front end builds its chooser from that rather than
reading `palettes/` itself, which would mean reproducing the file naming
rule and the schema, and offering palettes that do not load. Every
listed palette loads, because listing loads it. A missing directory is
exit code 70, not an empty list.

**Paths are yours, content is the caller's.** This project builds four
file system paths: the palette file, the configuration file, the input
image and the output document. Only the first is built from a value a
request supplies, and that value is bounded by character set and range
before the path is built and confined to the palette directory
afterwards. The other three come from configuration.

That division is the assumption behind the guarantee. A front end
decides where an upload lands and what the generator is told to read and
write; the caller supplies bytes. A front end that puts a caller's
string into the input or output path has moved that boundary, and this
project's validation does not follow it there.

**Palette text.** A palette's display name and color names are limited
to the 218 characters the legend fonts can print: WinAnsi without the
control characters, which covers Latin script and its accents. A palette
document containing anything else is rejected when it is loaded, rather
than printed as substituted symbols. A front end offering a palette
chooser is offering identifiers from `palettes/`, and never a document,
so this constrains the operator adding a palette and not the caller.

**Cleanup.** This project writes the document it was asked for and
nothing else. What accumulates and when it is removed is not its
concern.

## What this project provides

Validation of untrusted input before any unbounded allocation, decoders
restricted to BMP, JPEG, PNG and WEBP, palette identifiers confined to
the palette directory, and no unhandled exception from malformed,
oversized or truncated input.

**The extension is part of the contract.** The filename states which of
those four formats the caller claims, and the decoded content has to
match that claim. A file whose extension is not `.bmp`, `.jpeg`, `.jpg`,
`.png` or `.webp` is refused before it is opened, so a front end that
stores an upload under a name of its own has to give that name the right
extension. The one exception is a JPEG carrying auxiliary MPF frames,
which the imaging library reports as `MPO`; it is accepted when the
extension claims JPEG and the first MPF entry declares a JPEG primary
image, and only that primary frame is used.

The full list of what is validated is in
[`security-validation.md`](security-validation.md).