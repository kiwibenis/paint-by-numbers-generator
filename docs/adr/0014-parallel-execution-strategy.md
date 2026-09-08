# ADR-0014 - Parallel Execution Strategy

## Status

Accepted

## Context

Several generation stages are CPU-bound and can contain independent work that
can execute concurrently.

The project targets Python 3.12 and 3.13. On the interpreter builds it
supports, Python-level CPU-bound work does not reliably gain multi-core
execution from threads because of the Global Interpreter Lock.

Parallel execution introduces additional architectural concerns:

- execution order may become nondeterministic;
- process communication introduces serialization overhead;
- worker processes increase memory consumption;
- worker failures must not produce partial results;
- process behavior must remain portable across supported platforms;
- parallel execution must not move business logic outside the Core.

The project must remain deterministic, reproducible, testable and
cross-platform while allowing measured multi-core performance improvements.

Process communication is itself part of the performance boundary.
Transferring large collections of domain objects between processes can make
serialization cost significant relative to the work being parallelized.

Quantization is particularly sensitive to that cost because its independent
work units contain large collections of unique RGB values while the result for
each value only needs to identify one color in a palette already known to the
parent process.

ADR-0017 defines the compact one-byte palette-index representation used by
`QuantizedImage`. The same palette-addressability invariant is relevant when
quantization results cross a process boundary.

## Decision

CPU-bound parallel execution shall use separate worker processes rather than
threads.

Threads are not the default execution strategy for Python-level CPU-bound Core
work.

The Core shall remain independently executable without creating or managing
worker processes. It shall expose deterministic operations that can be
executed sequentially or partitioned into independent work units where
appropriate.

The Application layer owns parallel-execution orchestration. It decides
whether eligible work is executed sequentially or through a parallel execution
boundary.

Concrete process-management mechanics shall remain outside the Core. They may
be provided through an Application port with an Infrastructure implementation,
following ADR-0003.

Parallel execution shall preserve the observable behavior of the sequential
implementation.

Generated results shall not depend on:

- worker scheduling;
- task completion order;
- worker count;
- operating-system process scheduling.

Result assembly shall preserve the canonical ordering and tie-breaking rules
defined by the sequential implementation.

The sequential implementation remains the reference behavior and shall remain
available when parallel execution is not selected.

Parallel execution shall only be selected when the estimated workload is large
enough to justify process startup, serialization and result-assembly overhead.

If fewer than two effective workers are available, execution shall remain
sequential.

Worker count is an execution concern rather than generation semantics.

The effective worker count shall be bounded by:

- the configured maximum;
- available CPU resources;
- the number of independent work units.

The default execution policy shall not intentionally oversubscribe available
CPU resources.

Parallel work submission shall be coarse-grained and bounded. The
implementation shall not create unbounded queues of fine-grained tasks.

Large domain objects shall not be duplicated between worker processes when a
smaller immutable transport representation is sufficient.

### Quantization Worker Boundary

Parallel quantization shall use a compact transport representation.

A quantization chunk shall have the shape:

`tuple[int, bytes]`

The integer identifies the chunk.

The byte sequence contains the chunk's colors in their canonical order, using
exactly three bytes per color in red, green and blue order.

A quantization result shall also have the shape:

`tuple[int, bytes]`

The integer identifies the corresponding chunk.

The byte sequence contains one palette index for each color in that chunk, in
the same order as the input colors.

The palette index addresses `Palette.colors` of the palette supplied by the
parent process.

`PaletteColor` objects shall not be transported back from quantization workers.
The parent already owns the palette and shall resolve returned indices against
that palette.

Packing the outgoing quantization work belongs to the Application
orchestration boundary.

Unpacking colors and packing result indices inside the worker belongs to the
Infrastructure process-execution implementation.

Resolving returned palette indices belongs to the Application orchestration
boundary.

The Core quantization implementation shall continue to use the domain
vocabulary of `RGB`, `PaletteColor` and `Palette`. Transport compaction shall
not leak into the Core quantization API.

The quantization worker boundary depends on the one-byte palette-addressability
invariant defined by ADR-0017.

A palette that cannot be addressed by one byte shall be rejected before
parallel quantization work begins.

The compact transport representation shall not change:

- color matching;
- palette selection;
- deterministic ordering;
- quantization semantics;
- generated output.

Changing the quantization process-boundary representation or widening its
palette index beyond one byte requires an architectural decision.

### Failure and Platform Semantics

If parallel execution cannot be initialized before work begins, the
Application may use the sequential implementation.

Once parallel work has started, a worker failure shall fail the overall
operation.

Partial results shall not be returned.

A worker failure shall not be silently hidden by rerunning the operation
sequentially.

Outstanding parallel work should be cancelled when practical after a worker
failure.

Exceptions shall be propagated or translated according to the project
exception policy.

Parallel execution shall not rely on process-fork behavior.

Worker entry points and transferred values must support process creation
semantics used on all supported platforms, including Windows.

Each parallelized generation stage shall be benchmarked against its sequential
implementation.

A parallel implementation shall only be retained when it provides a meaningful
end-to-end performance benefit without unacceptable memory or complexity
costs.

Time-sensitive measurements belong in benchmark, roadmap or other supporting
documentation rather than in this ADR.

## Consequences

CPU-bound generation work can use multiple CPU cores while the Core remains
independent from process-management infrastructure.

Sequential and parallel execution share the same deterministic business
behavior.

The sequential path remains available for small workloads, limited runtime
environments and performance comparison.

Cross-platform process execution requires worker entry points and transferred
values to remain serializable and independent from fork-specific state.

Parallel execution adds process startup, serialization, synchronization and
memory overhead.

The compact quantization boundary substantially reduces the amount of
per-color object state that must be serialized between processes.

Quantization workers receive RGB values as compact bytes and return palette
indices rather than copies of palette domain objects.

The transport representation is less self-describing than a tuple of domain
objects, so its byte layout is an explicit part of the Application port
contract.

The one-byte result representation makes the palette-addressability bound
shared by `QuantizedImage` and the quantization process boundary.

Some generation stages may remain sequential when measurement shows that
parallel execution would not provide a meaningful benefit.

Parallelization can be introduced incrementally for other independent work
without changing generation semantics, provided the same determinism,
boundary, failure and measurement rules are preserved.