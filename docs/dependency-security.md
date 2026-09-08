# Dependency Security State

Measured on **2026-09-03**. This document describes the world rather than
the project, so it is wrong the moment it is written. ADR-0021 requires
the date for that reason.

Three kinds of number appear below, and they age differently:

- a **declared bound** is the project's own, and changes only when someone
  changes it. `tests/test_dependency_security_documentation.py` holds the
  Declared column to `pyproject.toml`;
- a **project invariant**, such as how many decoders remain reachable, is
  asserted by a test and is a defect if it changes;
- an **observation**, such as an installed version or how many decoders a
  release registers, was true of a named version on the date above and of
  nothing else. Nothing tests these, because a test would turn a fact about
  the world into an obligation on it.

Reproduce with:

    pip-audit

## Runtime dependencies

| Package | Declared | Measured | Notes |
|---|---|---|---|
| Pillow | `>=12.3,<13` | 12.3.0 | Raised from `>=11,<12` on this date |
| shapely | `>=2.1,<3` | 2.1.2 | Mandatory per ADR-0015 |
| reportlab | `>=4.4,<5` | 4.5.1 | |

`pip-audit` reports no known vulnerabilities against this set.

Wheels for every runtime dependency exist for both declared Python
versions on `win_amd64` and `manylinux`, verified on this date. The
project declares `requires-python = ">=3.12,<3.14"`, so continuous
integration exercises the two supported Python versions, 3.12 and 3.13.

## Evidence for the Pillow major upgrade

ADR-0021 requires evidence before a bound is raised across a major
release. Collected on 2026-09-03:

| Check | Result |
|---|---|
| Full test suite against 12.3.0 | 1556 passed |
| Decoder registry, 11.3.0 | 43 registered, 4 reachable |
| Decoder registry, 12.3.0 | 43 registered, 4 reachable |
| Generated output, same input and code | identical apart from timestamps and the derived `/ID` |

The last row matters most: the same image through the same code on both
versions produced PDFs of 102372 bytes that are byte-identical once
`/CreationDate`, `/ModDate` and `/ID` are normalized. Neither decoding
nor resampling moved a byte.

## What the previous bound cost

Before this date the declared bound was `Pillow>=11,<12` and the installed
version was 11.3.0. `pip-audit` reported **eighteen distinct advisories**
against it. The required fix versions were:

| Fix version | Advisories |
|---|---|
| 12.1.1 | 1 |
| 12.2.0 | 6 |
| 12.3.0 | 18 |

Every one of them was above the declared bound. The project was pinned
inside a vulnerable range by its own constraint. This is the concrete
case behind ADR-0021.

The exposure that mattered most for untrusted operation:

- **CVE-2026-25990** and **CVE-2026-42311**, out-of-bounds writes when
  loading PSD images. Reachable in principle because format detection is
  content-based: a file with an accepted extension carrying PSD content
  selects the PSD decoder, not the one the extension claims.
- **CVE-2026-59199**, out-of-bounds write in `Image.paste()` with large
  paste box dimensions.
- **CVE-2026-59205**, out-of-bounds write in `ImageCmsTransform` on a mode
  mismatch.
- **CVE-2026-59200**, decompression bomb through the PDF parser, and
  **CVE-2026-40192**, decompression bomb through FITS GZIP.
- **CVE-2026-59203**, infinite loop in the EPS parser on a negative
  `%%BeginBinary` byte count.

## What the decoder allowlist covers

The decoder deregistration of ADR-0016 removes every decoder except BMP,
JPEG, PNG and WEBP from the imaging library's registry. ADR-0016 excludes
TIFF from the supported format set together with RAW input.

The two numbers that describe this age differently.

**Four reachable afterwards** is the project's own count.
`tests/test_image_decoder_policy.py` asserts it, so a release that
registered a decoder the allowlist does not name would fail the suite
rather than widen the boundary quietly. It does not change with an
upgrade, and a change is a defect.

**Forty-three registered beforehand** is a property of the imaging library
and was the count in both 11.3.0 and 12.3.0. It is scoped to those two
versions rather than to a date: it does not drift over time, it changes
when the library does. The next release may register more, and whether the
allowlist still covers them is what ADR-0021 asks to be verified across a
major release rather than assumed.

That mitigates the format-specific advisories above, because PSD, PDF,
FITS, EPS, McIdas, GD and the font parsers are unreachable. It does not
mitigate advisories in code the accepted formats reach, and it is not a
substitute for the version. The allowlist held unchanged across the major
release, verified rather than assumed.

## RAW, removed

RAW input and its `rawpy` dependency were removed on 2026-09-03, and TIFF
was removed from the accepted formats with it. ADR-0016 records that as
the current input boundary.

What that closed, recorded because the reasoning outlives the code:

- `rawpy` bundled its own LibRaw 0.22.1. A distribution's LibRaw security
  updates never reached that binary, updating the wrapper to 0.27.1 did
  not change it, and no dependency scan could see it. It was the only
  component in this project outside everything ADR-0021 established.
- **CVE-2026-20884**, an integer overflow in the LibRaw DNG loader with
  potential code execution, was reachable through the accepted `.dng`
  extension. **USN-8522-1** collects CVE-2026-21413, CVE-2026-24450,
  CVE-2026-24660, CVE-2026-20889 and CVE-2026-5342.
- `except LibRawError` could not have contained a native memory-safety
  fault, so error handling was never a substitute for isolation.

TIFF went with it because every widely used RAW format is TIFF-based. A
DNG renamed to `.tif` loaded through the TIFF decoder while RAW input was
disabled, which is what showed that disabling the decoder does not close
the format.

## Unused declared dependencies

`opencv-python`, `scikit-image`, `scipy` and `svgwrite` were declared as
runtime dependencies and imported nowhere in `src`, `tests` or `tools`.
They were removed on 2026-09-03.

`numpy` was kept as a runtime dependency on the same occasion, although
`src` did not import it either. The reason was that the vectorized color
distance work and a possible numerical array representation both need
it, and the note said the decision should be revisited if neither
arrived.

**It was revisited.** The representation change has since happened three
times, in ADR-0017, ADR-0018 and the compact worker boundary of
ADR-0014, and none of them adopted `numpy`. The vectorized color
distance work has no decision and no milestone behind it.

`numpy` therefore moved to the development extras on 2026-09-05. It is
still needed there, by `tests/test_jpeg_auxiliary_frames.py` and
`tools/measure_input_bounds.py`, and it is no longer installed alongside
the generator. Nothing in `src` imports it, which is what the runtime
dependency set is supposed to describe.