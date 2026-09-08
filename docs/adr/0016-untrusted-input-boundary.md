# ADR-0016 - Untrusted Input Boundary

## Status

Accepted

## Context

Image input may originate from an untrusted caller.

ADR-0002 requires external input to be validated and identifies malformed
files, resource exhaustion and unsafe path handling as relevant risks.
ADR-0012 requires user-supplied image data to be normalized before it crosses
into the Core.

Those rules require one mandatory input boundary that every interface uses.
Validation performed only in a command-line interface, web front end or other
caller could be omitted by another interface and would therefore not protect
the generation pipeline itself.

Image decoding is the first expensive operation applied to an uploaded file.
Compressed file size does not bound decoded dimensions, memory consumption or
generation cost. Limits must therefore be derived from declared image
dimensions and from the processing resolution rather than from upload size
alone.

The imaging library also supports substantially more formats than this project
intends to accept. Because it selects decoders from file content rather than
from the filename extension alone, an extension allowlist does not by itself
bound the decoder attack surface.

The project needs only common raster photographs and images. Supporting RAW
camera formats would require additional native decoding surface, while TIFF is
the container through which the commonly encountered TIFF-based RAW formats
can reach a decoder. Neither format is required by the generation model.

Some current phones produce JPEG photographs that contain an MPF index with
auxiliary JPEG frames such as gain maps or depth maps. The imaging library may
report such a file as `MPO` even though its primary image, filename and file
content are JPEG. Rejecting every such file would reject ordinary phone
photographs, while enabling general MPO input would unnecessarily expand the
supported format model.

Generation itself can also consume substantial CPU time and memory after input
validation. This project is a reusable library and command-line application,
not the server or process supervisor that hosts it. The caller that launches a
generation process is therefore the component that knows the operating system,
deployment model, concurrency policy and available resource budget.

## Decision

Untrusted image input shall pass through one mandatory loading and validation
boundary before generation.

Every interface shall use that boundary. A command-line invocation, Python
caller or future front end shall not provide decoded or otherwise unchecked
user image data directly to normal Application generation.

The Application layer shall depend on an image-loading boundary rather than on
a concrete imaging library. The concrete decoder implementation shall remain
in Infrastructure in accordance with ADR-0003.

The validated result crossing inward shall be the project's normalized
`InputImage` model and shall contain no imaging-library types.

### Input limits

Input limits shall be required for every image load.

The controls shall include at least:

- maximum input width;
- maximum input height;
- maximum input pixel count;
- processing pixel count.

Declared dimensions shall be checked before unbounded pixel materialization.

The imaging library's own decompression-bomb protection shall be configured so
that an image exceeding the configured pixel bound is rejected rather than
merely warned about.

An accepted image larger than the configured processing resolution shall be
reduced before normalized pixel data is materialized for the generation
pipeline.

The processing resolution is a configurable deployment value rather than a
hard-coded hidden default. The shipped trusted and untrusted profiles currently
use a processing target of 1.6 megapixels.

Two limit profiles shall exist for trusted local and untrusted operation.

The profiles may differ in their values but shall use the same controls. A
profile shall not disable a validation control.

Limit values shall remain explicit configuration that can be supplied through
the project's supported configuration and command-line mechanisms.

### Supported image formats

The accepted image formats shall be exactly:

- BMP;
- JPEG;
- PNG;
- WEBP.

RAW camera formats and TIFF shall not be supported.

RAW support shall not remain as a disabled configuration option or dormant
decoder path. Reintroducing RAW or TIFF support requires an architectural
decision.

Unsupported image decoders shall be removed from the imaging library's
reachable decoder registry where the library permits this.

The filename extension shall state which supported format the caller claims,
but it shall not select the decoder.

The decoder shall be selected from the file content by the imaging library.

After opening the file, the detected format shall be validated against the
format claimed by the extension. A mismatch shall be rejected except for the
single JPEG auxiliary-frame case defined below.

An unsupported extension shall be rejected before decoding.

### JPEG with auxiliary frames

A JPEG carrying auxiliary MPF frames may be accepted through a narrow exception
to exact detected-format equality.

This exception applies only when all of the following hold:

1. the filename extension is `.jpg` or `.jpeg`;
2. the imaging library reports the opened image as `MPO`;
3. the MPF metadata exposed by the imaging library contains a first image
   entry;
4. that first entry declares `ImageDataFormat` as `JPEG`;
5. that first entry declares `MPType` as `Baseline MP Primary Image`.

If any of these conditions is absent, malformed or unrecognized, the input
shall be rejected.

`MPO` shall not become a separately supported input format.

The MPO decoder shall remain outside the registered supported decoder set, and
a `.mpo` input path shall remain unsupported.

No detected-format mismatch other than this JPEG-specific case is permitted.

Only frame zero shall contribute to the normalized `InputImage`.

The loader shall not seek to, iterate over or decode auxiliary frames.

Input dimension limits and processing-size calculations shall apply to the
primary frame that becomes the normalized image.

Auxiliary frames shall not cross the Infrastructure boundary.

The project shall not introduce an independent raw MPF parser solely to
validate metadata that the imaging library ignored.

If the imaging library ignores malformed or unusable MPF metadata and reports
the input as ordinary `JPEG`, the file shall follow the normal JPEG validation
path. The project does not claim to detect MPF structures that the imaging
library itself discarded before exposing the opened image.

### Failure handling and disclosure

Malformed, truncated, unsupported or oversized image input shall fail through
the project's image-error hierarchy rather than escaping from the loading
boundary as an arbitrary decoder exception.

Detailed operator diagnostics and caller-safe error disclosure are separate
concerns.

ADR-0019 defines the public and diagnostic error-message boundary and the
attribution of failures to the request or to the operation. This ADR does not
require all input failure modes to be indistinguishable to a caller.

### File-system boundaries

Request-controlled identifiers used by project-owned path construction shall be
validated before a path is constructed and shall be confined to their intended
directory.

In particular, a palette identifier shall not be able to escape the palette
directory through absolute paths, traversal components or unsupported
characters.

Input, configuration and output paths supplied by an integrating application
are deployment locations chosen by that integrator. The image-content
validation boundary does not make an attacker-controlled pathname safe if an
integrator chooses to pass one.

### Resource enforcement

The project shall not run generation inside an internal security-isolation
worker.

The project shall not enforce its own wall-clock or address-space limit for a
generation run.

A caller that executes the generator on untrusted input and requires bounded
resource consumption shall enforce those bounds around the process by means
appropriate to its platform and deployment environment.

The project shall provide measurements of representative and adversarial
generation cost so that an integrator can size those external limits.

Those measurements belong in dedicated measurement and integration
documentation rather than in this architectural decision, because absolute
runtime and memory figures change with hardware, processing resolution and
implementation.

External process termination may leave deployment-level concerns such as
partial files, cleanup, retry policy and job state. Those concerns belong to
the integrating application that applies the external limit.

This project does not require generation to be exposed as a synchronous or
asynchronous job. Queueing, concurrency, rate limiting and request lifecycle
are integration decisions outside the generator.

ADR-0026 defines the command-line process boundary available to non-Python
integrators.

### Generated artifacts

Input validation does not define how generated artifacts are served to an
untrusted consumer.

The supported generated document format is governed by ADR-0027.

Serving, storing, viewing, expiring or deleting generated documents remains the
responsibility of the integrating application.

Changing the accepted image-format set, restoring an internal security worker,
moving resource enforcement into the generator, weakening the mandatory input
boundary or broadening the JPEG auxiliary-frame exception requires an
architectural decision.

## Consequences

Every normal Application generation path receives image data through the same
validated loading boundary.

A new interface cannot obtain weaker image validation merely by bypassing
command-line checks.

Input cost is bounded before normalized pixel materialization by explicit
dimension and processing-resolution controls.

Trusted and untrusted deployments use the same validation mechanisms. Their
different risk profiles are represented by different configured values rather
than by different code paths.

Only BMP, JPEG, PNG and WEBP are supported. TIFF and RAW inputs are rejected,
and no dormant RAW configuration or decoder path remains available for later
accidental reactivation.

Removing unsupported decoders reduces reachable parser surface beyond what an
extension allowlist could provide.

JPEG photographs containing supported auxiliary MPF frames remain usable
without making MPO a general-purpose input format or decoding the auxiliary
frames.

The project deliberately relies on the imaging library for the MPF metadata it
exposes. It does not duplicate that parser to make stronger claims about
metadata the library ignored.

The Core remains independent of the imaging library and receives normalized
project-owned image data.

Error disclosure remains centralized under ADR-0019 rather than being
reimplemented by the image loader or by each interface.

The generator remains platform-neutral because it does not implement
operating-system-specific process isolation or resource-limit enforcement.

A deployment processing untrusted input must provide its own time, memory,
concurrency and process-lifecycle controls. The project supplies measurements
and an integration contract so that those controls can be sized without making
them part of the generator itself.