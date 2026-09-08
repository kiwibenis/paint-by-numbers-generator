# Region Complexity Calibration

## Purpose

This document records the current calibration basis for optional region
complexity reduction.

It documents:

- the currently evaluated merge-cost policy;
- the calibration methodology;
- the representative image classes used for cross-image validation;
- measured region-count behavior;
- the rationale for the current `maximum_merge_cost`;
- the fragile-detail validation that supports it;
- the relationship between optional complexity reduction and mandatory
  paintability;
- the conditions that require recalibration.

It does not describe the implementation of the reducer itself.

The current reduction algorithm is documented in
[`algorithms/region-complexity-reduction.md`](algorithms/region-complexity-reduction.md).

This document records the current state only. Experimental configurations and
superseded intermediate evaluations are intentionally not retained here.

## Current Evaluated Policy

The current evaluated region-complexity policy is:

```toml
[generation]

region_complexity_reduction_enabled = true
max_regions = 350
maximum_merge_cost = 0.300

merge_cost_color_weight = 0.40
merge_cost_affected_area_weight = 0.25
merge_cost_border_weight = 0.15
merge_cost_geometry_weight = 0.20

merge_cost_enclosure_strength = 0.50
merge_cost_compactness_strength = 0.15

minimum_region_size_mm = 2.0
color_distance = "delta_e_2000"
```

These values are present in the shipped trusted and untrusted configuration
profiles.

They are configuration policy rather than hidden Core defaults.

The policy has two independent stopping mechanisms:

- `max_regions` is the desired upper region-count target;
- `maximum_merge_cost` is the quality boundary.

The reducer stops as soon as either condition prevents further reduction.

Consequently, the configured `max_regions = 350` does not imply that every
image should contain 350 regions after optional complexity reduction.

Images whose mandatory baseline already contains at most 350 regions are not
reduced further by the optional stage.

Images above that target may still finish above 350 regions when the next
available candidate exceeds `maximum_merge_cost`.

## Calibration Objective

The purpose of calibration is not to select a threshold that removes a fixed
percentage of regions.

The intended semantic relationship is:

```text
lower merge cost
    means lower expected structural damage

higher merge cost
    means increasingly uncertain or destructive simplification
```

A global quality boundary should therefore be allowed to produce different
region-count reductions on different images.

An image containing many visually redundant or low-risk merge candidates may
be simplified substantially.

An image containing mostly structurally important regions may accept few or no
optional merges.

That difference is expected and desirable.

## Calibration Boundary

Calibration of `maximum_merge_cost` must measure the quality boundary rather
than the region-count target.

The calibration runs therefore use a region-count target that is low enough
not to become the active stop condition during the evaluated threshold range.

A calibration run is useful for threshold selection only when reduction stops
because:

- the next available candidate exceeds the quality boundary; or
- no acceptable candidate remains.

A run stopped by `max_regions` does not establish the behavior of the
merge-cost boundary beyond that point.

This calibration methodology is separate from the shipped
`max_regions = 350` policy.

## Calibration Configuration

The current cross-image calibration uses:

```text
palette:
    faberCastellPolychromos120

palette_version:
    1

color_distance:
    delta_e_2000

minimum_region_size_mm:
    2.0

merge-cost weights:
    color          0.40
    affected area  0.25
    border         0.15
    geometry       0.20

detail protection:
    enclosure      0.50
    compactness    0.15
```

The evaluated merge-cost boundaries are:

```text
0.200
0.250
0.300
0.350
```

The region set after quantization, detection and mandatory paintability
processing is the baseline for optional-complexity evaluation.

## Representative Image Classes

Cross-image calibration uses a deliberately diverse set of image structures.

The current evaluation set contains:

- animal imagery with fine texture;
- architecture with narrow frames and repeated geometry;
- a geometric object with clear boundaries;
- a flat illustration;
- a landscape containing gradients and natural boundaries;
- plants containing thin organic structures;
- a portrait;
- a highly textured photographic scene.

The purpose of this set is to expose substantially different distributions of
region size, shape, color difference, boundary structure and texture.

The calibration set is not intended to represent every possible user image.

It is intended to prevent threshold selection from being optimized around one
specific image structure.

## Mandatory Baselines

The baseline for each case is the region count after mandatory paintability
processing with:

```text
minimum_region_size_mm = 2.0
```

The current mandatory baselines are:

| Case | Mandatory regions |
|---|---:|
| animal | 660 |
| architecture | 690 |
| geometric object | 101 |
| illustration | 714 |
| landscape | 439 |
| plants | 1150 |
| portrait | 148 |
| texture | 1099 |

Optional reduction is measured from these baselines.

The original source-image region structure is not the denominator for optional
complexity reduction because quantization and mandatory paintability have
already changed the region representation before the optional reducer begins.

## Cross-Image Region-Count Results

The measured reduction from the mandatory baseline is:

| Case | `0.200` | `0.250` | `0.300` | `0.350` |
|---|---:|---:|---:|---:|
| animal | 21.52% | 30.76% | 35.30% | 41.97% |
| architecture | 23.62% | 30.29% | 32.90% | 35.80% |
| geometric object | 11.88% | 12.87% | 12.87% | 14.85% |
| illustration | 10.92% | 18.77% | 24.51% | 26.61% |
| landscape | 13.67% | 20.73% | 25.28% | 29.38% |
| plants | 14.87% | 24.52% | 30.35% | 33.74% |
| portrait | 6.08% | 10.14% | 13.51% | 18.92% |
| texture | 33.30% | 40.95% | 44.77% | 47.59% |
| **Median** | **14.27%** | **22.62%** | **27.82%** | **31.56%** |

All evaluated cases stopped at the quality boundary or because no acceptable
candidate remained.

The region-count target did not force additional merges in this series.

This confirms that the measured values describe the merge-cost boundary rather
than a region-count target.

## Interpretation of the Cross-Image Results

The results intentionally differ substantially by image class.

At `maximum_merge_cost = 0.300`:

- the portrait is reduced by 13.51%;
- the geometric object is reduced by 12.87%;
- the architecture case is reduced by 32.90%;
- the animal case is reduced by 35.30%;
- the texture case is reduced by 44.77%.

This variation is not evidence of inconsistent behavior.

It demonstrates that the cost model reacts to the available candidate
distribution rather than enforcing a common reduction percentage.

Highly textured images may contain many redundant or inexpensive merge
opportunities.

Images dominated by discrete geometric or facial structure can reach their
quality boundary much earlier.

## Current Maximum Merge Cost

The shipped quality boundary is:

```text
maximum_merge_cost = 0.300
```

Two independent lines of evidence support this value: the cross-image
region-count behavior below, and the fragile-detail validation recorded
further down.

The median reduction progression is:

```text
0.200 -> 14.27%
0.250 -> 22.62%
0.300 -> 27.82%
0.350 -> 31.56%
```

The median incremental gain is therefore:

```text
0.200 -> 0.250
    +8.35 percentage points

0.250 -> 0.300
    +5.20 percentage points

0.300 -> 0.350
    +3.74 percentage points
```

The curve remains monotonic and smooth.

There is no measured discontinuity that identifies another threshold as a
clearly superior global boundary.

The additional region-count reduction obtained above `0.300` also diminishes
relative to the preceding interval.

`0.300` therefore sits at the balance between useful optional simplification
and increasing merge risk.

This conclusion is specific to the current merge-cost formulation and
calibration conditions described in this document.

## Mandatory Paintability Policy

The current shipped paintability policy is:

```text
minimum_region_size_mm = 2.0
```

This value is a mandatory generation constraint and applies independently from
optional region-complexity reduction.

It specifies the minimum physical diameter of a circle that must fit completely
inside a region.

The same resolved constraint is used before and during optional complexity
reduction.

### Label-Space Requirement

Region numbers are rendered inside the paintable regions.

Their size comes from the shipped output configuration:

```text
font_size_pt = 3
```

Their typeface does not. The region-label font is fixed in the PDF exporter
as `Helvetica` and is not a configuration value. Only the palette legend has
configurable fonts, through `entry_font_name` and `entry_number_font_name`.

Measured label dimensions at that size in `Helvetica` are approximately:

```text
one digit:
    width 0.588 mm

two digits:
    width 1.177 mm

three digits:
    width 1.765 mm

digit height:
    0.760 mm
```

Reference palettes may require two- or three-digit region numbers.

The paintability constraint must therefore reserve enough physical space for
the label as well as for manual painting.

`2.0 mm` is the current shipped minimum because it accommodates the current
numbering requirements while preserving the meaning of
`minimum_region_size_mm` as a physical paintability guarantee.

Optional complexity calibration must use the same paintability policy as the
generation policy whose behavior it is intended to support.

## Quality Evaluation Baseline

Optional-complexity quality must be evaluated against the state that actually
enters the reducer.

The relevant pipeline stages are:

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

The mandatory paintability result is the direct baseline for judging optional
complexity reduction.

The original image remains useful as a developer visual reference, but losses
must be attributed to the stage that introduced them.

A structure already absent after quantization must not be classified as damage
caused by optional merging.

A region already removed by mandatory paintability processing must likewise
not be attributed to the optional reducer.

This distinction is required when tuning or validating the optional
merge-cost policy.

## Region Detection

The detected-region representation is expected to preserve the quantized pixel
representation.

Region detection groups connected pixels that already share a palette color.

It does not restore or reinterpret distinctions removed during quantization.

Quality loss visible before region detection is therefore an upstream
quantization concern rather than an optional-complexity concern.

## Preservation References

Some images contain little visually redundant region structure.

For those images, preservation is more important than reducing region count.

A valid optional-complexity result may therefore be:

```text
baseline_regions = N
final_regions = N
```

Zero optional merges must remain an acceptable result.

The simple stylized reference image is treated primarily as a preservation
reference rather than as evidence that a particular amount of simplification
is desirable.

It is useful for detecting whether small intentional structures are being
removed by the optional reducer.

## Visual Quality Criteria

Region-count reduction is not a direct measure of visual quality.

Changed-pixel fraction is also insufficient on its own.

A large number of changed pixels can result from simplifying broad homogeneous
or gradually varying areas without removing important high-level structure.

Conversely, a small merge can remove a narrow but visually important feature.

Quality evaluation therefore distinguishes between:

- removal of meaningful structural boundaries;
- removal of isolated high-contrast motifs;
- damage to narrow or line-like structures;
- damage to architectural surrounds and repeated geometry;
- damage to small organic structures;
- simplification of broad visually redundant regions;
- simplification of gradients or ordinary texture.

The purpose of the merge-cost model is to rank broadly acceptable
simplifications ahead of structurally destructive candidates.

## Fragile-Detail Validation

Region-count behavior alone does not establish that the shipped boundary
preserves the structures listed above. This section records the measurement
that does.

### Reference Selection

References are derived from the mandatory-merge baseline at the shipped
`minimum_region_size_mm = 2.0` rather than listed by hand.

Derivation is what makes the attribution rule enforceable. A structure that
quantization, region detection or mandatory paintability already removed is
absent from that baseline, so it cannot enter the measurement and cannot be
charged to the optional reducer.

A baseline region is a fragile-detail reference when it is:

```text
small:
    area at most three minimum-circle areas

or thin:
    isoperimetric ratio at most 0.30
```

and in either case:

```text
at least dE 5 from its nearest neighbor
```

A disc has an isoperimetric ratio of `1.0` and a square about `0.79`, so
`0.30` describes an elongated or ragged shape. `dE 5` is well above the
distances the shipped palettes themselves treat as two distinct colors.

The two rules instantiate the structure classes above. Narrow architectural
surrounds are thin by construction; small organic structures and isolated
high-contrast motifs are small and locally distinct.

### Result

Measured across the diverse evaluation set under the shipped policy,
`faberCastellPolychromos120`, Delta-E 2000, `maximum_merge_cost = 0.300` and
a `0.50` target fraction:

| Case | Baseline | Reduced | Merges | References | Destroyed |
|---|---:|---:|---:|---:|---:|
| animal | 660 | 427 | 233 | 214 | 0 |
| architecture | 690 | 463 | 227 | 184 | 0 |
| geometric object | 101 | 88 | 13 | 61 | 0 |
| illustration | 714 | 539 | 175 | 251 | 0 |
| landscape | 439 | 328 | 111 | 195 | 0 |
| plants | 1150 | 801 | 349 | 363 | 0 |
| portrait | 148 | 128 | 20 | 88 | 0 |
| texture | 1099 | 607 | 492 | 243 | 0 |

```text
accepted merges:
    1620

fragile-detail references in the baselines:
    1599

references removed by the optional reducer:
    0
```

### Ranking

The requirement that acceptable simplifications rank ahead of destructive
merges holds quantitatively.

```text
merges joining two regions that already carry the same palette color:
    1589 of 1620, 98.1 percent
```

Those merges are structural consolidation with no color loss at all.

The remaining `31` merges change color, and they sit at the top of the
accepted cost range. On the animal case:

```text
same-color merges:
    n = 227, min 0.0576, median 0.1729, max 0.2999

color-changing merges:
    n = 6, min 0.2332, median 0.2822, max 0.2955
```

The color-changing merges begin above the same-color median and cluster
against the `0.300` boundary. The same relationship holds in every case that
contains both classes.

### Threshold Sensitivity

The result is a property of `0.300` rather than of a selection rule that
cannot detect anything. Raising the boundary destroys references immediately:

| Boundary | portrait, 88 references | landscape, 195 references |
|---|---:|---:|
| `0.300` | 0 destroyed | 0 destroyed |
| `0.400` | 23 destroyed | 33 destroyed |
| `0.500` | 36 destroyed | 78 destroyed |

Above `0.500` both cases stop at `max_regions` rather than at the quality
boundary, so further destruction is bounded by the region target rather than
by merge cost.

This is the strongest single argument for the shipped value. `0.300` is not
merely the point where region-count gains diminish; it is below the boundary
at which fragile-detail destruction begins.

### Geometry

Raw traced outlines before and after optional reduction:

| Case | Regions | Holes | Vertices | Max vertices | Max box |
|---|---:|---:|---:|---:|---:|
| simple, mandatory | 44 | 19 | 41916 | 10212 | 1118208 |
| simple, reduced | 41 | 21 | 41712 | 10212 | 1118208 |
| medium, mandatory | 262 | 14 | 127244 | 6026 | 351505 |
| medium, reduced | 172 | 17 | 101608 | 7586 | 431504 |
| complex, mandatory | 890 | 22 | 226940 | 6988 | 462636 |
| complex, reduced | 488 | 43 | 183246 | 18324 | 941850 |

Represented pixels are identical before and after in every case, so nothing
is lost, only redistributed.

In aggregate the geometry becomes simpler: total outline vertices fall by up
to `20 percent`.

Individual regions become more complex. On the complex case hole count
doubles and the largest per-region outline grows from `6988` to `18324`
vertices.

That matters because topology-preserving simplification and pairwise overlap
validation scale with both region count and per-region complexity. The
degradation is bounded here because the reduction lowers the region count at
the same time, and the paired measurement in
[`performance-measurements.md`](performance-measurements.md) confirms it:
enabling outline simplification leaves the complex overhead at `1.255x`
against `1.262x` without it.

The geometry effect is therefore real, measured and acceptable.

## Relationship to `max_regions`

The shipped configuration currently uses:

```text
max_regions = 350
```

This value is not part of the `maximum_merge_cost` calibration itself.

The two settings answer different questions.

`maximum_merge_cost` asks:

```text
Is the next merge acceptable?
```

`max_regions` asks:

```text
Has the desired region-count target already been reached?
```

The reducer stops when either answer requires it to stop.

This means:

- an image below 350 mandatory regions receives no optional reduction;
- an image may stop above 350 because no further merge is acceptable;
- an image may reach 350 before the quality boundary is exhausted.

Changing `max_regions` does not redefine what a merge cost means.

## Recalibration Requirements

The current `maximum_merge_cost = 0.300` is valid only for the policy and
semantics against which it was calibrated.

Recalibration is required after a material change to any factor that changes
candidate costs or the region baseline used to interpret them.

Relevant changes include:

- raw merge metrics;
- metric normalization;
- color penalty normalization;
- merge-cost component weights;
- enclosure protection;
- compactness protection;
- color-distance semantics;
- production quantization behavior;
- mandatory paintability policy;
- candidate construction or directed merge semantics.

A purely internal optimization that preserves identical candidate metrics,
costs, ordering and region results does not require threshold recalibration.

## Performance Is a Separate Decision

Quality calibration and runtime acceptance are separate concerns.

A threshold can be visually acceptable while still imposing unacceptable
runtime overhead.

The end-to-end performance behavior and the accepted overhead for optional
complexity reduction are recorded in
[`performance-measurements.md`](performance-measurements.md).

Performance results must not be used as evidence that a visually destructive
merge is acceptable.

Likewise, region-count reduction alone must not be treated as evidence of
runtime efficiency.

## Current Status

The current calibrated policy is:

```text
maximum_merge_cost:
    0.300

merge-cost weights:
    color          0.40
    affected area  0.25
    border         0.15
    geometry       0.20

detail protection:
    enclosure      0.50
    compactness    0.15

mandatory paintability:
    2.0 mm

color distance:
    Delta E 2000
```

This threshold is represented in the shipped configuration profiles.

It is supported by cross-image region-count calibration and by the
fragile-detail validation recorded above, in which no reference structure was
removed across the evaluation set.

The separate end-to-end performance acceptance decision is recorded in
[`performance-measurements.md`](performance-measurements.md).

## Related Documentation

For the reduction algorithm itself, see:

- [`algorithms/region-complexity-reduction.md`](algorithms/region-complexity-reduction.md).

For the surrounding generation architecture, see:

- [`architecture-overview.md`](architecture-overview.md).

For the supported color-distance algorithms, see:

- [`algorithms/delta-e-76.md`](algorithms/delta-e-76.md);
- [`algorithms/delta-e-2000.md`](algorithms/delta-e-2000.md).

For user-facing configuration and CLI usage, see:

- [`../README.md`](../README.md).

For current planned and remaining work, see:

- [`../ROADMAP.md`](../ROADMAP.md).