# Input Bound Measurements

Measured on **2026-09-05**, Linux, one machine. Absolute figures are
hardware-dependent; the shapes and the ratios are the durable part.

Reproduce with:

    python tools/measure_input_bounds.py

This covers what an input costs *before* generation starts.
`docs/adversarial-input-measurements.md` covers generation itself and
begins from an image already at the processing resolution, so neither of
the two questions here is answerable from it.

## Decoding cost by pixel count

| Pixels | Content | File | Seconds | Peak |
|---|---|---|---|---|
| 1,597,696 | `noise` | 4.8 MB | 0.02 | 7 MB |
| 1,597,696 | `flat` | 0.0 MB | 0.02 | 7 MB |
| 4,000,000 | `noise` | 12.0 MB | 0.05 | 16 MB |
| 4,000,000 | `flat` | 0.0 MB | 0.04 | 16 MB |
| 9,998,244 | `noise` | 30.0 MB | 0.23 | 39 MB |
| 9,998,244 | `flat` | 0.0 MB | 0.08 | 39 MB |
| 19,998,784 | `noise` | 60.0 MB | 0.18 | 77 MB |
| 19,998,784 | `flat` | 0.1 MB | 0.19 | 77 MB |
| 39,992,976 | `noise` | 120.0 MB | 0.64 | 154 MB |
| 39,992,976 | `flat` | 0.1 MB | 0.32 | 154 MB |

Both contents cost the same to decode. A `flat` image at the hard bound
is **105 kilobytes** on disk and **154 megabytes** decoded, a ratio of
about **1,400 to 1**. That is the decompression bomb stated as a number:
a bound on upload size is not a bound on decoding cost, and the two are
unrelated by more than three orders of magnitude.

Cost is linear in the pixel count and has no threshold anywhere in the
measured range: about **3.9 bytes and 12 nanoseconds per pixel**. The
per-pixel memory exceeds the three bytes an RGB pixel occupies because
the decoder holds its own row buffers alongside the image.

## What the hard input bound is worth

The untrusted profile refuses an input above **40 megapixels** without
decoding it. At that bound the decode alone costs 154 MB and 0.6 s.

Set against the measured generation worst case of **1437 MB** and
**100 s** at the processing resolution, decoding contributes about
**11 % of the memory** and **under 1 % of the runtime**. The bound is
therefore not the constraint that matters, and it was never going to be:
generation dominates by an order of magnitude in both.

There is no measured cliff to derive a bound from. Any value is a policy
choice about how much of the memory budget to spend before the input is
known to be usable, and these figures are what a front end picks one
with. 40 megapixels spends about a tenth of it, which is a defensible
place to stop and not a derived one.

## Unique colors, before and after reduction

| Source | Pixels | Colors | Reduced to | Colors |
|---|---|---|---|---|
| `noise` | 1,597,696 | 1,524,105 | 1,597,696 | 1,524,105 |
| `noise` | 4,000,000 | 3,558,521 | 1,597,696 | 1,295,916 |
| `noise` | 7,997,584 | 6,362,130 | 1,597,696 | 965,111 |
| `noise` | 23,990,404 | 12,761,329 | 1,597,696 | 417,745 |
| `complex.png` | 1,571,840 | 705,290 | 1,571,840 | 705,290 |
| `landscape.png` | 1,572,864 | 658,777 | 1,572,864 | 658,777 |
| `portrait.png` | 1,572,864 | 199,089 | 1,572,864 | 199,089 |

Quantization evaluates one color distance per unique color per palette
color, so the unique color count is a cost driver the pixel count does
not describe on its own.

**The count is already bounded, and the bound is nearly tight.** It
cannot exceed the processing resolution, and noise at that resolution
reaches **1,524,105 of 1,600,225 pixels, or 95 %**. A separate bound
would be a second lever on a cost the processing resolution already
governs; lowering that resolution is the same lever with fewer moving
parts.

**Reduction lowers the count, and the more it reduces the more it
lowers.** Twenty-four megapixels of noise carry 12.8 million distinct
colors and arrive at 418 thousand, a factor of thirty. Interpolation
averages neighbours, and averages of many independent values collide.

**The worst case is therefore an input at the processing resolution, not
a large one.** An attacker maximizing this cost uploads 1.6 megapixels
of noise, not 40. A larger upload buys them nothing and costs them the
decode.

**Evaluated after reduction, not before.** The roadmap asked where. The
answer is measured rather than argued: on the same input the two
readings differ by up to a factor of thirty, and the reading before
reduction describes an image that never reaches quantization.

Real photographs at the processing resolution carry 199 thousand to 705
thousand distinct colors, a quarter to a half of the noise worst case.
That gap is the same shape as the one in the adversarial generation
measurements and has the same consequence: a bound sized from the
reference images would be sized at half the real worst case.

## Limits of this measurement

One machine, one Pillow version, PNG only. JPEG decoding differs, and
the loader additionally asks a JPEG decoder to decode directly at the
reduced scale, which this does not measure.

Peak memory is read from `VmHWM` after resetting it through
`/proc/self/clear_refs`, which is Linux-specific. The first version of
the tool used `ru_maxrss` and reported `0 MB` for every row, because
that counter is inherited across `fork` and the parent process builds a
forty megapixel array to write the file the child decodes.
