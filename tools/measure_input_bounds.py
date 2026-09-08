# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Measure what an input costs before generation starts.

Two questions the roadmap leaves open, and neither is answerable from the
generation measurements in `measure_adversarial_input.py`, which start
from an image already at the processing resolution.

The first is what the hard input bound buys. An input above it is never
decoded, so the bound is a statement about decoding cost, and decoding
cost had never been measured.

The second is whether the unique color count needs a bound of its own.
Quantization costs one color-distance evaluation per unique color per
palette color, so the count is a cost driver independent of the pixel
count, and the roadmap asks whether it is bounded and where it should be
evaluated.

Run with:

    python tools/measure_input_bounds.py

Each decode runs in its own process, because peak resident memory is a
high-water mark and one measurement in a shared process reports the
largest allocation so far rather than its own.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

PROCESSING_PIXEL_COUNT = 1_600_000
"""
The processing resolution of ADR-0016, which every input is reduced to.
"""

MEASURED_PIXEL_COUNTS = (
    1_600_000,
    4_000_000,
    10_000_000,
    20_000_000,
    40_000_000,
)
"""
Pixel counts to decode, ending at the untrusted profile's hard bound.
"""


@dataclass(frozen=True)
class DecodeCost:
    pixels: int
    file_bytes: int
    seconds: float
    peak_megabytes: float


def build_image(
    pixels: int,
    compressible: bool,
    seed: int,
) -> Image.Image:
    """
    Build a square image of about `pixels` pixels.

    Two contents, because the difference between them is the point: a
    flat image compresses to nothing and decodes to exactly as much as a
    noisy one.
    """
    side = int(
        pixels**0.5,
    )

    if compressible:
        return Image.fromarray(
            np.zeros(
                (side, side, 3),
                dtype=np.uint8,
            ),
        )

    return Image.fromarray(
        np.random.default_rng(
            seed,
        ).integers(
            0,
            256,
            size=(side, side, 3),
            dtype=np.uint8,
        ),
    )


def measure_decode(
    path: Path,
) -> DecodeCost:
    """
    Decode one file in a fresh process and report what it cost.
    """
    completed = subprocess.run(
        [
            sys.executable,
            __file__,
            "--decode",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    measurement = json.loads(
        completed.stdout,
    )

    return DecodeCost(
        pixels=measurement["pixels"],
        file_bytes=measurement["file_bytes"],
        seconds=measurement["seconds"],
        peak_megabytes=measurement["peak_megabytes"],
    )


CLEAR_REFERENCES = Path(
    "/proc/self/clear_refs",
)
"""
Resets this process's peak resident memory.

`ru_maxrss` is inherited across `fork`, so a child measuring itself
against its own starting value reports zero whenever the parent
allocated more than the child ever will. That is not a hypothetical: the
parent here builds a forty megapixel array to write the file the child
decodes, and the first version of this tool reported `0 MB` for every
row because of it.
"""


def peak_megabytes() -> float:
    """
    Return this process's peak resident memory since the last reset.
    """
    for line in (
        Path(
            "/proc/self/status",
        )
        .read_text(
            encoding="utf-8",
        )
        .splitlines()
    ):
        if line.startswith(
            "VmHWM:",
        ):
            return (
                int(
                    line.split()[1],
                )
                / 1024
            )

    raise RuntimeError(
        "VmHWM is not reported by this kernel",
    )


def decode_once(
    path: Path,
) -> None:
    """
    The child process: decode, report, exit.
    """
    Image.MAX_IMAGE_PIXELS = None

    CLEAR_REFERENCES.write_text(
        "5",
        encoding="utf-8",
    )

    before = peak_megabytes()

    started_at = time.perf_counter()

    image = Image.open(
        path,
    )
    image.load()

    finished_at = time.perf_counter()

    peak = peak_megabytes()

    print(
        json.dumps(
            {
                "pixels": image.width * image.height,
                "file_bytes": path.stat().st_size,
                "seconds": finished_at - started_at,
                "peak_megabytes": peak - before,
            },
        ),
    )


def unique_color_count(
    image: Image.Image,
) -> int:
    pixels = np.asarray(
        image.convert(
            "RGB",
        ),
    ).reshape(
        -1,
        3,
    )

    return len(
        np.unique(
            pixels.view(
                [
                    ("r", "u1"),
                    ("g", "u1"),
                    ("b", "u1"),
                ],
            ),
        ),
    )


def reduced(
    image: Image.Image,
) -> Image.Image:
    """
    Reduce to the processing resolution the way the loader does.
    """
    pixels = image.width * image.height

    if pixels <= PROCESSING_PIXEL_COUNT:
        return image

    scale = (PROCESSING_PIXEL_COUNT / pixels) ** 0.5

    return image.resize(
        (
            max(
                1,
                int(image.width * scale),
            ),
            max(
                1,
                int(image.height * scale),
            ),
        ),
        Image.Resampling.LANCZOS,
    )


def report_decode_cost() -> None:
    print(
        "## Decoding cost by pixel count",
    )
    print()
    print(
        "| Pixels | Content | File | Seconds | Peak |",
    )
    print(
        "|---|---|---|---|---|",
    )

    with TemporaryDirectory() as directory:
        root = Path(
            directory,
        )

        for pixels in MEASURED_PIXEL_COUNTS:
            for compressible, label in (
                (False, "noise"),
                (True, "flat"),
            ):
                path = root / f"{pixels}-{label}.png"

                build_image(
                    pixels,
                    compressible,
                    seed=11,
                ).save(
                    path,
                    compress_level=9 if compressible else 1,
                )

                cost = measure_decode(
                    path,
                )

                path.unlink()

                print(
                    f"| {cost.pixels:,} | `{label}` "
                    f"| {cost.file_bytes / 1e6:.1f} MB "
                    f"| {cost.seconds:.2f} "
                    f"| {cost.peak_megabytes:.0f} MB |",
                )


def report_unique_colors() -> None:
    print()
    print(
        "## Unique colors, before and after reduction",
    )
    print()
    print(
        "| Source | Pixels | Colors | Reduced to | Colors |",
    )
    print(
        "|---|---|---|---|---|",
    )

    for pixels in (
        1_600_000,
        4_000_000,
        8_000_000,
        24_000_000,
    ):
        image = build_image(
            pixels,
            compressible=False,
            seed=7,
        )

        small = reduced(
            image,
        )

        print(
            f"| `noise` | {image.width * image.height:,} "
            f"| {unique_color_count(image):,} "
            f"| {small.width * small.height:,} "
            f"| {unique_color_count(small):,} |",
        )

    for name in (
        "complex.png",
        "landscape.png",
        "portrait.png",
    ):
        path = (
            Path(
                "examples/input",
            )
            / name
        )

        if not path.exists():
            continue

        image = Image.open(
            path,
        ).convert(
            "RGB",
        )

        small = reduced(
            image,
        )

        print(
            f"| `{name}` | {image.width * image.height:,} "
            f"| {unique_color_count(image):,} "
            f"| {small.width * small.height:,} "
            f"| {unique_color_count(small):,} |",
        )


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=("Measure decoding cost and unique color counts."),
    )

    parser.add_argument(
        "--decode",
        help=("Internal. Decode one file and report the cost as JSON."),
    )

    return parser


def main() -> None:
    arguments = build_parser().parse_args()

    if arguments.decode:
        decode_once(
            Path(
                arguments.decode,
            ),
        )

        return

    report_decode_cost()
    report_unique_colors()


if __name__ == "__main__":
    main()
