# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The geometry library is a mandatory dependency per ADR-0015.

Tests that need it are therefore collected unconditionally. Skipping them
when it is absent would hide a broken installation behind a green run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture(scope="session")
def small_input_image(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """
    A small structured image for tests that run the command line.

    Those tests assert an exit code and the shape of what is written,
    which does not depend on how much work the pipeline did. Generating
    from `examples/input/simple_smaller.png` costs about 2.5 seconds per
    subprocess and this costs about 0.15, for the same assertions.

    Structured rather than flat, so quantization, region generation,
    outline tracing and label placement all have something to do. A
    single-color image would exercise the interface while skipping most
    of what stands behind it.

    Session-scoped: it is written once and never modified, and the tests
    using it only read it.
    """
    path = (
        tmp_path_factory.mktemp(
            "input",
        )
        / "small.png"
    )

    size = 64

    image = Image.new(
        "RGB",
        (size, size),
    )

    pixels = image.load()

    assert pixels is not None

    for y in range(size):
        for x in range(size):
            pixels[x, y] = (
                (x * 8) % 256,
                (y * 8) % 256,
                ((x + y) * 4) % 256,
            )

    image.save(
        path,
        format="PNG",
    )

    return path
