# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from pbn.exceptions import CorruptedImageError, UnsupportedImageFormatError
from pbn.infrastructure.image_decoder_policy import (
    reachable_image_decoders,
)
from pbn.infrastructure.image_loader import ImageLoader
from tests.image_limits import TEST_IMAGE_INPUT_LIMITS


def _write(
    directory: Path,
    name: str,
    image_format: str,
) -> Path:
    path = directory / name

    Image.new(
        "RGB",
        (4, 3),
        (10, 20, 30),
    ).save(
        path,
        format=image_format,
    )

    return path


@pytest.mark.parametrize(
    "name,image_format",
    [
        ("image.png", "PNG"),
        ("image.jpg", "JPEG"),
        ("image.jpeg", "JPEG"),
        ("image.bmp", "BMP"),
        ("image.webp", "WEBP"),
    ],
)
def test_matching_content_and_extension_is_accepted(
    tmp_path: Path,
    name: str,
    image_format: str,
) -> None:
    image = ImageLoader().load(
        _write(
            tmp_path,
            name,
            image_format,
        ),
        TEST_IMAGE_INPUT_LIMITS,
    )

    assert image.width == 4
    assert image.height == 3


@pytest.mark.parametrize(
    "name,image_format",
    [
        ("actually_png.jpg", "PNG"),
        ("actually_jpeg.png", "JPEG"),
        ("actually_bmp.png", "BMP"),
        ("actually_webp.bmp", "WEBP"),
    ],
)
def test_content_not_matching_the_extension_is_rejected(
    tmp_path: Path,
    name: str,
    image_format: str,
) -> None:
    path = _write(
        tmp_path,
        name,
        image_format,
    )

    with pytest.raises(UnsupportedImageFormatError):
        ImageLoader().load(
            path,
            TEST_IMAGE_INPUT_LIMITS,
        )


def test_tiff_content_cannot_be_decoded_at_all(
    tmp_path: Path,
) -> None:
    """
    TIFF is outside the supported format set defined by ADR-0016.

    The rejection is stronger than a format mismatch: the decoder is
    deregistered, so the content is not identifiable rather than
    identified and refused. That closes the container through which
    TIFF-based RAW formats would otherwise reach a decoder.
    """
    path = tmp_path / "image.png"

    Image.new(
        "RGB",
        (4, 3),
        (10, 20, 30),
    ).save(
        path,
        format="TIFF",
    )

    with pytest.raises(CorruptedImageError):
        ImageLoader().load(
            path,
            TEST_IMAGE_INPUT_LIMITS,
        )


def test_tiff_is_not_a_reachable_decoder() -> None:
    assert "TIFF" not in reachable_image_decoders()


def test_unsupported_extension_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "image.psd"
    path.write_bytes(b"8BPS")

    with pytest.raises(UnsupportedImageFormatError):
        ImageLoader().load(
            path,
            TEST_IMAGE_INPUT_LIMITS,
        )


def test_unsupported_content_behind_an_accepted_extension_is_rejected(
    tmp_path: Path,
) -> None:
    """
    A GIF is a reachable format for the library but not for this project.
    """
    path = tmp_path / "actually_gif.png"

    Image.new(
        "P",
        (4, 3),
    ).save(
        path,
        format="GIF",
    )

    with pytest.raises(
        (UnsupportedImageFormatError, CorruptedImageError),
    ):
        ImageLoader().load(
            path,
            TEST_IMAGE_INPUT_LIMITS,
        )


def test_non_image_content_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "image.png"
    path.write_bytes(b"not an image at all")

    with pytest.raises(CorruptedImageError):
        ImageLoader().load(
            path,
            TEST_IMAGE_INPUT_LIMITS,
        )


def test_empty_file_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "image.png"
    path.write_bytes(b"")

    with pytest.raises(CorruptedImageError):
        ImageLoader().load(
            path,
            TEST_IMAGE_INPUT_LIMITS,
        )
