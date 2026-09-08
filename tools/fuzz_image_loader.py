# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Randomized malformed-input coverage for the image loading boundary.

Two questions, and only the first is answered here. Does malformed input
reach a caller as something other than an `ImageError`, and does it crash
the decoder? A pass says neither happened in the runs performed. It does
not say the decoder is safe: a memory-safety fault that corrupts without
crashing is invisible to this, and finding those needs a sanitizer build
rather than a Python loop.

Each case runs in its own process, because a native decoder can end the
process rather than raise, and that outcome has to be observable rather
than fatal to the run.

Usage:

    python tools/fuzz_image_loader.py
    python tools/fuzz_image_loader.py --raster 200
"""

from __future__ import annotations

import io
import json
import random
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path

from PIL import Image

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

RASTER_FORMATS = (
    ("BMP", ".bmp"),
    ("JPEG", ".jpg"),
    ("PNG", ".png"),
    ("WEBP", ".webp"),
)

_CHILD = """
import json
import pathlib
import sys
import warnings

warnings.simplefilter("ignore")

from pbn.exceptions import ImageError
from pbn.infrastructure.image_loader import ImageLoader
from tests.image_limits import TEST_IMAGE_INPUT_LIMITS

try:
    ImageLoader().load(
        pathlib.Path({path!r}),
        TEST_IMAGE_INPUT_LIMITS,
    )
    outcome = {{"outcome": "accepted"}}

except ImageError as exc:
    outcome = {{"outcome": "rejected", "type": type(exc).__name__}}

except BaseException as exc:
    outcome = {{"outcome": "escaped", "type": type(exc).__name__}}

print("RESULT " + json.dumps(outcome))
"""


def _run(
    path: Path,
    timeout: int,
) -> dict[str, object]:
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                _CHILD.format(path=str(path)),
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return {"outcome": "timeout"}

    for line in completed.stdout.splitlines():
        if line.startswith("RESULT "):
            result: dict[str, object] = json.loads(
                line[len("RESULT ") :],
            )

            return result

    return {
        "outcome": "crashed",
        "returncode": completed.returncode,
        "detail": (completed.stderr.strip().splitlines() or [""])[-1][:110],
    }


def _corrupt(
    data: bytes,
    generator: random.Random,
    strategy: str,
) -> bytes:
    """
    Return a corrupted copy of the input.

    The strategies differ in where they damage, because the decoders
    react differently to a damaged header than to damage spread through
    the whole file.
    """
    corrupted = bytearray(data)

    if strategy == "truncate":
        return bytes(
            corrupted[
                : generator.randrange(
                    16,
                    len(corrupted),
                )
            ],
        )

    if strategy == "header":
        for _ in range(
            generator.randrange(1, 30),
        ):
            corrupted[
                generator.randrange(
                    4,
                    min(4096, len(corrupted)),
                )
            ] = generator.randrange(256)

    elif strategy == "spread":
        for _ in range(
            generator.randrange(4, 400),
        ):
            corrupted[
                generator.randrange(
                    4,
                    len(corrupted),
                )
            ] = generator.randrange(256)

    elif strategy == "offsets":
        # Structure fields rather than payload: a decoder that trusts a
        # length or an offset is the classic way into a buffer.
        for _ in range(
            generator.randrange(1, 12),
        ):
            index = (
                generator.randrange(
                    8,
                    min(60_000, len(corrupted)),
                )
                & ~3
            )

            corrupted[index : index + 4] = generator.choice(
                [
                    b"\xff\xff\xff\xff",
                    b"\x00\x00\x00\x00",
                    b"\xff\xff\xff\x7f",
                    b"\x01\x00\x00\x80",
                ],
            )

    return bytes(corrupted)


STRATEGIES = (
    "truncate",
    "header",
    "spread",
    "offsets",
)


def _report(
    label: str,
    outcomes: Counter[str],
    notable: dict[str, dict[str, object]],
) -> None:
    print(f"  {label}")

    for outcome, count in outcomes.most_common():
        print(f"    {count:5d}  {outcome}")

    for outcome, detail in notable.items():
        print(f"    !!!    {outcome}: {detail}")


def _fuzz(
    label: str,
    data: bytes,
    suffix: str,
    runs: int,
    seed: int,
    timeout: int,
) -> bool:
    """
    Return whether every case stayed inside the project's errors.
    """
    generator = random.Random(seed)
    contained = True

    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / f"fuzz{suffix}"

        for strategy in STRATEGIES:
            outcomes: Counter[str] = Counter()
            notable: dict[str, dict[str, object]] = {}

            for _ in range(runs):
                target.write_bytes(
                    _corrupt(
                        data,
                        generator,
                        strategy,
                    ),
                )

                result = _run(
                    target,
                    timeout,
                )
                key = str(result["outcome"])

                if "type" in result:
                    key = f"{key} ({result['type']})"

                outcomes[key] += 1

                if result["outcome"] in (
                    "crashed",
                    "escaped",
                    "timeout",
                ):
                    contained = False
                    notable.setdefault(
                        key,
                        result,
                    )

            _report(
                f"{label} / {strategy}",
                outcomes,
                notable,
            )

    return contained


def _raster_source(
    image_format: str,
) -> bytes:
    buffer = io.BytesIO()
    image = Image.new(
        "RGB",
        (48, 32),
    )
    image.putdata(
        [
            (
                x * 5 % 256,
                y * 7 % 256,
                (x + y) * 3 % 256,
            )
            for y in range(32)
            for x in range(48)
        ],
    )
    image.save(
        buffer,
        format=image_format,
    )

    return buffer.getvalue()


def main() -> None:
    parser = ArgumentParser(
        description="Fuzz the image loading boundary.",
    )
    parser.add_argument("--raster", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--timeout", type=int, default=180)
    arguments = parser.parse_args()

    contained = True

    for image_format, suffix in RASTER_FORMATS:
        contained &= _fuzz(
            image_format,
            _raster_source(image_format),
            suffix,
            arguments.raster,
            arguments.seed,
            arguments.timeout,
        )

    print()
    print(
        (
            "every case stayed inside the project's errors"
            if contained
            else "AT LEAST ONE CASE ESCAPED"
        ),
    )

    if not contained:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
