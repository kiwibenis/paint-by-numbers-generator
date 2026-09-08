# Performance Measurements

## Purpose

This document records the current performance characteristics and measurement
methodology of the Paint by Numbers Generator.

It focuses on production-generation performance:

- complete end-to-end generation;
- sequential versus process-parallel quantization;
- quantization calibration;
- process-boundary serialization;
- optional region-complexity reduction.

It intentionally does not contain an optimization history.

Superseded profiles, intermediate implementations and measurements that no
longer describe the current system are not retained here.

Input-decoding limits and adversarial resource behavior are documented
separately because they answer different questions.

## Measurement Principles

Performance measurements are hardware- and runtime-dependent.

Absolute execution times must therefore not be treated as universal project
constants.

Durable conclusions should primarily be based on:

- relative speedup;
- scaling behavior;
- workload thresholds;
- stable bottleneck identification;
- memory or serialization shape;
- deterministic equivalence of compared execution paths.

Ordinary automated tests do not enforce timing thresholds.

Performance claims are measured through dedicated developer tools in accordance
with
[ADR-0004](adr/0004-test-strategy.md).

## Benchmark Boundaries

The project maintains several different benchmark boundaries.

### Complete Generation

```text
tools/benchmark.py
```

measures the complete CLI generation pipeline.

It includes:

- configuration loading;
- image loading;
- palette loading;
- quantization;
- region processing;
- outline generation;
- label placement;
- PDF serialization;
- process startup where parallel quantization is selected.

This is the primary benchmark for determining whether an optimization improves
the actual generator rather than only an isolated function.

### Isolated Quantization Calibration

```text
tools/benchmark_quantization.py
```

measures quantization independently from the rest of generation.

It is used to determine:

- when process-parallel quantization becomes worthwhile;
- how palette size affects the workload;
- how worker count scales on the target system;
- a recommended parallel break-even workload;
- a recommended maximum worker count.

### Worker Serialization

```text
tools/measure_worker_serialization.py
```

measures the data transferred across the spawned quantization-worker boundary.

It is used to verify that process transport remains small relative to the work
being parallelized.

### Region-Complexity Performance

Dedicated region-complexity benchmarks under `tools/` measure:

- isolated optional reduction;
- downstream generation after reduction;
- complete enabled-versus-disabled generation;
- outline and geometry-validation cost where required.

The complete generation comparison is the authoritative performance gate for
optional complexity reduction.

## End-to-End Benchmark Method

The standard complete benchmark covers:

```text
simple_smaller
simple
medium_smaller
medium
complex_smaller
complex
```

The benchmark uses:

```text
palette:
    faberCastellPolychromos60

palette_version:
    1

color_distance:
    delta_e_2000
```

and otherwise starts from:

```text
config/example.toml
```

Each case is executed both:

```text
sequential quantization
parallel quantization
```

For repeated runs, execution order alternates:

```text
run 1:
    sequential
    parallel

run 2:
    parallel
    sequential

run 3:
    sequential
    parallel
```

This reduces systematic bias caused by always running one configuration first.

The reported duration for each path is the median of the measured runs.

Parallel end-to-end speedup is:

```text
speedup =
    median_sequential_seconds
    /
    median_parallel_seconds
```

The benchmark can be run with:

```text
python tools/benchmark.py --runs 3
```

## Performance Must Be Evaluated End to End

An isolated optimization is not sufficient evidence for retaining a production
change.

A faster individual stage can still make complete generation slower because it
may alter:

- downstream region structure;
- process serialization;
- memory pressure;
- outline complexity;
- geometry-validation workload;
- PDF-generation workload.

The project therefore distinguishes:

```text
isolated benchmark
```

from:

```text
complete generation benchmark
```

Isolated measurements identify where time is spent.

End-to-end measurements determine whether a production change is actually
beneficial.

## Parallel Quantization

Quantization is CPU-bound and can operate independently on distinct source RGB
values.

Process-parallel quantization follows
[ADR-0014](adr/0014-parallel-execution-strategy.md).

The sequential quantizer remains the reference behavior.

Parallel execution is eligible only when:

- parallel quantization is enabled;
- the selected color-distance strategy is eligible;
- at least two effective workers are available;
- the estimated workload reaches the configured break-even threshold.

The estimated workload is:

```text
unique_rgb_count
    *
palette_color_count
```

This is a better predictor than image pixel count alone because palette
matching is performed once for every distinct source color against every
palette color.

## System-Specific Quantization Calibration

Parallel-process performance depends strongly on the target system.

Relevant factors include:

- CPU core count;
- process-spawn cost;
- operating system;
- Python runtime;
- memory bandwidth;
- serialization cost;
- palette size;
- number of unique RGB values.

The same parallel policy must therefore not assume that one worker count or
break-even point is optimal on every machine.

Measurements on the same representative quantization workload demonstrate this
difference.

On a two-core environment:

```text
parallel:
    23.83 s

sequential:
    23.58 s
```

The two paths are effectively within measurement noise.

On a machine with more available cores:

```text
parallel:
    8.30 s

sequential:
    15.06 s

speedup:
    1.81x
```

The durable conclusion is not either absolute runtime.

The durable conclusion is:

```text
parallel quantization policy is system-specific
```

A target deployment should therefore calibrate the parallel boundary rather
than copy performance assumptions from another machine.

## Quantization Calibration Method

The calibration tool uses deterministic synthetic work.

Its current calibration case contains:

```text
image:
    1024 x 1024

unique RGB colors:
    16,384

color distance:
    Delta E 2000
```

Palette size is swept across:

```text
8
10
12
...
160
```

colors.

For every calibration point:

```text
estimated_workload =
    unique_rgb_count
    *
    palette_color_count
```

The calibration evaluates sequential execution and available worker counts.

The current recommendation criteria are:

```text
minimum useful parallel speedup:
    1.25x

minimum useful incremental worker speedup:
    1.05x

required stable worker-count points:
    3
```

The tool can be run with:

```text
python tools/benchmark_quantization.py --runs 3 --max-workers 16
```

The reported recommendations are configuration inputs.

The calibration tool does not modify generation configuration automatically.

## Current Shipped Quantization Policy

The shipped trusted and untrusted profiles currently use:

```text
parallel_quantization_enabled:
    true

parallel_quantization_break_even_workload:
    557056

parallel_quantization_max_workers:
    8
```

These values are explicit policy.

They are not Core defaults.

They represent the currently shipped calibration and should be recalibrated
when generation moves to a target system whose hardware or runtime environment
differs materially.

The calibration procedure for users is documented in
[`README.md`](../README.md).

## Compact Quantization Worker Boundary

Parallel quantization communicates through compact byte representations.

One outgoing work item has the shape:

```text
tuple[int, bytes]
```

with:

```text
3 bytes per unique RGB color
```

The result has the same outer shape:

```text
tuple[int, bytes]
```

with:

```text
1 palette index per source color
```

The parent process already owns the palette, so workers do not return
`PaletteColor` domain objects.

This boundary is defined by ADR-0014 and depends on the one-byte
palette-addressability invariant of
[ADR-0017](adr/0017-compact-pixel-representation.md).

## Current Worker-Transport Measurement

On the measured `complex_smaller` case:

```text
unique colors:
    391,374
```

the current compact representation requires approximately:

```text
outgoing RGB data:
    1.17 MB

returned palette indices:
    0.39 MB
```

Measured serialization of the compact transport is approximately:

```text
outgoing dump:
    0.3 ms

returned-index load:
    below 0.1 ms
```

The important current property is that process-boundary serialization is small
relative to the CPU cost of Delta E 2000 palette matching on workloads large
enough to select the parallel path.

The measurement can be reproduced with:

```text
python tools/measure_worker_serialization.py
```

or for another benchmark case:

```text
python tools/measure_worker_serialization.py --case complex --workers 8
```

## Compact Core Representations

High-volume generation data uses compact project-owned representations.

Relevant current invariants include:

- normalized RGB pixels are stored as three bytes per pixel;
- quantized pixels are stored as one palette index per pixel;
- region membership is stored as packed integer indices;
- quantization worker transport uses byte sequences rather than per-color
  domain-object collections.

These representations are defined by:

- [ADR-0017](adr/0017-compact-pixel-representation.md);
- [ADR-0018](adr/0018-packed-pixel-indices.md);
- [ADR-0014](adr/0014-parallel-execution-strategy.md).

Performance-sensitive consumers of packed region membership should operate on
the packed representation directly where practical.

Repeatedly expanding packed membership into coordinate-object collections in a
hot path defeats the purpose of the shared representation and can materially
increase runtime and allocation cost.

Representation changes must preserve generated output and deterministic
behavior.

## Optional Region Complexity Reduction

Optional region complexity reduction introduces additional Core work before
outline generation.

Its complete performance effect cannot be inferred from reducer runtime alone.

Changing the region set can affect downstream work including:

- outline tracing;
- topology-preserving simplification;
- geometry validation;
- label placement;
- PDF serialization.

The performance gate therefore compares complete generation with optional
complexity reduction:

```text
disabled
```

against:

```text
enabled
```

under the same generation policy.

## Complexity-Reduction Performance

The comparison uses three paired runs per configuration with alternating
execution order, the median of each set, and the normal accelerated
production geometry path.

Both outline-simplification settings are measured. Optional reduction changes
the region set that topology-preserving simplification and pairwise overlap
validation operate on, and that cost scales steeply with region count, so the
overhead is not the same question with the stage enabled and disabled.

### Shipped Policy

With `outline_simplification_enabled = false`, as both shipped profiles
configure it:

| Case | Baseline regions | Disabled | Enabled | Overhead | Ratio |
|---|---:|---:|---:|---:|---:|
| simple | 44 | `16.820 s` | `22.039 s` | `+31.03%` | `1.310x` |
| medium | 262 | `48.093 s` | `55.315 s` | `+15.02%` | `1.150x` |
| complex | 890 | `96.309 s` | `121.563 s` | `+26.22%` | `1.262x` |

### With Outline Simplification Enabled

| Case | Baseline regions | Disabled | Enabled | Overhead | Ratio |
|---|---:|---:|---:|---:|---:|
| simple | 44 | `22.231 s` | `24.116 s` | `+8.48%` | `1.085x` |
| medium | 262 | `53.683 s` | `58.946 s` | `+9.80%` | `1.098x` |
| complex | 890 | `101.060 s` | `126.816 s` | `+25.49%` | `1.255x` |

### Interpretation

Enabling simplification lowers the relative overhead, because the stage costs
both configurations while optional reduction gives it fewer regions to work
on. The overhead of optional reduction is therefore bounded by the setting
that disables it, which is the setting the profiles ship.

The mandatory paintability policy is what keeps the overhead in this range.
At `minimum_region_size_mm = 2.0` the complex case enters the optional stage
with `890` regions and leaves it with `488`. A lower paintability baseline
retains several times that many regions, and pairwise overlap validation
becomes the dominant cost well before optional reduction does.

The largest relative figure belongs to the smallest workload. The
`+31.03 percent` on the simple case is `5.219 s` of reducer initialization
spread over three accepted merges rather than a proportional cost, which is
why the percentage falls as the workload grows.

## Accepted Complexity-Reduction Overhead

```text
accepted end-to-end overhead:
    1.5x complete generation

measured maximum:
    1.310x
```

The bound has headroom over normal measurement spread and over a slower
machine.

This is a recorded figure rather than an enforced one. Nothing checks it
automatically.

Its purpose is that a later measurement above it is a documented regression
rather than a matter of opinion.

An automatic check would need a machine-independent metric. Comparing seconds
on rented continuous-integration runners would not provide one, and the
complex case alone costs six complete generations per run.

## Performance and Quality Are Independent Gates

Performance and visual quality must be evaluated separately.

A merge policy may:

- reduce region count;
- preserve acceptable detail;
- still impose excessive runtime cost.

Conversely, a faster policy is not acceptable merely because it improves
runtime if it damages meaningful image structure.

The selected optional-complexity policy therefore has separate:

```text
quality validation
```

and:

```text
performance validation
```

gates.

The current quality calibration is documented in
[`region-complexity-calibration.md`](region-complexity-calibration.md).

## Geometry Acceleration

Normal production overlap validation uses the accelerated geometry path defined
by
[ADR-0015](adr/0015-geometry-predicate-acceleration.md).

Detailed measurements establishing the performance and equivalence of that
decision belong in the dedicated geometry-acceleration evaluation document
rather than being duplicated here.

This document treats the accelerated geometry implementation as the normal
production path for current end-to-end measurements.

## Input and Adversarial Resource Measurements

Image-loading performance and adversarial request-resource behavior are
deliberately documented separately.

For image decoding, input-size limits and unique-color behavior before
generation, see:

- [`input-bound-measurements.md`](input-bound-measurements.md).

For runtime and peak-memory behavior of adversarial generation inputs, see:

- [`adversarial-input-measurements.md`](adversarial-input-measurements.md).

Those documents provide the evidence used to size integration-level resource
controls.

Their measurements should not be duplicated into general generation
performance documentation.

## Dependency Performance

Dependency versions and dependency-security state are also documented
separately.

A dependency upgrade may require performance verification when it affects a
hot production path, but version and vulnerability state belong in:

- [`dependency-security.md`](dependency-security.md).

## Reproduction

The primary current performance tools are:

```text
python tools/benchmark.py --runs 3

python tools/benchmark_quantization.py --runs 3 --max-workers 16

python tools/measure_worker_serialization.py

python -m tools.benchmark_region_complexity_end_to_end --runs 3
```

The last one is run as a module because it imports from a sibling module
under `tools/`. Running it as a script puts `tools/` on the import path
instead of the repository root, and the import fails.

The last of those produces the paired complete-generation comparison
reported above.

It takes its generation policy from `config/example.toml` and restates none
of it. The command line carries only the benchmark parameters: the profile,
the two paths, the palette, the reduction state under test and the region
target derived from each case's own baseline. A recalibrated profile is
therefore measured as recalibrated, without a second copy of its values that
could disagree.

Measuring a different policy, outline simplification included, means
pointing `CONFIG_PATH` at a copy of the profile with that value changed.

The palette is the one deliberate divergence from the profile: the profile
ships `reference8`, which is too small to exercise region complexity, so the
benchmark measures `faberCastellPolychromos120`.

`tests/test_benchmark_region_complexity_end_to_end.py` keeps the command
line to those parameters. The tool previously restated the merge-cost policy
and `minimum_region_size_mm` as constants of its own, and while they said
`1.0 mm` it measured a paintability policy the project does not ship.

More focused developer benchmarks are available under `tools/` for:

- region complexity;
- outline simplification;
- merge metrics;
- candidate tracking;
- geometry validation.

Focused tools are used to explain a measured end-to-end result.

They do not replace the complete-generation benchmark as the final performance
criterion.

## Invalidation Rules

A recorded performance conclusion should be re-evaluated after a material
change to:

- quantization semantics;
- palette matching implementation;
- process transport;
- worker orchestration;
- compact pixel or region representation;
- mandatory paintability processing;
- optional region-complexity reduction;
- outline tracing;
- topology-preserving simplification;
- accelerated geometry predicates;
- label placement;
- PDF serialization;
- supported Python runtime;
- a runtime dependency used in a measured hot path.

System-specific parallel calibration should additionally be repeated after a
material deployment hardware change.

## Current Status

The current performance state is:

```text
complete benchmark:
    available

parallel quantization:
    production-enabled when workload clears the configured gate

current shipped break-even workload:
    557056

current shipped maximum workers:
    8

worker transport:
    compact bytes

geometry overlap validation:
    accelerated production path

optional complexity performance:
    complex-case ratio 1.262x, maximum across cases 1.310x

accepted optional complexity overhead:
    1.5x complete generation
```

## Related Documentation

For architecture, see:

- [`architecture-overview.md`](architecture-overview.md).

For parallel execution semantics, see:

- [`adr/0014-parallel-execution-strategy.md`](adr/0014-parallel-execution-strategy.md).

For compact representations, see:

- [`adr/0017-compact-pixel-representation.md`](adr/0017-compact-pixel-representation.md);
- [`adr/0018-packed-pixel-indices.md`](adr/0018-packed-pixel-indices.md).

For optional region complexity, see:

- [`algorithms/region-complexity-reduction.md`](algorithms/region-complexity-reduction.md);
- [`region-complexity-calibration.md`](region-complexity-calibration.md).

For quantization quality, see:

- [`quantization-quality-evaluation.md`](quantization-quality-evaluation.md).

For input-resource measurements, see:

- [`input-bound-measurements.md`](input-bound-measurements.md);
- [`adversarial-input-measurements.md`](adversarial-input-measurements.md).

For current planned and remaining work, see:

- [`../ROADMAP.md`](../ROADMAP.md).