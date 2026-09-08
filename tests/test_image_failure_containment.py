# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Every way an image can fail must leave the loader as an `ImageError`.

The decoders raise more than `OSError` on hostile content, and the set is
not enumerable from their documentation. These cases therefore exercise
the translation rather than assert a list of library exceptions.
"""

from __future__ import annotations

import random
import struct
import zlib
from pathlib import Path
from typing import Self

import pytest

from pbn.core.image_input_rules import ImageInputLimits
from pbn.exceptions import ImageError
from pbn.infrastructure.image_loader import ImageLoader
from pbn.models import InputImage
from tests.image_limits import TEST_IMAGE_INPUT_LIMITS


def _load(
    path: Path,
) -> None:
    ImageLoader().load(
        path,
        TEST_IMAGE_INPUT_LIMITS,
    )


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(
    kind: bytes,
    payload: bytes,
) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(
            ">I",
            zlib.crc32(kind + payload) & 0xFFFFFFFF,
        )
    )


def _png_header(
    width: int,
    height: int,
    bit_depth: int = 8,
    color_type: int = 2,
) -> bytes:
    return _PNG_SIGNATURE + _png_chunk(
        b"IHDR",
        struct.pack(
            ">IIBBBBB",
            width,
            height,
            bit_depth,
            color_type,
            0,
            0,
            0,
        ),
    )


_MALFORMED: dict[str, bytes] = {
    "empty": b"",
    "signature_only": _PNG_SIGNATURE,
    "header_without_data": _png_header(4, 4),
    "zero_width": _png_header(0, 4) + _png_chunk(b"IDAT", zlib.compress(b"\x00")),
    "zero_height": _png_header(4, 0) + _png_chunk(b"IDAT", zlib.compress(b"\x00")),
    "impossible_bit_depth": _png_header(4, 4, bit_depth=7)
    + _png_chunk(b"IDAT", zlib.compress(b"\x00")),
    "impossible_color_type": _png_header(4, 4, color_type=9)
    + _png_chunk(b"IDAT", zlib.compress(b"\x00")),
    "truncated_idat": _png_header(4, 4) + _png_chunk(b"IDAT", b"\x78\x9c\x01"),
    "corrupt_deflate_stream": _png_header(4, 4) + _png_chunk(b"IDAT", b"\xff" * 32),
    "declared_size_without_data": _png_header(4000, 3000)
    + _png_chunk(b"IDAT", zlib.compress(b"\x00" * 8)),
    "text_content": b"this is not an image at all",
    "nul_bytes": b"\x00" * 512,
}


@pytest.mark.parametrize(
    "name",
    sorted(_MALFORMED),
)
def test_malformed_content_leaves_as_a_project_error(
    tmp_path: Path,
    name: str,
) -> None:
    path = tmp_path / f"{name}.png"
    path.write_bytes(
        _MALFORMED[name],
    )

    with pytest.raises(ImageError):
        _load(path)


@pytest.mark.parametrize(
    "suffix",
    [
        ".bmp",
        ".jpg",
        ".png",
        ".webp",
    ],
)
def test_every_accepted_extension_contains_its_failures(
    tmp_path: Path,
    suffix: str,
) -> None:
    """
    The extension selects the decoder, so each one needs the guarantee.
    """
    path = tmp_path / f"hostile{suffix}"
    path.write_bytes(
        b"\x00\x01\x02\x03" * 64,
    )

    with pytest.raises(ImageError):
        _load(path)


def test_truncated_valid_image_is_rejected(
    tmp_path: Path,
) -> None:
    """
    Truncation must be rejected rather than silently completed.
    """
    from PIL import Image as PillowImage

    complete = tmp_path / "complete.png"
    PillowImage.new(
        "RGB",
        (64, 64),
        (10, 20, 30),
    ).save(complete)

    truncated = tmp_path / "truncated.png"
    truncated.write_bytes(
        complete.read_bytes()[:-40],
    )

    with pytest.raises(ImageError):
        _load(truncated)


@pytest.mark.parametrize(
    "seed",
    range(24),
)
def test_randomly_corrupted_images_are_contained(
    tmp_path: Path,
    seed: int,
) -> None:
    """
    Randomized corruption of a valid image, one seed per case.

    A pass is not proof of absence. It is a cheap net for the failure
    modes a hand-written corpus does not think of.
    """
    from PIL import Image as PillowImage

    source = tmp_path / f"source-{seed}.png"
    PillowImage.new(
        "RGB",
        (32, 32),
        (200, 100, 50),
    ).save(source)

    data = bytearray(
        source.read_bytes(),
    )
    generator = random.Random(seed)

    for _ in range(8):
        index = generator.randrange(
            len(_PNG_SIGNATURE),
            len(data),
        )
        data[index] = generator.randrange(256)

    corrupted = tmp_path / f"corrupted-{seed}.png"
    corrupted.write_bytes(
        bytes(data),
    )

    try:
        _load(corrupted)
    except ImageError:
        return


def test_a_directory_is_rejected(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "directory.png"
    directory.mkdir()

    with pytest.raises(ImageError):
        _load(directory)


def test_an_unreadable_file_is_rejected(
    tmp_path: Path,
) -> None:
    """
    A permission failure is an operational condition, not a crash.
    """
    path = tmp_path / "unreadable.png"
    path.write_bytes(
        _png_header(4, 4),
    )
    path.chmod(0o000)

    try:
        with pytest.raises(ImageError):
            _load(path)
    finally:
        path.chmod(0o600)


class _FailingHandle:
    def __enter__(self) -> Self:
        raise PermissionError(
            "Permission denied: /var/lib/pbn/upload.png",
        )

    def __exit__(self, *arguments: object) -> None:
        return None


def test_the_translation_keeps_the_original_as_the_cause() -> None:
    """
    The operator must still see what actually happened.
    """
    from tests.image_limits import TEST_IMAGE_INPUT_LIMITS as limits

    loader = ImageLoader()

    original = RuntimeError(
        "Decoder detail.",
    )

    def explode(
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage:
        raise original

    loader._load = explode  # type: ignore[method-assign]

    with pytest.raises(ImageError) as caught:
        loader.load(
            Path("unused.png"),
            limits,
        )

    assert caught.value.__cause__ is original


@pytest.mark.parametrize(
    "name",
    sorted(_MALFORMED),
)
def test_a_rejected_input_is_attributed_to_the_request(
    tmp_path: Path,
    name: str,
) -> None:
    """
    An interface derives a client error from this, per ADR-0019.
    """
    path = tmp_path / f"{name}.png"
    path.write_bytes(
        _MALFORMED[name],
    )

    with pytest.raises(ImageError) as caught:
        _load(path)

    assert caught.value.caused_by_request


@pytest.mark.parametrize(
    "name",
    sorted(_MALFORMED),
)
def test_a_rejection_does_not_publish_the_path(
    tmp_path: Path,
    name: str,
) -> None:
    """
    The diagnostic message may name the path. The public one may not.
    """
    path = tmp_path / f"{name}.png"
    path.write_bytes(
        _MALFORMED[name],
    )

    with pytest.raises(ImageError) as caught:
        _load(path)

    assert str(tmp_path) in caught.value.diagnostic_message
    assert str(tmp_path) not in caught.value.public_message
    assert name not in caught.value.public_message
