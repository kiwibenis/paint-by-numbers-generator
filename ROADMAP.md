# Paint By Numbers Generator - Roadmap

This roadmap tracks remaining planned implementation work and future project
milestones.

Completed implementation work is not retained here as a historical checklist.
The current architecture and technical behavior are documented under `docs/`
and in the accepted ADRs. Implementation history remains available through Git
history in accordance with
[ADR-0009](docs/adr/0009-project-documentation.md).

The roadmap must remain aligned with the accepted architectural baseline in
[`docs/adr/`](docs/adr/).

---

## Current Technical Documentation

Current implemented behavior and the results behind existing technical
decisions are documented separately from this roadmap.

The primary documents are:

* [`docs/architecture-overview.md`](docs/architecture-overview.md) for the
  current system architecture;
* [`docs/algorithms/region-complexity-reduction.md`](docs/algorithms/region-complexity-reduction.md)
  for optional region-complexity reduction semantics;
* [`docs/region-complexity-calibration.md`](docs/region-complexity-calibration.md)
  for the validated region-complexity policy and quality evidence;
* [`docs/quantization-quality-evaluation.md`](docs/quantization-quality-evaluation.md)
  for the current quantization-quality findings;
* [`docs/performance-measurements.md`](docs/performance-measurements.md) for
  current production performance measurements, accepted performance bounds and
  benchmark methodology;
* [`docs/geometry-acceleration-evaluation.md`](docs/geometry-acceleration-evaluation.md)
  for accelerated overlap-predicate validation and performance evidence;
* [`docs/security-validation.md`](docs/security-validation.md) for current
  security boundaries and their validation;
* [`docs/input-bound-measurements.md`](docs/input-bound-measurements.md) for
  image-input-bound measurements;
* [`docs/adversarial-input-measurements.md`](docs/adversarial-input-measurements.md)
  for adversarial runtime and memory measurements;
* [`docs/dependency-security.md`](docs/dependency-security.md) for the current
  dated dependency-security state;
* [`docs/integration-contract.md`](docs/integration-contract.md) for the
  supported external integration boundary and deployment responsibilities;
* [`docs/palette-format.md`](docs/palette-format.md) for the palette storage
  format: the shape of a document, every field, every bound the loader
  enforces, the file name and the versioning rules;
* [`docs/palette-authoring-guide.md`](docs/palette-authoring-guide.md) for the
  workflow, source requirements and validation rules for adding and maintaining
  reference palettes, which is to say which values belong in those fields;
* [`docs/developer-guide.md`](docs/developer-guide.md) for the local development
  workflow, project validation, ADR lifecycle, repository tooling and commit
  discipline.

---

## Milestone 14 - GPU Acceleration

GPU acceleration is an optional future performance optimization.

The existing sequential CPU implementation remains the reference behavior.
The existing process-based CPU parallelization remains available independently
from GPU support.

GPU acceleration must preserve the project's deterministic and reproducible
generation semantics.

The initial acceleration target is color quantization, with Delta E 2000 as
the primary candidate because its palette-distance calculations provide a
large regular data-parallel workload.

Additional pipeline stages shall only receive GPU implementations when current
profiling and isolated benchmarks demonstrate a meaningful end-to-end benefit.

### Architecture

* [ ] Create an ADR defining the GPU acceleration strategy before introducing
  a concrete GPU implementation.
* [ ] Keep GPU libraries and device-specific APIs outside the Core layer in
  accordance with ADR-0003.
* [ ] Keep quantization semantics and other business rules inside the Core.
* [ ] Define an accelerator boundary that allows GPU implementations to remain
  replaceable Infrastructure.
* [ ] Keep the sequential CPU implementation as the reference behavior and
  mandatory fallback.
* [ ] Preserve the existing process-based CPU parallelization independently
  from GPU acceleration.
* [ ] Define deterministic result ordering and tie-breaking across CPU and GPU
  execution paths.
* [ ] Define numerical-equivalence requirements so GPU floating-point behavior
  cannot silently change palette-color selection.
* [ ] Define GPU initialization and failure semantics without allowing partial
  generation results.
* [ ] Ensure unsupported or unavailable GPU hardware follows an explicitly
  defined execution policy.
* [ ] Keep GPU-specific dependencies optional so normal CPU installations do
  not require a GPU software stack.
* [ ] Preserve cross-platform CPU functionality when no supported GPU backend
  is installed.

### Profiling and Feasibility

* [ ] Re-profile the current complete generation pipeline before implementing
  GPU acceleration.
* [ ] Measure the current end-to-end share of color quantization after the
  existing CPU optimizations and process parallelization.
* [ ] Measure representative Delta E 2000 workloads by unique RGB color count
  and palette size.
* [ ] Measure CPU-to-GPU transfer overhead separately from GPU computation.
* [ ] Measure GPU-to-CPU result-transfer overhead separately from GPU
  computation.
* [ ] Determine whether retaining intermediate quantization data on the GPU can
  reduce transfer overhead without violating architectural boundaries.
* [ ] Build an isolated GPU quantization prototype before integrating GPU
  execution into the generation pipeline.
* [ ] Compare the prototype against sequential CPU quantization.
* [ ] Compare the prototype against the existing process-parallel CPU
  quantization path.
* [ ] Evaluate performance on simple, medium and complex representative images.
* [ ] Reject GPU integration if measured end-to-end improvements do not justify
  the additional dependency and architectural complexity.

### GPU Quantization

* [ ] Define a deterministic GPU work representation for palette matching.
* [ ] Implement GPU execution for eligible color-quantization workloads.
* [ ] Implement Delta E 2000 palette-distance evaluation as the initial GPU
  workload.
* [ ] Preserve the exact palette-number and palette-version semantics of the
  CPU implementation.
* [ ] Preserve deterministic palette-color selection for equivalent inputs.
* [ ] Preserve explicit deterministic tie-breaking when multiple palette
  colors have equivalent or numerically indistinguishable costs.
* [ ] Avoid transferring unnecessary domain data to the GPU.
* [ ] Bound GPU memory usage for large unique-color and palette combinations.
* [ ] Partition workloads deterministically when they exceed available GPU
  memory.
* [ ] Ensure GPU workload partitioning does not change generated results.
* [ ] Add focused equivalence tests comparing GPU results with the sequential
  CPU reference implementation.
* [ ] Add regression tests covering deterministic results across repeated GPU
  executions.
* [ ] Verify equivalent results across sequential CPU, parallel CPU and GPU
  quantization paths.

### Execution Policy and Configuration

* [ ] Define how GPU availability is detected without introducing GPU-specific
  dependencies into the Core.
* [ ] Define configuration semantics for explicitly enabling or disabling GPU
  acceleration.
* [ ] Define the interaction between GPU acceleration and existing parallel
  CPU quantization settings.
* [ ] Define deterministic execution-path selection between sequential CPU,
  parallel CPU and GPU quantization.
* [ ] Determine a system-specific GPU break-even workload through calibration
  rather than a hidden program default.
* [ ] Extend the existing calibration approach to compare sequential CPU,
  parallel CPU and GPU execution.
* [ ] Ensure small workloads remain on the execution path with the lowest
  measured overhead.
* [ ] Ensure missing or unsupported GPU hardware does not prevent normal CPU
  generation when the configured execution policy permits CPU fallback.
* [ ] Add configuration-source parity tests for finalized GPU settings.
* [ ] Add CLI and TOML precedence tests for finalized GPU settings.
* [ ] Document finalized GPU configuration and calibration behavior in
  `README.md`.

### GPU Performance Validation

* [ ] Benchmark GPU quantization on representative simple images.
* [ ] Benchmark GPU quantization on representative medium images.
* [ ] Benchmark GPU quantization on representative complex images.
* [ ] Benchmark GPU quantization with different palette sizes.
* [ ] Measure total GPU memory consumption.
* [ ] Measure host-to-device and device-to-host transfer costs.
* [ ] Compare complete generation runtime between sequential CPU, parallel CPU
  and GPU execution.
* [ ] Determine system-specific GPU break-even workloads.
* [ ] Verify that GPU acceleration provides a meaningful end-to-end performance
  improvement rather than only an isolated kernel speedup.
* [ ] Verify that GPU acceleration does not introduce unacceptable memory or
  initialization overhead.
* [ ] Confirm deterministic and reproducible generated output before enabling
  GPU acceleration for normal generation workflows.

### Further GPU Candidates

* [ ] Re-profile the complete pipeline after GPU quantization has been
  integrated.
* [ ] Identify remaining numerically intensive and data-parallel bottlenecks.
* [ ] Benchmark additional GPU candidates individually before implementation.
* [ ] Add GPU implementations for additional pipeline stages only when measured
  end-to-end performance gains justify their complexity.
