# Quantization Quality Evaluation

## Purpose

This document records the current quality evaluation of palette quantization.

It documents:

- the production quantization semantics;
- how quantization loss is distinguished from later region-processing loss;
- palette-utilization and collision measurements;
- alternative-palette rescue-cost measurements;
- evaluated spatial and structural diagnostics;
- the cross-image generalization results;
- the reason production quantization remains unchanged.

The diagnostic tooling described here is developer-only.

It does not participate in normal generation and does not change production
quantization behavior.

## Production Quantization Semantics

The production quantizer independently assigns every distinct source RGB color
to the nearest color in the selected reference palette.

The processing model is:

```text
source RGB
    |
    v
CIELAB conversion
    |
    v
distance to each palette color
    |
    v
nearest palette color
```

The configured color-distance strategy determines what "nearest" means.

Supported strategies are:

- Delta E 76;
- Delta E 2000.

The same source RGB value always receives the same palette-color assignment
within one quantization run.

Distinct source RGB values are evaluated independently from their spatial
location or neighboring pixels.

Production quantization does not:

- optimize palette utilization;
- detect semantic objects;
- preserve boundaries explicitly;
- choose a second-best palette color to maintain a local distinction;
- use image segmentation as part of palette assignment.

The production behavior is deterministic.

Sequential and parallel execution must produce equivalent assignments in
accordance with
[ADR-0014](adr/0014-parallel-execution-strategy.md).

## Quality Question

Independent nearest-color assignment is locally optimal with respect to the
configured color-distance metric.

That does not imply that it is globally optimal for preserving image
structure.

Two visibly distinct source colors can both map to the same palette color:

```text
source A ----\
              > palette color X
source B ----/
```

When the two source colors occur on opposite sides of an image boundary, that
boundary disappears from the quantized representation.

Later region-processing stages cannot reconstruct a boundary that no longer
exists in the quantized image.

The quality investigation therefore asks:

```text
Does independent nearest-color assignment remove meaningful source-image
structure that could be preserved at acceptably small additional color cost?
```

## Stage-Loss Attribution

Quality loss must be attributed to the stage that introduces it.

The relevant sequence is:

```text
original input
    |
    v
quantized image
    |
    v
detected regions
    |
    v
mandatory paintability result
    |
    v
optional complexity result
```

The original image is a developer quality reference.

It is not semantic input to later merge-cost decisions.

### Quantization Versus Region Detection

The quantized image and detected-region representation have been verified to be
pixel-equivalent.

Region detection therefore does not alter palette assignments.

It groups connected pixels that already share a palette color.

A distinction absent in the quantized image is already unavailable before
region detection begins.

### Quantization Versus Mandatory Paintability

Quantization and mandatory paintability merging are separate loss mechanisms.

On the simple preservation reference with:

```text
minimum_region_size_mm = 2.0
```

the stage diagnostic measured:

```text
detected_regions = 8224
mandatory_regions = 44
```

The quantized and detected representations remain pixel-equivalent.

Some fine foreground structures, including thin green plant detail, are already
weakened or collapsed by palette assignment.

Mandatory paintability processing independently removes additional regions that
cannot satisfy the configured physical paintability constraint.

Optional-complexity evaluation must therefore not attribute either type of
upstream loss to the optional reducer.

## Diagnostic Scope

The current diagnostic tooling evaluates several different questions:

- how much of the palette is used;
- how many source colors map to each palette color;
- which local source-color boundaries collapse;
- how perceptually different the collapsed source colors are;
- whether alternative palette colors exist at low additional distance;
- whether perceptual source-color grouping produces paintable local
  components;
- whether collapsed distinctions form spatially coherent structures;
- whether collapsed contrast remains visible across increasing spatial
  offsets;
- whether center-surround patterns identify thin structures that disappear
  during quantization;
- whether such signals generalize across different image classes.

The principal diagnostic implementation is:

```text
tools/evaluate_quantization_collisions.py
```

Additional developer tools include:

```text
tools/evaluate_quantization_source_spread.py
tools/evaluate_region_stage_loss.py
```

These tools remain outside `src/`.

Production code does not depend on them.

## Evaluation Configuration

The primary cross-image diagnostic measurements use:

```text
palette:
    faberCastellPolychromos120

palette_version:
    1

color_distance:
    delta_e_2000
```

The principal representative inputs are:

- simple;
- medium;
- complex.

The simple image is a stylized preservation reference.

The medium and complex images provide progressively more photographic texture
and color variation.

This distinction is important because a diagnostic that appears selective on a
stylized image may become indiscriminate on photographic input.

## Palette Utilization

The measured palette utilization is:

| Case | Palette colors | Used colors | Utilization | Distinct source RGB |
|---|---:|---:|---:|---:|
| simple | 120 | 74 | 61.67% | 43,595 |
| medium | 120 | 92 | 76.67% | 306,273 |
| complex | 120 | 107 | 89.17% | 705,290 |

Palette utilization rises substantially with image complexity.

The complex reference uses almost ninety percent of the available palette.

Despite that high utilization, substantial source-color collisions remain.

The current conclusion is therefore:

```text
high palette utilization
    does not imply
structural preservation
```

Palette utilization is useful descriptive information but is not itself a
production quality objective.

The quantizer must not choose additional colors merely to increase the number
of palette entries used.

## Collapsed Local Boundaries

A collapsed boundary occurs when neighboring source pixels have different RGB
values but both quantize to the same palette color.

The measured aggregate collision behavior is:

| Case | Collapsed color pairs | Collapsed boundary length |
|---|---:|---:|
| simple | 159,003 | 1,915,210 px |
| medium | 1,290,102 | 2,407,214 px |
| complex | 1,771,947 | 1,986,631 px |

The raw number of collapsed boundaries is not a direct quality measure.

Photographic gradients, antialiasing and texture naturally contain very large
numbers of distinct neighboring RGB values.

Many of those differences are not meaningful structures that should receive
different paint colors.

A useful production signal therefore has to distinguish intentional local
structure from ordinary continuous photographic variation.

## Source-Color Difference

Collapsed boundaries can be filtered by the configured perceptual distance
between the two original source colors.

On the simple reference, only:

```text
10,499 boundary pixels
```

of the measured collapsed boundary length have a source-color distance greater
than `5.0`.

That is approximately:

```text
0.55%
```

of all collapsed boundary pixels.

Visual inspection shows that many remaining detections still correspond to
ordinary transition edges and antialiasing rather than clearly recoverable
paint-by-numbers structure.

A perceptual source-distance threshold therefore reduces the diagnostic volume
but does not by itself create a sufficiently selective production rule.

## Ranked Alternative Palette Candidates

For each source color, diagnostics can rank not only the nearest palette color
but also alternative palette candidates.

For an alternative candidate:

```text
additional_distance =
    alternative_distance
    - nearest_distance
```

A small value means that the source color could be mapped to another palette
color with only a small increase in configured color error.

This allows the diagnostics to distinguish:

```text
nearest candidate clearly superior
```

from:

```text
multiple nearly equivalent palette candidates
```

## Rescue Cost

A collapsed boundary is potentially rescuable when one side can use a
different palette color at low additional color-distance cost.

On the simple reference, among the collapsed boundary pixels whose source-color
distance exceeds `5.0`, an alternative assignment with additional distance at
most `5.0` exists for:

```text
10,118 of 10,499 boundary pixels
```

or approximately:

```text
96.37%
```

On the complex reference, the diagnostics measured:

```text
meaningful_collisions = 381,615
meaningful_boundary_px = 382,099

rescue_cost_le_5 = 369,829
rescue_cost_le_5_boundary_px = 370,305
```

Approximately:

```text
96.91%
```

of those meaningful complex collisions and boundary pixels have an alternative
palette candidate within the same additional-distance range.

This establishes an important property of the palette:

```text
near-equivalent alternative colors are often available
```

It does not establish:

```text
which local structures should use those alternatives
```

Low rescue cost measures palette capacity.

It does not identify structural importance.

## Why Rescue Cost Is Not a Production Rule

A production reassignment rule based only on low additional distance would
alter large numbers of ordinary photographic transitions.

The same low-cost alternatives occur in:

- important thin structures;
- gradients;
- texture;
- antialiasing;
- ordinary contours;
- local noise.

The diagnostic therefore cannot safely infer:

```text
low rescue cost
    means
choose the alternative palette color
```

No generally acceptable additional color-distance threshold has been
established for production reassignment.

Values such as `5.0` remain diagnostic thresholds, not generation policy.

## Source-Color Clustering

A diagnostic groups source colors around fixed perceptual representatives.

At a Delta E grouping threshold of `5.0`, the measured source-cluster counts
include:

```text
simple:
    216 source clusters

medium:
    529 source clusters
```

Local connected source components can then be evaluated against the physical
paintability constraint.

The measured unpaintable pixel fractions are:

```text
simple:
    0.020917

medium:
    0.320455

complex:
    0.788958
```

For the complex reference, the diagnostic measured:

```text
local_components = 398,137
paintable_components = 127
unpaintable_components = 398,010
```

The fraction of pixels classified into unpaintable components therefore rises
dramatically with photographic complexity.

The method fragments normal photographic gradients and texture into very large
numbers of local perceptual components.

The current conclusion is:

```text
fixed-representative perceptual source clustering
    is not a general production segmentation rule
```

It remains useful only as diagnostic instrumentation.

## Offset Collision Diagnostics

Collapsed source contrast was also evaluated across spatial offsets rather than
only between immediately adjacent pixels.

Offsets allow diagnostics to ask whether two source areas that remain
perceptually distinct over a wider distance still collapse to one palette
color.

The evaluated offsets include:

```text
2 px
4 px
8 px
```

Increasing the offset broadens the detections around:

- normal contours;
- gradients;
- antialiasing;
- photographic texture.

The signal does not become selectively concentrated on missing thin structures.

Direct offset collisions are therefore not used as a production palette
assignment rule.

## Spatial Boundary Components

Meaningful collapsed raster edges can be grouped into spatially connected
boundary components.

This provides more geometric context than an aggregate collision count.

The diagnostics can measure:

- component extent;
- source-color-distance range;
- rescue-cost range;
- dominant palette assignment;
- incident source pixels.

This representation is useful for visual investigation.

On photographic inputs, however, the components still occur broadly across
ordinary image texture and contours.

Spatial connectedness alone does not distinguish intentional paint-by-numbers
structure from normal photographic variation.

## Center-Surround Diagnostic

A center-surround diagnostic targets a more specific structural pattern.

For a candidate:

- two pixels on opposite sides of a center pixel must be perceptually similar
  to each other;
- the center must differ perceptually from both;
- all three must nevertheless quantize to the same palette color.

Conceptually:

```text
background A
     |
     v
  center
     |
     v
background B
```

with:

```text
background A ~= background B

center != background A
center != background B

quantized(background A)
    =
quantized(center)
    =
quantized(background B)
```

This pattern can identify thin source structures that disappear into a
surrounding color.

## Multiscale Persistence

Center-surround detections are evaluated at several offsets.

A center is considered persistent when it is detected at multiple spatial
scales.

The current measurements are:

| Case | Persistent centers | Supported by 2 offsets | Supported by 3 offsets |
|---|---:|---:|---:|
| simple | 553 | 458 | 95 |
| medium | 12,815 | 11,172 | 1,643 |
| complex | 21,212 | 18,448 | 2,764 |

On the simple preservation reference, the persistent preview highlights many
fine foreground structures such as:

- plant stems;
- grass tufts;
- other thin details.

This demonstrates that the diagnostic can identify real lost structure in a
stylized image.

The same unchanged diagnostic expands dramatically on medium and complex
photographic inputs.

There it appears broadly across:

- grass;
- water;
- rock;
- mountains;
- trees;
- reflections;
- shoreline vegetation;
- ordinary photographic texture.

The diagnostic therefore does not generalize into a selective production rule.

## Cross-Image Generalization Result

The central result of the evaluation is not that quantization loss does not
exist.

Quantization demonstrably removes some useful source distinctions.

The central result is that the evaluated diagnostics do not reliably
distinguish those useful distinctions from normal photographic variation
across different image classes.

The observed pattern is consistent across:

- fixed source clustering;
- local component paintability;
- collapsed raster boundaries;
- offset collisions;
- spatial boundary components;
- alternative rescue cost;
- center-surround detection;
- multiscale center-surround persistence.

Signals that are selective on the stylized preservation reference become
increasingly dense over ordinary texture as photographic complexity rises.

## Current Findings

The current evidence supports the following conclusions:

- palette quantization contributes to the loss of some thin source-image
  details;
- mandatory paintability merging independently removes additional regions;
- region detection itself preserves the quantized pixel representation;
- high palette utilization does not prevent structurally relevant
  quantization collisions;
- low alternative rescue cost is common;
- low rescue cost describes palette capacity rather than structural
  importance;
- palette utilization is not a useful production optimization objective;
- fixed source clustering does not generalize to photographic input;
- local component paintability does not provide a selective quantization rule;
- direct and offset collision signals expand across ordinary contours,
  gradients and texture;
- spatial collapsed-boundary components remain too broad on photographic
  input;
- center-surround persistence can identify useful thin structures on stylized
  input but expands into ordinary photographic texture on more complex input;
- no evaluated diagnostic currently provides a sufficiently selective
  cross-image rule for alternative palette assignment.

## Production Decision

Production quantization remains independent nearest-palette-color assignment.

No collision-aware or structure-preserving reassignment is currently enabled.

This is not because the diagnostics show that the existing quantizer preserves
all useful structure.

They do not.

The reason is that the available evidence does not provide a deterministic,
general and selective rule that improves structural preservation without also
reassigning large amounts of normal photographic texture.

Changing production quantization without such a rule would replace a
well-defined nearest-color objective with an inadequately validated heuristic.

The current production behavior therefore remains the reference.

## Requirements for a Future Quantization Change

A future structure-preserving quantization strategy would require new evidence.

Any production change must:

- preserve deterministic results;
- retain the configured color-distance semantics as the basis for color
  fidelity;
- demonstrate cross-image selectivity rather than success on one stylized
  image;
- avoid optimizing palette utilization for its own sake;
- distinguish meaningful structural preservation from ordinary texture,
  gradients and antialiasing;
- preserve sequential and parallel equivalence under ADR-0014;
- re-run stage-loss diagnostics;
- re-establish region baselines affected by the changed quantization;
- re-evaluate region-complexity calibration when the new quantization changes
  the mandatory region distribution materially.

Semantic object recognition is not required by the current architecture.

Any structural strategy should be based on deterministic image-local
information unless a separate architectural decision establishes otherwise.

## Relationship to Region Complexity Calibration

Optional region complexity reduction operates after quantization.

Its calibration therefore depends on the region structure produced by the
production quantizer.

The current region-complexity calibration is documented in:

- [`region-complexity-calibration.md`](region-complexity-calibration.md).

If quantization semantics change materially, the existing merge-cost
calibration cannot automatically be assumed to remain valid.

The resulting region distribution, paintability baseline and optional
merge-candidate distribution must be re-evaluated.

## Developer Tooling Boundary

All quantization-quality diagnostics remain developer tooling under:

```text
tools/
```

They are not imported by production source under:

```text
src/
```

This separation is intentional.

Diagnostic runtime and diagnostic memory consumption are not part of normal
generation performance.

The diagnostic tools may calculate additional candidates, spatial structures
or source-color statistics that production generation never computes.

## Related Documentation

For production color-distance semantics, see:

- [`algorithms/delta-e-76.md`](algorithms/delta-e-76.md);
- [`algorithms/delta-e-2000.md`](algorithms/delta-e-2000.md).

For region-complexity calibration, see:

- [`region-complexity-calibration.md`](region-complexity-calibration.md).

For optional reduction semantics, see:

- [`algorithms/region-complexity-reduction.md`](algorithms/region-complexity-reduction.md).

For the surrounding architecture, see:

- [`architecture-overview.md`](architecture-overview.md).

For parallel quantization architecture, see:

- [`adr/0014-parallel-execution-strategy.md`](adr/0014-parallel-execution-strategy.md).

For current planned and remaining work, see:

- [`../ROADMAP.md`](../ROADMAP.md).