# Delta E 76 Color Distance

## Purpose

This document describes how Delta E 76 computes a distance between two
CIELAB colors, and what that costs.

It is selected with:

```toml
[generation]
color_distance = "delta_e_76"
```

The alternative is `delta_e_2000`, described in
[`delta-e-2000.md`](delta-e-2000.md). The shipped example configuration
selects that one.

## Inputs

Delta E 76 compares two colors represented in the CIELAB color space:

```text
L*, a*, b*
```

The calculation produces a non-negative scalar distance. A smaller value means
that the two colors are considered closer in CIELAB space.

The quantizer evaluates the configured distance metric against palette colors
and selects the palette color with the smallest distance.

## Algorithm

Delta E 76 uses the Euclidean distance between two CIELAB colors.

For two colors:

```text
Lab1 = (L1, a1, b1)
Lab2 = (L2, a2, b2)
```

the component differences are:

```text
DeltaL = L1 - L2
Deltaa = a1 - a2
Deltab = b1 - b2
```

The final distance is:

```text
DeltaE76 = sqrt(
    DeltaL^2
    + Deltaa^2
    + Deltab^2
)
```

No additional weighting or hue correction is applied.

## Properties

Delta E 76 has several useful properties for palette matching:

- The distance is zero when both Lab colors are identical.
- The distance is symmetric.
- Larger distances indicate greater separation in CIELAB space.
- The calculation is deterministic.
- The calculation requires substantially less arithmetic than CIEDE2000.

Because CIELAB is not perfectly perceptually uniform, equal Delta E 76
distances do not necessarily correspond to equal perceived color differences.

## CIEDE2000 Comparison

`delta_e_76` uses direct Euclidean distance in CIELAB.

`delta_e_2000` applies additional perceptual corrections for lightness,
chroma and hue and includes special handling for hue-angle wrap-around and
interactions in specific color regions.

The two metrics can therefore select different nearest palette colors for the
same source color.

Neither metric changes the reference palette itself. The configured metric
only changes how distances to palette colors are evaluated during
quantization.

CIEDE2000 implementation details are documented in
[`delta-e-2000.md`](delta-e-2000.md).

## Configuration

`color_distance` is a required generation configuration value. Its
configuration reference, including both supported values and the precedence
between TOML and the CLI, is in [`../../README.md`](../../README.md) under
"Color Distance Configuration".

Reproducibility follows from that value: Delta E 76 is not interchangeable with
the other metric, so a document regenerated under a different setting can
differ in which palette color each source color matched.

## Validation

Unsupported color-distance identifiers are rejected during configuration
validation before generation starts.

The Delta E 76 implementation is covered by dedicated tests that verify zero
distance, Euclidean distance calculation and symmetry.

## Performance

Delta E 76 is computationally simpler than CIEDE2000 and is therefore suited
to repeated nearest-palette calculations during image quantization.

The quantizer caches nearest-palette results for repeated RGB values within a
quantization run. This reduces repeated color conversion and distance
calculation when the same input colors occur multiple times.
