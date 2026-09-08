# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Measure worst-case runtime and memory against adversarial input.

ADR-0016 requires the resource limits to be derived from adversarial
rather than representative inputs. The reference images in `examples`
are representative: they are photographs, and a photograph is not what
an attacker uploads.

Each generator below targets a different cost in the pipeline. The point
is not that these are the worst inputs that exist, only that they are
cheap to construct and already exceed the reference images by a wide
margin, which is enough to show that reference measurements cannot size
a limit.

Memory is the resident set size of the whole process, because that is
what an address-space limit bounds. It is only available where the
`resource` module is, which excludes Windows; the runtime figures are
measured everywhere.

Usage:

    python tools/measure_adversarial_input.py
    python tools/measure_adversarial_input.py --width 1400 --height 1140
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
import time
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path

from PIL import Image

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def build_noise(
    width: int,
    height: int,
) -> Image.Image:
    """
    Maximize the number of detected regions.

    Every pixel differs from its neighbors, so region detection produces
    close to one region per pixel and the merge stage has to reduce all
    of them.
    """
    generator = random.Random(1)
    image = Image.new("RGB", (width, height))
    image.putdata(
        [
            (
                generator.randrange(256),
                generator.randrange(256),
                generator.randrange(256),
            )
            for _ in range(width * height)
        ],
    )

    return image


def build_checkerboard(
    width: int,
    height: int,
) -> Image.Image:
    """
    Maximize outline length relative to area.

    Every region is a single pixel and every region boundary is a full
    perimeter, which is the worst case for outline tracing and for the
    pairwise overlap predicates.
    """
    image = Image.new("RGB", (width, height))
    image.putdata(
        [
            (255, 255, 255) if (x + y) % 2 else (0, 0, 0)
            for y in range(height)
            for x in range(width)
        ],
    )

    return image


def build_comb(
    width: int,
    height: int,
) -> Image.Image:
    """
    Maximize the perimeter of a single region.

    Few regions, but each one is a comb whose outline is far longer than
    its area suggests.
    """
    image = Image.new("RGB", (width, height), (255, 255, 255))
    pixels = image.load()

    if pixels is None:
        raise RuntimeError(
            "The image did not expose its pixel access object.",
        )

    for x in range(0, width, 2):
        depth = height - 2 if (x // 2) % 2 == 0 else height - 1

        for y in range(depth):
            pixels[x, y] = (0, 0, 0)

    return image


def build_gradient(
    width: int,
    height: int,
) -> Image.Image:
    """
    Maximize the number of distinct colors.

    Quantization caches by color, so an input with no repeated color
    defeats the cache while the regions stay large and smooth.
    """
    image = Image.new("RGB", (width, height))
    image.putdata(
        [
            (
                (x * 7) % 256,
                (y * 11) % 256,
                ((x + y) * 13) % 256,
            )
            for y in range(height)
            for x in range(width)
        ],
    )

    return image


def build_flat(
    width: int,
    height: int,
) -> Image.Image:
    """
    The cheapest possible input, as a floor for the comparison.
    """
    return Image.new("RGB", (width, height), (128, 64, 32))


BUILDERS: dict[str, Callable[[int, int], Image.Image]] = {
    "flat": build_flat,
    "comb": build_comb,
    "gradient": build_gradient,
    "checkerboard": build_checkerboard,
    "noise": build_noise,
}

_CHILD = """
import json
import sys
import time

sys.argv = [
    "pbn",
    "generate",
    "--input", {image!r},
    "--output", {output!r},
    "--parallel-quantization-enabled", "false",
    "--processing-pixel-count", {processing!r},
    "--config_file", {config!r},
]

try:
    import resource
except ImportError:
    resource = None

from pbn.cli.main import main

start = time.perf_counter()

try:
    main()
    status = "ok"
except BaseException as exc:
    status = f"{{type(exc).__name__}}: {{exc}}"[:120]

elapsed = time.perf_counter() - start

peak = None

if resource is not None:
    peak = round(
        resource.getrusage(
            resource.RUSAGE_SELF,
        ).ru_maxrss / 1024,
        1,
    )

print(
    "RESULT " + json.dumps(
        {{
            "seconds": round(elapsed, 1),
            "megabytes": peak,
            "status": status,
        }},
    ),
)
"""


def measure(
    image: Path,
    output: Path,
    config: Path,
    timeout: int,
    processing_pixel_count: int,
) -> dict[str, object]:
    """
    Run one complete generation in its own process and measure it.

    A separate process is what makes the resident set size attributable
    to this run rather than to everything measured before it.

    The processing resolution is set to the image's own pixel count, so
    that a measurement is of the size it names. Left to the profile, a
    run above the configured resolution would silently measure the
    reduced image and report it under the larger label.
    """
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                _CHILD.format(
                    image=str(image),
                    output=str(output),
                    config=str(config),
                    processing=str(processing_pixel_count),
                ),
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return {
            "seconds": None,
            "megabytes": None,
            "status": f"timeout above {timeout} s",
        }

    for line in completed.stdout.splitlines():
        if line.startswith("RESULT "):
            result: dict[str, object] = json.loads(
                line[len("RESULT ") :],
            )

            return result

    return {
        "seconds": round(time.perf_counter() - started, 1),
        "megabytes": None,
        "status": (completed.stderr.strip().splitlines() or ["no result"])[-1][:120],
    }


def main() -> None:
    parser = ArgumentParser(
        description="Measure adversarial input cost.",
    )
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=1140)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "config" / "example.toml",
    )
    parser.add_argument(
        "--classes",
        help=(
            "Comma-separated subset of the classes to measure. "
            "Defaults to all of them."
        ),
    )
    arguments = parser.parse_args()

    pixels = arguments.width * arguments.height

    print(
        f"{arguments.width}x{arguments.height} = " f"{pixels / 1e6:.3f} megapixels",
    )
    print(
        f"{'class':16s} {'bytes':>10s} {'seconds':>9s} " f"{'megabytes':>10s}  status",
    )

    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)

        selected = (
            tuple(name.strip() for name in arguments.classes.split(","))
            if arguments.classes
            else tuple(BUILDERS)
        )

        for name in selected:
            builder = BUILDERS[name]

            image_path = workspace / f"{name}.png"
            builder(
                arguments.width,
                arguments.height,
            ).save(image_path)

            result = measure(
                image_path,
                workspace / f"{name}.pdf",
                arguments.config,
                arguments.timeout,
                pixels,
            )

            seconds = result["seconds"]
            megabytes = result["megabytes"]

            print(
                f"{name:16s} "
                f"{image_path.stat().st_size:10d} "
                f"{seconds if seconds is not None else '-':>9} "
                f"{megabytes if megabytes is not None else '-':>10}  "
                f"{result['status']}",
            )


if __name__ == "__main__":
    main()
