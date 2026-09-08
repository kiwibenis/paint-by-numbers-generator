# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Measure what crosses the boundary to spawned quantization workers.

ADR-0014 parallelizes quantization across processes. `spawn` cannot share
memory, so every argument is pickled on the way out and every result on
the way back, and the cost scales with the number of unique colors
rather than with the image.

The port carried the colors as `RGB` objects and returned them paired
with `PaletteColor` objects until ADR-0014 replaced both with bytes.
This measures the two shapes side by side: `objects` is what the port
used to carry, `bytes` is what it carries now.

The parent pays part of this sequentially: it serializes every chunk
before any worker starts, and deserializes every result after they
finish. That part cannot be parallelized away and is what this measures
separately. It is where the change was expected to show, and where the
end-to-end measurement in the roadmap found it.

Usage:

    python tools/measure_worker_serialization.py
    python tools/measure_worker_serialization.py --case complex --workers 8
"""

from __future__ import annotations

import pickle
import time
from argparse import ArgumentParser
from pathlib import Path

from pbn.color.color_distance import ColorDistance
from pbn.color.delta_e_76 import DeltaE76
from pbn.color.delta_e_2000 import DeltaE2000
from pbn.color.quantizer import ImageQuantizer
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import RGB, PaletteColor

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def _palette_path(
    palette_id: str,
    palette_version: int,
) -> Path:
    return REPOSITORY_ROOT / "palettes" / f"{palette_id}-v{palette_version}.json"


def _color_distance(
    name: str,
) -> ColorDistance:
    """
    Resolved here rather than imported from another tool.

    Tools in this project do not import each other, because doing so
    only works when the repository root happens to be on the path.
    """
    if name == "delta_e_76":
        return DeltaE76()

    if name == "delta_e_2000":
        return DeltaE2000()

    raise ValueError(
        f"Unknown color distance: {name}",
    )


def _measure(
    value: object,
    repetitions: int = 3,
) -> tuple[int, float, float]:
    """
    Return the pickled size and the best dump and load times.
    """
    best_dump = None
    blob = b""

    for _ in range(repetitions):
        started = time.perf_counter()
        blob = pickle.dumps(
            value,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
        elapsed = time.perf_counter() - started
        best_dump = elapsed if best_dump is None else min(best_dump, elapsed)

    started = time.perf_counter()
    pickle.loads(blob)
    load = time.perf_counter() - started

    return len(blob), best_dump or 0.0, load


def _packed(
    colors: tuple[RGB, ...],
) -> bytes:
    return bytes(
        bytearray(
            channel
            for color in colors
            for channel in (
                color.red,
                color.green,
                color.blue,
            )
        ),
    )


def main() -> None:
    parser = ArgumentParser(
        description="Measure worker serialization cost.",
    )
    parser.add_argument("--case", default="complex_smaller")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "config" / "example.toml",
    )
    arguments = parser.parse_args()

    config = load_config(arguments.config)
    palette = load_palette(
        _palette_path(
            config.palette,
            config.palette_version,
        ),
    )
    image = load_image(
        REPOSITORY_ROOT / "examples" / "input" / f"{arguments.case}.png",
        config.image_input_limits,
    )

    colors = ImageQuantizer(
        color_distance=_color_distance(
            config.color_distance,
        ),
    ).collect_unique_colors(image)

    print(
        f"{arguments.case}: {image.width}x{image.height}, "
        f"{len(colors)} unique colors, "
        f"palette of {len(palette.colors)}",
    )
    print(
        f"\n{'representation':40s} {'MB':>7s} " f"{'dump ms':>9s} {'load ms':>9s}",
    )

    outward_size, outward_dump, outward_load = _measure(
        tuple(colors),
    )
    print(
        f"{'outward as objects, tuple[RGB, ...]':40s} "
        f"{outward_size / 1e6:7.2f} "
        f"{outward_dump * 1000:9.1f} {outward_load * 1000:9.1f}",
    )

    results: tuple[tuple[RGB, PaletteColor], ...] = tuple(
        (color, palette.colors[0]) for color in colors
    )
    return_size, return_dump, return_load = _measure(results)
    print(
        f"{'return as objects, (RGB, PaletteColor)':40s} "
        f"{return_size / 1e6:7.2f} "
        f"{return_dump * 1000:9.1f} {return_load * 1000:9.1f}",
    )

    packed_size, packed_dump, packed_load = _measure(
        _packed(colors),
    )
    print(
        f"{'outward as bytes, three per color':40s} "
        f"{packed_size / 1e6:7.2f} "
        f"{packed_dump * 1000:9.1f} {packed_load * 1000:9.1f}",
    )

    index_size, index_dump, index_load = _measure(
        bytes(len(colors)),
    )
    print(
        f"{'return as bytes, one index per color':40s} "
        f"{index_size / 1e6:7.2f} "
        f"{index_dump * 1000:9.1f} {index_load * 1000:9.1f}",
    )

    # The parent serializes outward and deserializes the results. Both
    # happen once for the whole colour set regardless of worker count,
    # and neither overlaps with the workers computing.
    sequential = outward_dump + return_load
    packed_sequential = packed_dump + index_load

    print(
        f"\nsequential in the parent, objects   : " f"{sequential:6.2f} s",
    )
    print(
        f"sequential in the parent, bytes     : " f"{packed_sequential:6.2f} s",
    )
    print(
        f"worker side, objects                : "
        f"{outward_load + return_dump:6.2f} s "
        f"(parallel across {arguments.workers} workers)",
    )


if __name__ == "__main__":
    main()
