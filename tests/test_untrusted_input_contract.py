# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Every rejection an untrusted caller can provoke, through the interface.

The rejections themselves are covered where they are implemented, in
`test_image_input_enforcement.py`, `test_image_format_detection.py`,
`test_image_failure_containment.py` and
`test_palette_identifier_validation.py`. Those tests call a loader or a
manager directly.

This module answers the question those cannot: whether the rejection is
still a rejection by the time it leaves the process. A caller in another
language sees an exit code, a type name and a message, and nothing else.
An input that is refused deep inside but arrives as exit 70, or as a
crash, or with the input path on standard output, is a different
contract than the one stated in `docs/integration-contract.md`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image

from pbn.cli.contract import EXIT_REQUEST

CONFIGURATION = "config/untrusted.toml"
"""
The profile a caller-facing deployment uses.

The example profile bounds input far more loosely, so asserting these
rejections against it would prove less than it appears to.
"""


def run_generate(
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pbn",
            "generate",
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )


def generate(
    tmp_path: Path,
    *,
    image: Path | str,
    palette: str | None = None,
    palette_version: str | None = None,
    overrides: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    arguments = [
        "--input",
        str(image),
        "--output",
        str(tmp_path / "out.pdf"),
        "--config_file",
        CONFIGURATION,
        "--json",
    ]

    if palette is not None:
        arguments += [
            "--palette",
            palette,
        ]

    if palette_version is not None:
        arguments += [
            "--palette-version",
            palette_version,
        ]

    return run_generate(
        *arguments,
        *overrides,
    )


def failure_of(
    completed: subprocess.CompletedProcess[str],
    tmp_path: Path,
) -> dict[str, object]:
    """
    Return the reported failure, asserting the contract around it.

    The path check is here rather than in a test of its own, so that it
    holds for every rejection class below instead of for the one or two
    a separate test would have sampled. A front end that echoes standard
    output must not disclose where the upload was stored, whichever way
    the input was refused.
    """
    assert completed.returncode == EXIT_REQUEST, completed.stderr

    payload = json.loads(
        completed.stdout,
    )

    assert payload["status"] == "failed"
    assert str(tmp_path) not in completed.stdout

    error = payload["error"]

    assert error["caused_by_request"] is True
    assert error["message"]

    return dict(
        error,
    )


def png_declaring(
    path: Path,
    width: int,
    height: int,
) -> Path:
    """
    Write a PNG whose header declares a size its data does not carry.

    The shape of a decompression bomb: a small file that costs whatever
    the reader allocates on the strength of the header.
    """
    header = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes(
            (8, 2, 0, 0, 0),
        )
    )

    def chunk(
        kind: bytes,
        payload: bytes,
    ) -> bytes:
        return (
            len(payload).to_bytes(4, "big")
            + kind
            + payload
            + zlib.crc32(kind + payload).to_bytes(4, "big")
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00" * 32))
        + chunk(b"IEND", b""),
    )

    return path


def image_of(
    path: Path,
    width: int,
    height: int,
    image_format: str = "PNG",
    mode: str = "RGB",
) -> Path:
    Image.new(
        mode,
        (width, height),
        (10, 20, 30) if mode == "RGB" else 0,
    ).save(
        path,
        format=image_format,
    )

    return path


TIGHTENED = (
    "--maximum-input-width",
    "64",
    "--maximum-input-height",
    "64",
    "--maximum-input-pixel-count",
    "2048",
    "--processing-pixel-count",
    "2048",
)
"""
Bounds set on the command line, well below the configured profile.

The processing resolution comes down with them, because a profile whose
processing bound exceeds its input bound is refused as a configuration
error before any input is read.

The profile's own values are asserted in `test_limit_profiles.py`.
Reproducing them here would mean building a forty megapixel image to
prove that a bound is applied, which is a property of the code path and
not of the number. Overriding on the command line exercises the same
path, and confirms in passing that a bound may be tightened by a caller.
"""


def test_an_image_wider_than_the_limit_is_a_request_failure(
    tmp_path: Path,
) -> None:
    image = image_of(
        tmp_path / "wide.png",
        65,
        4,
    )

    assert (
        failure_of(
            generate(
                tmp_path,
                image=image,
                overrides=TIGHTENED,
            ),
            tmp_path,
        )["type"]
        == "ImageTooLargeError"
    )


def test_an_image_taller_than_the_limit_is_a_request_failure(
    tmp_path: Path,
) -> None:
    image = image_of(
        tmp_path / "tall.png",
        4,
        65,
    )

    assert (
        failure_of(
            generate(
                tmp_path,
                image=image,
                overrides=TIGHTENED,
            ),
            tmp_path,
        )["type"]
        == "ImageTooLargeError"
    )


def test_an_image_above_the_pixel_bound_is_a_request_failure(
    tmp_path: Path,
) -> None:
    """
    Inside the width and height bounds, and outside the area bound.

    The three limits are separate. An input satisfying two of them is
    not thereby accepted, which a single oversized dimension would not
    show.
    """
    image = image_of(
        tmp_path / "large.png",
        64,
        64,
    )

    assert 64 * 64 > 2048

    assert (
        failure_of(
            generate(
                tmp_path,
                image=image,
                overrides=TIGHTENED,
            ),
            tmp_path,
        )["type"]
        == "ImageTooLargeError"
    )


def test_a_declared_size_bomb_is_a_request_failure(
    tmp_path: Path,
) -> None:
    """
    Rejected on the header, before the declared pixels are allocated.

    The file is under a kilobyte, so an upload bound would not have
    stopped it.
    """
    image = png_declaring(
        tmp_path / "bomb.png",
        40_000,
        40_000,
    )

    assert image.stat().st_size < 1024

    assert (
        failure_of(
            generate(
                tmp_path,
                image=image,
            ),
            tmp_path,
        )["type"]
        == "ImageTooLargeError"
    )


def test_a_truncated_image_is_a_request_failure(
    tmp_path: Path,
) -> None:
    complete = image_of(
        tmp_path / "complete.png",
        200,
        200,
    ).read_bytes()

    truncated = tmp_path / "truncated.png"
    truncated.write_bytes(
        complete[: len(complete) // 2],
    )

    assert (
        failure_of(
            generate(
                tmp_path,
                image=truncated,
            ),
            tmp_path,
        )["type"]
        == "CorruptedImageError"
    )


@pytest.fixture(
    params=(
        "GIF",
        "TIFF",
    ),
)
def unsupported_content(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> Iterator[Path]:
    """
    Content of a format this project does not accept, behind an accepted
    extension.

    GIF is reachable for the library and refused here. TIFF is not
    reachable at all because ADR-0016 keeps it outside the supported
    decoder set together with RAW input. Both must be refused, and a
    caller need not know which mechanism did it.
    """
    yield image_of(
        tmp_path / "actually_other.png",
        4,
        3,
        image_format=request.param,
        mode="P" if request.param == "GIF" else "RGB",
    )


def test_unsupported_content_behind_an_accepted_extension_is_a_request_failure(
    tmp_path: Path,
    unsupported_content: Path,
) -> None:
    assert failure_of(
        generate(
            tmp_path,
            image=unsupported_content,
        ),
        tmp_path,
    )["type"] in (
        "UnsupportedImageFormatError",
        "CorruptedImageError",
    )


def test_an_unsupported_extension_is_a_request_failure(
    tmp_path: Path,
) -> None:
    image = tmp_path / "image.psd"
    image.write_bytes(
        b"8BPS" + b"\x00" * 64,
    )

    assert (
        failure_of(
            generate(
                tmp_path,
                image=image,
            ),
            tmp_path,
        )["type"]
        == "UnsupportedImageFormatError"
    )


@pytest.mark.parametrize(
    "identifier",
    (
        "reference8/../../secret",
        "/etc/passwd",
    ),
)
def test_a_palette_identifier_leaving_the_directory_is_a_request_failure(
    tmp_path: Path,
    small_input_image: Path,
    identifier: str,
) -> None:
    """
    One relative escape and one absolute path, not the full set.

    `test_palette_identifier_validation.py` covers eleven identifiers
    against the manager. What is open here is only whether the refusal
    survives to the interface, and that does not vary per identifier.
    Each case here costs a process.
    """
    assert (
        failure_of(
            generate(
                tmp_path,
                image=small_input_image,
                palette=identifier,
                palette_version="1",
            ),
            tmp_path,
        )["type"]
        == "PaletteNotFoundError"
    )


def test_an_input_within_the_limits_still_succeeds(
    tmp_path: Path,
    small_input_image: Path,
) -> None:
    """
    The counterpart every rejection test needs.

    A profile that refused everything would satisfy all of the above.
    """
    output = tmp_path / "out.pdf"

    completed = run_generate(
        "--input",
        str(small_input_image),
        "--output",
        str(output),
        "--config_file",
        CONFIGURATION,
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    assert (
        json.loads(
            completed.stdout,
        )["status"]
        == "succeeded"
    )
    assert output.exists()
