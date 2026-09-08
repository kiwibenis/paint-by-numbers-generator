# Architecture Overview

This document provides a high-level view of the current Paint by Numbers
Generator architecture.

It is descriptive documentation, not an Architecture Decision Record. Accepted
ADRs in [`docs/adr/`](adr/) remain the binding architectural source of truth.
If this overview conflicts with an accepted ADR, the ADR takes precedence.

Detailed formats, measurements, integration guidance and reference-data evidence
are maintained in dedicated documentation and are linked from the relevant
sections below rather than duplicated here.

## Purpose

The Paint by Numbers Generator is a reusable Python library with a command-line
interface that converts raster images into printable paint-by-numbers PDF
documents.

The architecture is designed to keep generation behavior:

- deterministic and reproducible;
- independent from interface-specific concerns;
- independent from concrete third-party library types;
- secure at external-input and integration boundaries;
- testable at narrow architectural boundaries;
- reusable by Python callers and external applications.

The long-term project direction is described in [`VISION.md`](../VISION.md).

## Architectural Model

The project follows the four conceptual layers defined by
[ADR-0001](adr/0001-layered-architecture.md):

```text
+---------------------------+
|         Callers           |
| Python / external process |
+-------------+-------------+
              |
              v
+---------------------------+
|            CLI            |
| interface + composition   |
+-------------+-------------+
              |
              v
+---------------------------+
|        Application        |
| use-case orchestration    |
| ports + execution policy  |
+-------------+-------------+
              |
              v
+---------------------------+
|            Core           |
| domain models             |
| deterministic semantics   |
| generation business rules |
+---------------------------+

        Application ports
              ^
              |
+-------------+-------------+
|       Infrastructure      |
| image decoding            |
| process execution         |
| geometry acceleration     |
| configuration loading     |
| palette loading           |
| PDF serialization         |
+---------------------------+
```

The arrows describe use-case flow rather than permission for arbitrary
dependencies.

The Core does not depend on the CLI or Infrastructure. External runtime
libraries are confined to Infrastructure. The Application layer coordinates
Core operations and depends on project-owned ports and models.

Core responsibility is conceptual rather than tied to a single `core`
directory. Core behavior is intentionally distributed across packages that
represent individual domain responsibilities.

## Layer Responsibilities

### CLI

The command-line interface lives under:

```text
src/pbn/cli/
```

It is the interface and composition boundary.

The CLI is responsible for:

- parsing command-line syntax;
- combining explicit CLI values with optional TOML configuration;
- building and validating effective generation configuration;
- loading the selected reference palette;
- constructing Infrastructure adapters;
- constructing and invoking `GeneratorApplication`;
- writing the generated PDF to the configured output path;
- reporting progress, success and failures according to the CLI contract.

The CLI does not own paint-by-numbers generation semantics.

Python callers may use the library directly. For callers that do not integrate
through Python, the CLI is the supported process boundary defined by
[ADR-0026](adr/0026-command-line-integration-contract.md).

The complete non-Python process contract, including stream semantics, exit
classification, machine-readable results and frontend responsibilities, is
documented in
[`integration-contract.md`](integration-contract.md).

The CLI also exposes the loadable reference-palette catalogue through the
supported process contract so that external front ends do not need to inspect
the `palettes/` directory or reproduce palette-loading rules.

### Application

Application orchestration lives primarily under:

```text
src/pbn/application/
```

The main use-case boundary is `GeneratorApplication`.

The Application layer is responsible for:

- coordinating validated input, palette and configuration;
- resolving physical output and image-placement geometry;
- converting `minimum_region_size_mm` into the pixel-space paintability
  constraint used by the Core;
- resolving the configured color-distance strategy;
- constructing the configured optional region-complexity policy;
- selecting sequential or process-parallel quantization according to validated
  execution policy;
- supplying the required overlap-detection dependency;
- invoking Core generation;
- passing the resulting `VectorDocument` to the PDF export boundary.

Application boundaries isolate external or interface-specific behavior from the
use case. Current boundaries include:

- `ImageLoaderPort`;
- `QuantizationExecutorPort`;
- `OverlapDetectorPort`;
- `PdfExporterPort`;
- `ProgressReporter`.

The Application layer does not contain concrete third-party integrations.

Progress reporting is an Application-owned boundary. The Application reports
progress without depending on a concrete interface. The CLI supplies the
console implementation, while library use can remain silent through
`NullProgressReporter`.

### Core

The Core owns project semantics and project-owned domain models.

Its responsibilities are distributed across responsibility-specific packages,
including:

```text
src/pbn/models/
src/pbn/color/
src/pbn/core/
src/pbn/regions/
src/pbn/outline/
src/pbn/label/
src/pbn/pipeline/
```

Important Core responsibilities include:

- color conversion and color-distance calculation;
- palette-color quantization;
- connected-region detection;
- mandatory paintability merging;
- paintability verification;
- optional quality-bounded region-complexity reduction;
- outline tracing;
- topology-preserving outline simplification;
- label placement;
- construction of the format-independent `VectorDocument`.

The Core operates on project-owned models and immutable values rather than
Pillow, ReportLab, Shapely or other external-library object types.

### Infrastructure

Concrete external integrations live under:

```text
src/pbn/infrastructure/
```

Current Infrastructure responsibilities include:

- TOML configuration loading;
- raster image decoding and normalization;
- image decoder restriction and validation;
- reference-palette loading and validation;
- process-based quantization execution;
- accelerated outline-overlap detection;
- PDF serialization and palette-legend generation.

The principal runtime libraries are currently:

- Pillow for raster image decoding;
- ReportLab for PDF serialization;
- Shapely for compiled geometry predicates.

Infrastructure translates between external representations and project-owned
models. Third-party types do not become part of Core or Application contracts.

Runtime dependency constraints and upgrade policy are governed by
[ADR-0021](adr/0021-dependency-version-bounds.md).

Current dependency versions, vulnerability-scan results and compatibility
measurements are intentionally kept out of this architecture overview because
they are time-sensitive. The current measured state is recorded in
[`dependency-security.md`](dependency-security.md).

## Generation Data Flow

A normal CLI generation follows the flow shown below.

The diagram includes configuration resolution and validation, palette loading,
image-input normalization, processing-resolution reduction, execution-policy
decisions, generation stages, error boundaries and CLI exit classifications.

[![Paint by Numbers generation data flow](images/generation-data-flow.png)](images/generation-data-flow.png)
The chart was made with mermaid and can be edited [here](https://mermaid.live/edit#pako:eNrtHGlv2zj2rxAedAbYUQ47vupmMnAcx3Hr2I6PpO1kYMgSbQuRJY2OJG7R3zXf95fteyQl6_LZehe72AwmKMn3HsnHd5PK14xiqjRTybx581UzNLdCvj5mJrr5osxk233MsLZKJ7Knuz1qqNSmNvY-Zqj-9JiR4B8zd6635DHVHRxwbY9ir-LZz5RDjmVHczisAZP1LVnRjCmOnZ1ipy0bT6HOfOHbt29v3jwaj0awEDK4wvajQeDnzRvy23f8BESyx6TWaV83G8NeddDstH8QdU7G8cZTW7ZmYoo_HjM4nWlMtKlny65mGo-ZPzko_qiaTRXsFTv1-6uAWGs1iWxPvTk1XOd8bJ9cyIZKTAvBZZ0MOrctoiQoL2nUrhunQOZc1Z6J4y50-tsvLn11j2RdmxoVnU7cXy6W0Ofjix7V6bNsuFGq5yfjMJinh1rQ1rULXOizrHvUOT-BZnyYLXQi6_pYVp5SIc4dSzb8NU5Mwz1ytC-0Uj5988vFPwiSd-Un6hALmEVVaij0_ARRLmLUzk8iqzs_ga1fxLmCrO1Rx9SfKaGTCbL_mTL2RrYtdhTHvs-CYgCvIkcKS7c9xYWWri8QUVN_R7YxqqH1rNnmEsqmsiqPdcoOOEbhV06cn72zMFz5dQWEiyScxCAsECb4ywOxU8UOkasOiFgClr5awBwfjrgLC9gRYi47gcfMtwh_LoG7l56mq6RBDQrsMW3OKs5hkGBNlV2aYGsula10DuKoKT-CrbHl3CM1bG7cUecDbEmAU5XNHaOV0Ltqs5XdSfP6gfxEdQ_URtM9m27WwRiaBvIDzDZMl4wpE6lUxdOMpDylwTnCSGkOQZIyR2AylgofFTFEm2uOA4Y-nbprwxATMISby64ySwUcm6ZO4aw3Q2qGS6fU3gLS8ObjDYBbmRU89Nxuhy6ke98jD5gs-AdcpnPLXaRu0zMcz7JMG_XZkqeUoI5shDRtDSyDcAObqOqyQtFXkTl4-43giqmb9pGqOa4M9hz3AOo1XawV0zm4Q80gJ2Cy4ICZkZRBttfiWLJOXZeSZ2o7q7bhw065XuMpWLItz6kLSGsxtDnw8kgzLM8lujbX3PXgNp0C8SPFnFs6fdXcBbFMXVM27JraMIdiOi55odp05jrAAeAXNabuzNmweXRJVD_6y0NR-7LT3kzP1TWDgjWF1WoTMMMM2wUdtGXmg9cjI0_YKa-fpnt1TXRQVkONxx3bkF-NsJXW1ns9jLTCZOq2DV4hDvexORAhmU1Rgp1AT9EhgDbX4ThJqUz--Tepfxzx6I_pcJRSlRwdXUAQEg3TyNGx6A0HKhz0PhsLQKAboudPGJtwiMuU4bbpjzJvFPXRgnAu5oIThDsfUsajlHNJz8cHgbNx6xgaiB6BGAAe836QhR8f9ueOSbfaqg8GddKvt-q1w4X-YhqQF5xT2J8-BNfKmvi_FeUKILdMGS3GBHIvtJDCkCWD_N1CjT-Ysfpzs3sR86WqoRgbpRvVbTSvixJRLMDSBYPapntteobK1C-iVMWCUKqr6qAK0pKiVYxaCbOdJjcQgmiSWOlUEOt3rgcP1V49hRryVGhkpBv6QP59h-IZ8jOYAPRCoBAILfa0EgMCSJkICxZGKZ0eUOzPjknzttqok1anetVsN8jPpN3p3VZbzc8HzH6b7e4QDSbOji6SoDBjkAKzm_YcOPBl-2QYNYlRQSLU7ppYoYic2DU7-Ykt-4kYrbBTD2GBz-xqum6-xFCb9zzzaDIfzvw5edHcmWYwCjPZVomsKNTicQp38vunIS-a6s7Iz7r77jcIZ161uTcfsb5E-jVjvj4GyjsTsJb2SjF18Iw4AhsZsZFNmU4TZdFn9cA0WxBt0b3UkVHqDG7qvZ1MU8edwTmx6fm0G20UPy5MSSZoOzYGnROUPTcVTDFt27MQ6ARUW6WKybNwZi43GLh1nFlvBpvdXqcmBJDthb4qlKo8cbdsU6EsbYJUC87C3V_sIgIydd-RJe2dRKRXvxrWUB9ZuUj1QCP4GQA95DErTemLvdfJ9ylkOH2NMbqsemE_QybgYLmCsCAuBvO-W28Q1ZYnEEGDiAGsBRGtwtLXuCq1qu3a504fHC-uL4Uh0fPzbSnyxLdsgieMtGuSXuNS8B8dQIxAI4ynEmaFmCQkfVLuMH6ewY34ivfJextne6xrxO3oFstLMWSp-hs1pusghA1NjWvSJW73mmVCddH0CD9CRdrofEcRE6SBRyj16FHwgCPdaYmQo3mfhpJYsA-NBirijFmwfh3xvpwEz4JFWuSjB54gAi6WEfbCseSCISbHl8lJYmGsIwHFDVYq1HKuQIlTbN06iKCXATUOGMXlj0m12201ayxmI90O_PMT6dX7ndbwgIkMmwbUG6fnJpOFZ11WtCCsiu5tndPchArvIn-fUnNOXXsR3G4ERaS4nV3iilJ9avUohvU-NKMls5KRpmPVRTENRNGEN5lrBrMMimYrOh2pGi-PjKzXGMEPQXXbv4YRq_HrOUc2OkVeZWFMihFohVYUrskwMvSVKt5qXFDW_G6mdlnP-nObCjKwdOSzdD-jVDjg-vxD4jW0EVrb0Xy-3zqLB1ynWN9SJkaBTIyogTGHuso9ib05a90XKweOsByYDhYMj_iJvqx2dyFYmd2EUXWEBdUtccamDYnVlsC-qm8JTg1FNx1wJCO_0rl5t3NLVlwDvNgqnC2lo3RA6fArsqOw9q-Vi3SMMRzT04g-U2P0YtpPuinvgo2yhmjJEvCWLCrvxiJu7rdizzS94rTpJiJwHCt0By8O9jYXeR5rNaO2jne-jxoW3vkhKk-8sxXlIO-8OWDQUFhWPO-G1fbgoBUfNgNIRWFZ8rwLidxWhZ5bVg4Er3y5aLNrOSe4aY0dyl1X3MN3hXxHvCmhIIkaaNR3JMxr9TSeNMZ8Z3w4SoN5-c0Xz3fdHLua0LFuTDxD-8uj4j4lwQxMwWqyrng6hEHLVw2E6zhZ5s0YY0U45RuPBMl8jL_L4ARQ3NnLTPse9gZLFGYoNbX_NVhdsuC1rVHcyOU-sK5PgbdARoRzLP8WwksTkle7GbaXcaCKgSKGJo6rKcvQlCgzz3iKH1QVs_2wVtSFLKSUNKs3K2qaXZ6ppZFJLLVze9ls15kYzceaAXE3emwhwGyJWOfwdDchUr16rdNmwSqPlWEFDEnw289hY2id5f6omlbGuBM1xsjq9ykxggV9-58Khv93PPktS1zBmMZsayxBvuunjC6TbLBUMcMlus8iNkp05mN2Zu1c-cRcTP2SCskGq42wrvGum7BKCRJcLZKKwoeZ6EdtBBvoxNXD741CYikkYmKjFZG7aGFjOTUvofDr7Qg-19AoelQRODJ3eizB9YHxYJOAwiucBOY1yDcF1lkaFrdr7H0Me7HJYfvbg4qTO1i4UzwmvXoDyyONert-yLedfBr0HDgny9n892X4z59JN1Rs2Cry6TJTywihR1FSnnPeAcgt-G-MhhbRcgZmQYzREQS8fLmntjaJQseg-uDnO_6b0mXSyuzxspghzNrvMe85CJZdCzD5tUDcFw23WkxPuAdOM8zFfZ1EdrcnsOkM_vcWJ7K7XeinHB4JDu7_5Yr_4nLFD6rLdblbC1kS1hGpzfb8lwqpRVLIPhwwbc5Eo_7DhV7UjfEnPP2IYYm77kFiLHD6w4hRSXYN91xezBTwlPsutXeY0ELef8gnSaVj0hkOWuj-D-2yxDzos3BW_rQv5LS28lL4VMJHjb4K5PXrdCfxAHMOTAgxzOniSFzX4lNgRDFTqcUE-OMfy2nhxJWkq6tijtN5prYuW1fMf6bnVKveifRnskX1BTE5CeGDEwlVQ7inhjAO-z8vyh0wdxE8HUV5utaYr0AJnnqOrNc9DE_izu4hMRZYgI8JDnH1u0_tfYgePo_0r8MHzQ2Gf55BkkuS2ALUN_jhd10QIkeD90bU6j3EUFcCH8R6lI_Jfb026PTIVac2vK23B4cxHT51EFmckikGuTIVL7in23Tzh1eI7FOxlfd7n1l4iJQjhEMk2Bl_PiA73x6zp8j1j91O70CcBPqwT3-iV8u3UJv4V8VvlrrqhKOkvoCrXq4qF8FUVOCBPPfY62U4jDg-vjhF2PHCTXz1VL0Sb59fbA1G_dtbAI-HGlfXwkQGq93PRvaHtVq93489uXY8BUtfEWqnKyzs2YFuKLCkyeN7Kz0qZIaUvUJZC8HCujVfpKQCbJtB7HhPbKmTEX-Cf8grmlWXMIIsvrdxRhbsXDNWfKtjmRDtbYDh4TKEgrqa9FoBiDc31rztsc0XPsvKvUIwbruj11WbmVF8cjparBoX76ZXA7CPW1YPix2slTJDntOROZk41F0FAvsUr6FWQcCBQg7EZB7prYERUrsN6EYV4mBMTVYtb1tNKBzIDHDAEWjOHgur8k87qpdh-827amGTzLuuwoaY51ncOkbtvygCMqMbi0SEWY7SYZVAtOergGP2lEde4TUzS5PeLS5H_bUfxGHfVpvhUh-5bnUefqjfrnV4WTl4ZsYPJHgDxivMN36TV5dveaMZbrwPNz6EGy2_wZsd1uz6zSFrBg_lHljzE2989Bu8-ZnLSvXHs7k_-NSq938oYxVddpwrOhHfb-Hnqnrlp8lkkleLEsQv5hOt_DQul4unY9E8YqaukrVeJWbgKz_lcrl3MWpjfAMuYxzO6NHyJDuZBPTy41JOLu5CTzXnsmb41OikRGlArVAs5wu7UaOK5oiPc3G3BaBYDuiVTwuFsrILPTBk1Ma6n6CXw_8CeqVSaRdiwgT4tFQqU3l5Em_zcr68CzkRqH0H60IE2RdyEloV_JXDX2f4K4-_CviriL9K-KuMv94yYI7CcLIMKcuwsgwNDBSXvdhUdanakKrwuxpIUwyiId1Kd90c_H8m3fUlfqsh-dc4Er8ZkjpSV7qTetJAGkoP0kfpk_RZiFN8b_ewwvuc1LyX2NNUoJuF__NSX7oPRCaGcy2Jt6nS8gWqVL2RqtcSuAFfLhJMxG_zJP4lnoRf3UnsiztJfLUkiU-RJPbyVlo-3JXYlZPEKmoSy2kl4SJ8qYnP1PkgCQ_lC8K7jJSZ2pqaqbC_E5KZUxt4Ac3MV8R8zLgzyAr5nw0Bnj89Zh6Nb4BjycZn05z7aLbpTWeZykTWHWh5Fn6Rf6XJkFwFILLnmv2FofhtqmqQVN7yP3bC_uYJo5qpfM28Zir5fO64nM2X82_LhbNCFqQys8hUCmfHxbfFXLGYLeXPssX8afGblPnC1nF6XC4VTuHnDFCK2eIZYNjs76PUMJrMVErf_gU2tkvW)

The image is linked to its original file so that the complete diagram can be
opened at full resolution.

Each boundary has a distinct responsibility. Configuration parsing, file
decoding, process management, compiled geometry and PDF serialization do not
become part of the generation business model.

The main successful flow is:

1. resolve and validate effective configuration;
2. load the selected reference palette;
3. load, validate and normalize the input image;
4. resolve Application generation and execution policies;
5. quantize the normalized image to the selected palette;
6. detect and process paintable regions;
7. trace or simplify region outlines;
8. place labels and construct a `VectorDocument`;
9. serialize the document to PDF;
10. write the configured PDF output.

Failure paths leave this normal flow through the project error hierarchy and
are classified by the CLI integration contract.

## Security Principles

Security is a cross-cutting architectural concern rather than a responsibility
of one interface.

[ADR-0002](adr/0002-security-principles.md) defines the general rules. Among
their architectural consequences:

- external input is validated before reaching business logic;
- third-party parsers remain behind Infrastructure boundaries;
- project-owned path construction validates request-controlled identifiers;
- external implementation failures are translated at the boundary where that
  translation is owned;
- required validation and security dependencies fail closed rather than
  silently selecting a less constrained path;
- deployment-level process limits remain outside the generator where defined by
  the untrusted-input and integration contracts.

Detailed vulnerability-reporting guidance and the project's security-support
policy are maintained in [`SECURITY.md`](../SECURITY.md).

Deployment responsibilities for applications processing untrusted input are
documented in
[`integration-contract.md`](integration-contract.md).

## Input Boundary

Normal Application generation cannot receive an arbitrary decoded image object.

Image input passes through the mandatory loading boundary defined by
[ADR-0012](adr/0012-normalized-user-inputs.md) and
[ADR-0016](adr/0016-untrusted-input-boundary.md).

The Infrastructure image loader:

- validates that the input path identifies a supported input file;
- validates the claimed and detected image format;
- restricts accepted formats to BMP, JPEG, PNG and WEBP;
- applies configured width, height and total-pixel acceptance limits before
  unbounded normalized pixel materialization;
- applies decompression-bomb protection using the configured pixel bound;
- calculates the configured processing resolution;
- proportionally reduces accepted images that exceed
  `processing_pixel_count`;
- preserves the image aspect ratio during processing-size reduction;
- handles the narrow JPEG auxiliary-frame exception defined by ADR-0016;
- normalizes accepted data into the project-owned `InputImage` model.

The hard image-acceptance limits and the processing-resolution target have
different purposes.

`maximum_width`, `maximum_height` and `maximum_pixel_count` determine whether
an image is accepted at all. Exceeding one of those bounds causes the input to
be rejected.

`processing_pixel_count` does not reject an otherwise accepted image. Instead,
an accepted image whose pixel count exceeds that target is reduced
proportionally before normalized RGB pixel data is materialized for the
generation pipeline.

Images already at or below the configured processing target retain their
dimensions.

RAW and TIFF are outside the supported input boundary.

The Core therefore receives normalized image data rather than raw files,
decoder metadata or Pillow objects.

### Input Profiles

Trusted local and untrusted operation use the same validation mechanisms and
the same categories of input controls.

Their risk profiles are represented through different configured values rather
than different code paths or disabled validation.

The shipped profiles are:

- [`config/example.toml`](../config/example.toml) for trusted local operation;
- [`config/untrusted.toml`](../config/untrusted.toml) for untrusted operation.

Concrete limit values do not form part of this architecture overview.

Measurements used to evaluate decoding cost and input-size policy are recorded
in
[`input-bound-measurements.md`](input-bound-measurements.md).

Measurements of generation cost under adversarial image structures are
recorded in
[`adversarial-input-measurements.md`](adversarial-input-measurements.md).

The deployment implications of those measurements are documented in
[`integration-contract.md`](integration-contract.md).

## Reference Palettes

Reference palettes are versioned, immutable reference data loaded through
Infrastructure.

Palette identity consists of the palette identifier and palette version. That
identity remains associated with generation and is carried into the resulting
`VectorDocument`.

The architecture for reference palettes is governed by
[ADR-0006](adr/0006-reference-palette-strategy.md) and
[ADR-0007](adr/0007-palette-versioning.md).

The concrete JSON schema, filename convention and versioning rules are
documented in [`palette-format.md`](palette-format.md).

Source provenance and evidence for shipped palette data are maintained
separately under [`reference-data/`](reference-data/).

This keeps palette format and source evidence outside the architecture
overview while preserving the architectural rule that generated documents are
bound to an identifiable immutable palette version.

## Domain Models

Project-owned domain models form the vocabulary shared by generation stages.

Representative models include:

- `InputImage`;
- `QuantizedImage`;
- `RGB`;
- `Palette`;
- `PaletteColor`;
- `Region`;
- `RegionMergeMetrics`;
- `RegionMergeCost`;
- `RegionMergeCandidate`;
- `Outline`;
- `Label`;
- `ImagePlacementGeometry`;
- `PhysicalOutputGeometry`;
- `VectorDocument`.

The domain representation is intentionally independent from third-party APIs.

`VectorDocument` is the format-independent result of Core generation. It
contains generated outlines, labels and palette identity without exposing
ReportLab or PDF-specific objects.

Domain value semantics are governed by
[ADR-0005](adr/0005-value-objects.md) and
[ADR-0008](adr/0008-domain-models.md).

## Physical Output Geometry

Physical output geometry is resolved by the Application layer before PDF
serialization.

The PBN page geometry and palette-legend page geometry are resolved
independently. They may therefore use different page formats and orientations.

`ImagePlacementGeometry` defines the deterministic mapping between the
normalized raster image and the printable PBN page. The configured placement
mode controls how the original aspect ratio is mapped to the available physical
area.

The same mapping is also used to convert the physical
`minimum_region_size_mm` paintability requirement into the pixel-space
`minimum_circle_diameter_px` consumed by Core region processing.

Concrete page, placement and legend configuration is documented in
[`README.md`](../README.md).

## Core Data Representation

Domain values that represent shared observable state are immutable. Changes are
represented by constructing new values rather than mutating existing domain
objects.

Some high-volume Core data uses compact standard-library representations to
avoid unnecessary Python-object overhead while retaining project-owned domain
models at architectural boundaries.

In particular:

- `InputImage` stores normalized RGB pixels in compact byte storage;
- `QuantizedImage` stores one palette index per pixel in compact byte storage;
- region membership uses an immutable packed integer representation.

These are storage and lookup decisions. They do not change color semantics,
region membership, deterministic ordering or generated output.

The binding representation rules are defined by:

- [ADR-0005 - Immutable Value Objects](adr/0005-value-objects.md);
- [ADR-0017 - Compact Pixel Representation](adr/0017-compact-pixel-representation.md);
- [ADR-0018 - Packed Pixel Indices for Region Membership](adr/0018-packed-pixel-indices.md).

Representation-level details belong in those ADRs rather than being duplicated
in this overview.

## Region Processing

Region generation is split into mandatory and optional stages.

The current processing order is:

1. quantize the normalized input to the selected palette;
2. detect connected palette-color regions;
3. apply mandatory paintability merging;
4. verify the paintability invariant;
5. optionally apply cost-based region-complexity reduction;
6. verify the same paintability invariant again.

`minimum_region_size_mm` is resolved once into
`minimum_circle_diameter_px`. The same resolved constraint governs mandatory
and optional processing.

Mandatory paintability merging is handled by `RegionMerger`.

Optional reduction is handled by `RegionComplexityReducer` and is controlled by
the configured region target and merge-cost policy. Optional complexity
settings cannot weaken or replace mandatory paintability.

If mandatory paintability cannot be satisfied because an undersized region
cannot be resolved through a valid neighboring merge, generation fails instead
of silently accepting a region that violates the paintability constraint.

## Quantization and Parallel Execution

Sequential Core quantization remains the reference behavior.

Process-parallel CPU quantization follows
[ADR-0014](adr/0014-parallel-execution-strategy.md).

The Application layer determines whether the parallel quantizer is eligible
according to the validated generation configuration and available execution
dependency.

An eligible parallel quantizer still performs a second runtime decision before
using worker processes. The effective worker count and quantization workload
must justify parallel execution according to the configured break-even policy.

If parallel execution is disabled, ineligible or not worthwhile for the current
workload, quantization uses the sequential reference path.

Concrete process management is supplied by Infrastructure through
`QuantizationExecutorPort`.

Parallel execution must preserve the observable result of sequential
quantization. Results must not depend on worker count, scheduling or task
completion order.

Parallel work is split into deterministic color chunks. Results are associated
with their chunk order and combined deterministically before the final
`QuantizedImage` is reconstructed.

The process boundary uses compact transport data rather than transferring large
collections of domain objects unnecessarily.

Failure after parallel execution has started fails the operation rather than
silently retrying the same work through an unrequested sequential recovery
path.

Detailed descriptions of supported color-distance algorithms are maintained
under [`algorithms/`](algorithms/) rather than in this architecture overview.

## Outline Geometry

Outlines may contain an outer ring and hole rings.

The Core owns:

- outline tracing;
- ring and topology semantics;
- individual outline validity;
- topology-preserving simplification;
- the reference overlap semantics.

Normal pairwise overlap detection uses the compiled geometry implementation
defined by
[ADR-0015](adr/0015-geometry-predicate-acceleration.md).

The concrete Shapely adapter remains in Infrastructure behind
`OverlapDetectorPort`.

The pure Python overlap implementation remains available as the reference
behavior for differential testing and developer diagnostics. It is not a normal
production fallback.

When outline simplification is enabled, overlap detection participates in
preserving valid topology. Geometry-library unavailability or an accelerated
geometry failure is an operational failure rather than a request-level input
error.

## Output Boundary

The supported generated artifact is PDF, as defined by
[ADR-0027](adr/0027-pdf-is-the-only-output.md).

Core generation ends at `VectorDocument`.

PDF serialization is an Infrastructure responsibility behind
`PdfExporterPort`. The exporter receives project-owned document and geometry
models and translates them into the concrete PDF representation.

Palette legends are generated as part of the PDF output.

The CLI writes the returned PDF bytes to the configured output path. A failure
to serialize or write the generated PDF is classified as an operational
failure.

SVG and other document formats are not dormant output options. Adding another
generated format requires an architectural decision.

## Configuration

The project has no hidden generation defaults. ADR-0030 states the rule and
what follows from it.

Effective configuration is assembled from:

- explicit CLI values;
- optional TOML fallback values.

Explicit CLI values take precedence over TOML values.

Configuration handling has two distinct validation concerns.

First, the effective configuration values must be structurally usable. This
includes:

- readable and valid TOML when a configuration file is used;
- valid TOML tables;
- presence of all required effective values;
- expected value types.

Second, the resulting configuration candidate must satisfy the semantic
constraints enforced by `GeneratorConfigValidator`.

A failure in either configuration-validation concern is reported as
`ConfigurationError`.

Configuration loading is an Infrastructure concern. Configuration building,
validation and use-case resolution are Application concerns.

The resulting Core operations receive already validated values and domain
objects instead of reading configuration files themselves.

Concrete configuration options and command-line usage are user-facing concerns
and are documented in [`README.md`](../README.md).

## Determinism and Reproducibility

Deterministic behavior is a project-wide architectural requirement.

Important consequences include:

- stable palette numbering and palette version identity;
- immutable observable domain state;
- deterministic region and merge-candidate ordering;
- explicit tie-breaking;
- sequential and parallel quantization equivalence;
- deterministic parallel work partitioning and result reconstruction;
- reference and accelerated geometry equivalence;
- stable generation semantics independent of worker scheduling;
- project-owned domain models at execution boundaries.

Performance optimizations are retained only when they preserve the reference
behavior required by the relevant architectural boundary.

## Error and Integration Boundaries

Project errors distinguish caller-safe information from diagnostic information.

[ADR-0019](adr/0019-error-disclosure-boundary.md) defines the distinction
between caller-safe public error information, operator diagnostics and
request attribution.

Every project-specific error derives from the project error hierarchy and
carries an attribution describing whether the request caused the failure or
whether the operation or environment caused it.

The CLI derives its exit classification centrally from that attribution rather
than choosing an exit code independently at each failure site.

The supported outcome classifications distinguish:

- successful generation;
- request-caused failure;
- configuration-caused failure;
- operational failure.

The concrete `sysexits` values are shown in the generation-flow diagram and
defined by the CLI integration contract.

The CLI process contract also separates result data on standard output from
progress and operator diagnostics on standard error.

Python callers may use the exception hierarchy directly instead of the process
exit-code contract.

The complete supported process interface, machine-readable result shape and
frontend responsibilities are documented in
[`integration-contract.md`](integration-contract.md).

The generator does not own deployment concerns such as:

- request queues;
- concurrency limits;
- rate limiting;
- wall-clock process limits;
- CPU-time limits;
- address-space or memory limits;
- serving or expiring generated documents.

Those responsibilities belong to the integrating application as defined by the
untrusted-input and CLI integration contracts.

## Repository Responsibilities

The repository follows the responsibility-based structure defined by
[ADR-0011](adr/0011-repository-structure.md).

The primary locations are:

```text
src/          production package
tests/        automated tests and fixtures
docs/         project documentation
docs/adr/     accepted architectural decisions
docs/images/  documentation images and diagrams
config/       shipped configuration profiles
examples/     user-facing examples and generated artifacts
palettes/     versioned reference palette data
tools/        developer-only diagnostics and benchmarks
.github/      repository automation
```

Developer tools remain outside `src/` and production code does not depend on
`tools/`.

The rendered generation-flow diagram used by this document is stored under:

```text
docs/images/generation-data-flow.png
```

The architecture overview references that repository-local image rather than
duplicating the diagram in multiple documentation locations.

## Testing the Architecture

Automated tests are part of the architectural change discipline defined by
[ADR-0004](adr/0004-test-strategy.md).

The test suite verifies behavior including:

- dependency and layer boundaries;
- deterministic ordering and output;
- immutable and compact representation invariants;
- sequential and parallel equivalence;
- reference and accelerated geometry equivalence;
- configuration validation and precedence;
- supported input-format boundaries;
- input-size and processing-resolution behavior;
- error-disclosure and CLI classification behavior.

Performance claims are evaluated through dedicated developer tooling rather
than timing-dependent unit tests.

Dependency vulnerability scanning and major-version compatibility requirements
are governed by
[ADR-0021](adr/0021-dependency-version-bounds.md).

The current measured dependency-security state is recorded separately in
[`dependency-security.md`](dependency-security.md).

## Extension Rules

Changes should extend the existing boundaries rather than bypass them.

In particular:

- new interfaces should call Application use cases instead of duplicating Core
  business logic;
- new external libraries belong in Infrastructure;
- external representations must be normalized before Core use;
- security controls must fail closed;
- request-controlled identifiers used for project-owned paths must remain
  confined to their intended location;
- new execution strategies must preserve deterministic reference behavior;
- changes to shared Core storage representations require review against their
  governing ADRs;
- new generated output formats require an architectural decision;
- reintroducing RAW or TIFF requires an architectural decision;
- changing the mandatory geometry acceleration or its fallback semantics
  requires an architectural decision;
- moving wall-clock, CPU-time or address-space enforcement into the generator
  requires an architectural decision.

## Related Documentation

This overview intentionally delegates detailed or time-sensitive subjects to
more focused documentation:

- [`palette-format.md`](palette-format.md) defines the reference-palette file
  format and versioning conventions;
- [`reference-data/`](reference-data/) records source provenance for shipped
  reference palettes;
- [`algorithms/delta-e-76.md`](algorithms/delta-e-76.md) and
  [`algorithms/delta-e-2000.md`](algorithms/delta-e-2000.md) document the
  supported color-distance algorithms;
- [`algorithms/region-complexity-reduction.md`](algorithms/region-complexity-reduction.md)
  documents the current optional region-complexity reduction algorithm;
- [`region-complexity-calibration.md`](region-complexity-calibration.md)
  records the current calibration basis for optional region-complexity
  reduction;
- [`quantization-quality-evaluation.md`](quantization-quality-evaluation.md)
  records the current evaluation of palette-quantization quality and the
  retained production conclusion;
- [`performance-measurements.md`](performance-measurements.md) records current
  production-performance measurements and benchmark methodology;
- [`geometry-acceleration-evaluation.md`](geometry-acceleration-evaluation.md)
  records the equivalence and performance evidence for accelerated outline
  overlap detection;
- [`input-bound-measurements.md`](input-bound-measurements.md) records measured
  image-decoding and input-bound behavior;
- [`adversarial-input-measurements.md`](adversarial-input-measurements.md)
  records measured generation behavior for adversarial input structures;
- [`integration-contract.md`](integration-contract.md) defines the supported
  frontend/process integration behavior and deployment responsibilities;
- [`dependency-security.md`](dependency-security.md) records the current
  measured dependency-security state;
- [`security-validation.md`](security-validation.md) records the current
  security boundaries and their validation;
- [`SECURITY.md`](../SECURITY.md) defines vulnerability-reporting and security
  support policy;
- [`README.md`](../README.md) documents user-facing installation,
  configuration and command-line usage;
- [`ROADMAP.md`](../ROADMAP.md) tracks planned and remaining implementation
  work;
- [`VISION.md`](../VISION.md) defines the project's long-term direction,
  goals and quality objectives.

## Architectural Sources

The accepted ADRs most directly relevant to this overview are:

- [ADR-0001 - Layered Architecture](adr/0001-layered-architecture.md)
- [ADR-0002 - Security Principles](adr/0002-security-principles.md)
- [ADR-0003 - Dependency Boundaries](adr/0003-dependency-boundaries.md)
- [ADR-0004 - Test Strategy](adr/0004-test-strategy.md)
- [ADR-0005 - Immutable Value Objects](adr/0005-value-objects.md)
- [ADR-0006 - Reference Palette Strategy](adr/0006-reference-palette-strategy.md)
- [ADR-0007 - Palette Versioning](adr/0007-palette-versioning.md)
- [ADR-0008 - Domain Models](adr/0008-domain-models.md)
- [ADR-0009 - Project Documentation](adr/0009-project-documentation.md)
- [ADR-0011 - Repository Structure](adr/0011-repository-structure.md)
- [ADR-0012 - Normalized User Inputs](adr/0012-normalized-user-inputs.md)
- [ADR-0014 - Parallel Execution Strategy](adr/0014-parallel-execution-strategy.md)
- [ADR-0015 - Geometry Predicate Acceleration](adr/0015-geometry-predicate-acceleration.md)
- [ADR-0016 - Untrusted Input Boundary](adr/0016-untrusted-input-boundary.md)
- [ADR-0017 - Compact Pixel Representation](adr/0017-compact-pixel-representation.md)
- [ADR-0018 - Packed Pixel Indices for Region Membership](adr/0018-packed-pixel-indices.md)
- [ADR-0019 - Error Disclosure Boundary](adr/0019-error-disclosure-boundary.md)
- [ADR-0021 - Dependency Version Bounds](adr/0021-dependency-version-bounds.md)
- [ADR-0026 - The Command Line Interface as the Integration Contract](adr/0026-command-line-integration-contract.md)
- [ADR-0027 - PDF Is the Only Output](adr/0027-pdf-is-the-only-output.md)

ADR-0010 and ADR-0013 define repository and project-governance conventions
rather than runtime system architecture and are therefore not summarized here.

For the complete accepted architectural baseline, see
[`docs/adr/INDEX.md`](adr/INDEX.md).