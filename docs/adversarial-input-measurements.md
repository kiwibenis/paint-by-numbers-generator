# Adversarial Input Measurements

Measured on **2026-09-03**, Linux, one machine. Absolute figures are
hardware-dependent; the ratios between classes are the durable part.

Reproduce with:

    python tools/measure_adversarial_input.py

ADR-0016 requires the resource limits to be derived from adversarial
rather than representative inputs. This document is the measurement
behind that requirement, and it shows why the requirement exists.

## At the processing limit

1400x1140 = 1.596 megapixels, just under the 1.6 megapixel processing
limit of ADR-0016. Complete generation including outlines, labels and PDF
export, with `config/example.toml` and parallel quantization disabled.

| Class | Upload | Seconds | Peak RSS |
|---|---|---|---|
| `checkerboard` | 10 kB | 42.9 | **1437 MB** |
| `noise` | 4.8 MB | **100.0** | 1080 MB |
| `gradient` | 7 kB | 75.2 | 511 MB |
| `comb` | 7 kB | 20.0 | 334 MB |
| `complex` (reference photograph) | 1.4 MB | 50.4 | 434 MB |

## What this changes

The reference images understate the worst case by **3.3x in memory** and
**2.0x in runtime**. An address-space limit sized from the reference
photographs would abort a legitimate request that happens to contain a
fine repeating pattern, and a wall-clock limit sized the same way would
abort at half the real worst case.

A prior extrapolation in the roadmap put a request at roughly `450 MB` at
the processing limit, derived from the reference images. The measured
worst case is `1437 MB`. That extrapolation was wrong by a factor of
three, and it was wrong in the direction that matters.

## Amplification

The cost is not carried by the upload:

| Class | Upload | Peak RSS | Amplification |
|---|---|---|---|
| `checkerboard` | 10 061 bytes | 1437 MB | 142 800x |
| `noise` | 4 795 924 bytes | 1080 MB | 225x |

A ten kilobyte file is the most expensive input measured. Any limit
placed on upload size is therefore not a limit on cost, and a request
that passes an upload check tells nothing about what it will consume.

## Scaling

Fitted between 800x600 (0.48 MP) and 1400x1140 (1.596 MP), as exponents
of the pixel count:

| Class | Runtime | Memory |
|---|---|---|
| `checkerboard` | 1.10 | 0.95 |
| `noise` | 1.08 | 0.92 |
| `gradient` | **1.27** | 0.78 |
| `comb` | 1.07 | 0.71 |

Memory scales slightly below linear, so the per-megapixel figure falls
with size and the small case is the conservative one for a memory bound.

Runtime scales above linear for every class. `gradient` is the worst at
`1.27`, because quantization caches by color and an input with no
repeated color defeats the cache. Doubling the accepted resolution
therefore more than doubles the worst-case time, which a limit derived at
one resolution must not be assumed to survive at another.

## Cost by processing resolution

Measured on **2026-09-05**, same machine, `config/example.toml` with
parallel quantization disabled and the processing resolution set to the
image's own size, so that each row is of the resolution it names.

Reproduce one row with:

    python tools/measure_adversarial_input.py \
        --width 1212 --height 987 \
        --classes checkerboard,noise,gradient

| Megapixels | `checkerboard` | `noise` | `gradient` |
|---|---|---|---|
| 0.199 | 3.3 s / 228 MB | 8.5 s / 180 MB | 5.5 s / 115 MB |
| 0.399 | 7.2 s / 406 MB | 17.1 s / 316 MB | 9.2 s / 181 MB |
| 0.798 | 14.5 s / 763 MB | 38.1 s / 581 MB | 18.2 s / 296 MB |
| 1.196 | 23.7 s / 1059 MB | 55.9 s / 838 MB | 36.2 s / 376 MB |
| 1.596 | 30.6 s / **1435 MB** | **72.8 s** / 1079 MB | 48.4 s / 509 MB |
| 2.394 | over 900 s | over 900 s | over 900 s |

Fitted over the five completed rows, as exponents of the pixel count:

| Class | Runtime | at 1 MP | Memory | at 1 MP |
|---|---|---|---|---|
| `checkerboard` | 1.07 | 18.9 s | 0.88 | 928 MB |
| `noise` | 1.05 | 46.0 s | 0.86 | 714 MB |
| `gradient` | 1.07 | 27.4 s | 0.70 | 349 MB |

**A bound on memory as a function of the accepted pixel limit.** Memory
scales below linear for every class, so a linear rule is conservative
and the small case sets it. The worst per-megapixel figure measured is
`1147 MB` at 0.199 megapixels, falling to `899 MB` at 1.596. Taking the
largest and rounding up:

    peak memory bound = 1200 MB per megapixel of processing resolution

At the 1.6 megapixel resolution of ADR-0016 that gives `1920 MB`,
against a worst measured `1435 MB`, which is the `2048 MB` already
recorded rounded to a page boundary rather than a new figure.

**The row that matters most is the one with no numbers in it.** Every
class exceeds 900 seconds at 2.394 megapixels, having taken 30 to 73
seconds at 1.596. A 1.5x increase in pixels produced at least a 12x to
29x increase in runtime, where the fitted exponents predict about 1.6x.

The exponents therefore describe the range they were fitted in and
nothing above it. This was already stated here as a caution; it is now a
measurement.

## Where the cliff is

Not an exponent. A constant.

The cause was found by sampling the stack of a running generation every
sixty seconds. Over thirty-two minutes at 2.394 megapixels, on a second
machine where the run eventually finished after **1924 seconds**, every
single sample stood in the same place:

    label/placer.py  _squared_border_distance
    label/placer.py  _select_best_pixel
    label/placer.py  _best_position

Label placement, and specifically its fallback. `_best_position` chooses
between a distance transform, which costs the bounding box area, and a
pairwise scan, which costs `interior x boundary`. The chooser refuses
the transform when its array would exceed `_MAX_DISTANCE_TRANSFORM_BYTES`,
16 MiB, at `_DISTANCE_VALUE_BYTES` of 8 per entry:

    cliff = 16 MiB / 8 = 2,097,152 pixels of bounding box

The refusal is a memory bound and it is the right shape for memory. It
is the wrong shape for time: a region large enough to trip it is large
in bounding box, interior and boundary at once, so it is handed the
quadratic algorithm exactly where that is most expensive.

Confirmed by measuring either side of the constant rather than by
reading it:

| Pixels | Against the cliff | Seconds |
|---|---|---|
| 1,998,216 | below | **46.9** |
| 2,198,334 | above | over 400 |

**It is unreachable at the processing resolution of ADR-0016.** A
region's bounding box cannot exceed the image, and at 1.6 megapixels the
whole image is 1,600,000 pixels, below the 2,097,152 of the cliff. No
input this project accepts today reaches the fallback. This is a
property of a constant that happens to sit above the configured
resolution, not a guarantee anything enforces.

It is left in place deliberately, documented here and at the chooser.

**What this means for a limit.** Figures exist for resolutions up to 1.6
megapixels and are stated above. Between there and 2.097 megapixels the
table has no rows but the shape is expected to hold. Above 2.097
megapixels the fallback becomes reachable and the figures do not
transfer at all. A deployment raising the processing resolution has to
measure, and now knows what it would be measuring.

## What each class targets

| Class | Cost it maximizes |
|---|---|
| `noise` | Number of detected regions, and the merge work to reduce them |
| `checkerboard` | Outline length relative to area, and pairwise overlap predicates |
| `comb` | Perimeter of a single region relative to its area |
| `gradient` | Number of distinct colors, defeating the quantization cache |
| `flat` | Cheapest possible input, as the floor of the comparison |

## Limits of this measurement

These are five cheaply constructed classes, not a search for the worst
input. A better one very likely exists: nothing here targets the merge
cost function directly, or constructs a topology that maximizes the
outline overlap predicate path specifically, which Milestone 12 measured
as the dominant cost before acceleration.

Every run completed. No class was found that fails rather than merely
costs, which is the more interesting failure and has not been searched
for.

The figures come from one machine and one configuration. `max_regions`
and `maximum_merge_cost` from `config/example.toml` shape the merge stage
substantially, and a different configuration will produce different
worst cases.
