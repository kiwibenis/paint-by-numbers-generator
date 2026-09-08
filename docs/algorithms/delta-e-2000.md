# CIEDE2000 Color Distance

## Purpose

This document describes how CIEDE2000 computes a distance between two
CIELAB colors, and what that costs.

It is selected with:

```toml
[generation]
color_distance = "delta_e_2000"
```

The alternative is `delta_e_76`, described in
[`delta-e-76.md`](delta-e-76.md).

## Inputs

CIEDE2000 compares two colors represented as CIELAB values:

```text
L*, a*, b*
```

The calculation produces a non-negative scalar distance. A smaller value
means that the two colors are considered more similar by the metric.

## Algorithm

The project implements the CIEDE2000 color-difference calculation rather than
plain Euclidean distance in Lab space.

For two Lab colors, the calculation performs these steps:

1. Calculate the initial chroma values from `a*` and `b*`.
2. Calculate the mean chroma and the CIEDE2000 `G` compensation term.
3. Adjust the `a*` components and calculate the adjusted chroma values.
4. Calculate adjusted hue angles in degrees and normalize them to the
   `[0, 360)` range.
5. Calculate lightness, chroma and hue differences.
6. Resolve hue wrap-around so that differences across the `0`/`360` degree
   boundary use the shortest valid angular path.
7. Calculate mean lightness, mean chroma and mean hue.
8. Calculate the hue weighting term `T`.
9. Calculate the lightness, chroma and hue weighting functions `S_L`, `S_C`
   and `S_H`.
10. Calculate the rotation term `R_T`, which accounts for interactions between
    chroma and hue differences in the blue region of Lab space.
11. Combine the normalized lightness, chroma and hue terms into the final
    CIEDE2000 distance.

The final structure is:

```text
DeltaE00 = sqrt(
    (DeltaL' / (kL * SL))^2
    + (DeltaC' / (kC * SC))^2
    + (DeltaH' / (kH * SH))^2
    + RT
      * (DeltaC' / (kC * SC))
      * (DeltaH' / (kH * SH))
)
```

The standard reference conditions use:

```text
kL = 1
kC = 1
kH = 1
```

## Hue Handling

Hue is circular rather than linear. CIEDE2000 therefore requires explicit
handling when hue angles cross the `0`/`360` degree boundary.

For example, hue angles close to `359` and `1` degrees are close to each
other. Treating their difference as approximately `358` degrees would be
incorrect.

The implementation normalizes hue angles and applies the CIEDE2000
wrap-around rules when calculating both hue differences and mean hue.

Achromatic cases are handled separately because hue is undefined when the
adjusted chroma is zero.

## Delta E 76 Comparison

`delta_e_76` uses the direct Euclidean distance between two Lab colors:

```text
DeltaE76 = sqrt(
    (DeltaL*)^2
    + (Deltaa*)^2
    + (Deltab*)^2
)
```

It is simpler and computationally cheaper than CIEDE2000.

`delta_e_2000` applies additional corrections for perceptual non-uniformity in
CIELAB. The two metrics can therefore select different nearest palette colors
for the same source color.

## Configuration

`color_distance` is a required generation configuration value. Its
configuration reference, including both supported values and the precedence
between TOML and the CLI, is in [`../../README.md`](../../README.md) under
"Color Distance Configuration".

Reproducibility follows from that value: CIEDE2000 is not interchangeable with
the other metric, so a document regenerated under a different setting can
differ in which palette color each source color matched.

## Validation

Unsupported color-distance identifiers are rejected during configuration
validation before generation starts.

The CIEDE2000 implementation is covered by dedicated calculation tests,
including published reference-pair cases, to detect regressions in the
formula and its hue-boundary handling.

## Performance

CIEDE2000 requires substantially more arithmetic than Delta E 76. Palette
matching evaluates the selected metric repeatedly during quantization, so the
choice of metric can have a measurable effect on generation time for images
with many distinct colors.

The quantizer caches nearest-palette results for repeated RGB values within a
quantization run. This reduces repeated color conversions and distance
calculations when the same input colors occur multiple times.
