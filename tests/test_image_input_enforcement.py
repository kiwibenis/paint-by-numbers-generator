# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import struct
import zlib
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from pbn.config import ImageInputLimitsConfig
from pbn.exceptions import (
    CorruptedImageError,
    ImageTooLargeError,
)
from pbn.infrastructure.image_loader import ImageLoader
from tests.image_limits import TEST_IMAGE_INPUT_LIMITS


def _write_png(
    path: Path,
    width: int,
    height: int,
) -> Path:
    Image.new(
        "RGB",
        (width, height),
        (10, 20, 30),
    ).save(
        path,
        format="PNG",
    )

    return path


def _write_png_declaring(
    path: Path,
    width: int,
    height: int,
) -> Path:
    """
    Write a PNG whose header declares a size its data cannot supply.

    Decoding such a file fails, so a successful rejection by size proves
    the size check ran before any pixel data was materialized.
    """
    source = _write_png(
        path.with_suffix(".source.png"),
        4,
        3,
    ).read_bytes()

    signature = source[:8]
    length = struct.unpack(">I", source[8:12])[0]
    header_start = 12
    # The chunk CRC covers the chunk type and its data.
    header_end = header_start + 4 + length
    header = bytearray(source[header_start:header_end])

    header[4:8] = struct.pack(">I", width)
    header[8:12] = struct.pack(">I", height)

    crc = zlib.crc32(bytes(header)) & 0xFFFFFFFF

    path.write_bytes(
        signature
        + source[8:12]
        + bytes(header)
        + struct.pack(">I", crc)
        + source[header_end + 4 :],
    )

    return path


def _limits(
    **overrides: object,
) -> ImageInputLimitsConfig:
    return replace(
        TEST_IMAGE_INPUT_LIMITS,
        **overrides,  # type: ignore[arg-type]
    )


def test_image_within_the_limits_is_accepted(
    tmp_path: Path,
) -> None:
    image = ImageLoader().load(
        _write_png(
            tmp_path / "image.png",
            40,
            30,
        ),
        _limits(),
    )

    assert image.width == 40
    assert image.height == 30


def test_excessive_width_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ImageTooLargeError):
        ImageLoader().load(
            _write_png(
                tmp_path / "image.png",
                40,
                10,
            ),
            _limits(
                maximum_width=39,
                maximum_pixel_count=100,
                processing_pixel_count=100,
            ),
        )


def test_excessive_height_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ImageTooLargeError):
        ImageLoader().load(
            _write_png(
                tmp_path / "image.png",
                10,
                40,
            ),
            _limits(
                maximum_height=39,
                maximum_pixel_count=100,
                processing_pixel_count=100,
            ),
        )


def test_excessive_pixel_count_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ImageTooLargeError):
        ImageLoader().load(
            _write_png(
                tmp_path / "image.png",
                40,
                30,
            ),
            _limits(
                maximum_pixel_count=1_000,
                processing_pixel_count=1_000,
            ),
        )


def test_rejection_happens_before_pixel_data_is_materialized(
    tmp_path: Path,
) -> None:
    """
    The declared size is rejected although the data cannot be decoded.

    A decode attempt would fail with a decoding error instead, so an
    ImageTooLargeError proves that no pixel data was touched.
    """
    path = _write_png_declaring(
        tmp_path / "declared.png",
        30_000,
        30_000,
    )

    with pytest.raises(ImageTooLargeError):
        ImageLoader().load(
            path,
            _limits(
                maximum_pixel_count=1_000_000,
                maximum_width=20_000,
                maximum_height=20_000,
                processing_pixel_count=1_000_000,
            ),
        )


def test_declared_size_above_the_library_bound_is_rejected(
    tmp_path: Path,
) -> None:
    """
    The library reports its own bound as an ignorable warning.

    Promoting it to an error makes the first protection stage take effect
    rather than being skipped.
    """
    path = _write_png_declaring(
        tmp_path / "declared.png",
        4_000,
        4_000,
    )

    with pytest.raises(ImageTooLargeError):
        ImageLoader().load(
            path,
            _limits(
                maximum_pixel_count=1_000_000,
                processing_pixel_count=1_000_000,
            ),
        )


def test_truncated_input_is_rejected_as_a_decoding_error(
    tmp_path: Path,
) -> None:
    source = _write_png(
        tmp_path / "source.png",
        200,
        200,
    ).read_bytes()

    path = tmp_path / "truncated.png"
    path.write_bytes(
        source[: len(source) // 2],
    )

    with pytest.raises(CorruptedImageError):
        ImageLoader().load(
            path,
            _limits(),
        )


def test_oversized_input_is_reduced_to_the_processing_resolution(
    tmp_path: Path,
) -> None:
    image = ImageLoader().load(
        _write_png(
            tmp_path / "image.png",
            600,
            400,
        ),
        _limits(
            processing_pixel_count=60_000,
        ),
    )

    assert image.width * image.height <= 60_000
    assert abs(image.width / image.height - 1.5) < 0.02
    assert len(tuple(image.rows())) == image.height
    assert len(image.rows_at(0)) == image.width


def test_input_below_the_processing_resolution_is_unchanged(
    tmp_path: Path,
) -> None:
    image = ImageLoader().load(
        _write_png(
            tmp_path / "image.png",
            120,
            80,
        ),
        _limits(
            processing_pixel_count=1_000_000,
        ),
    )

    assert image.width == 120
    assert image.height == 80


def test_library_pixel_bound_is_restored_after_loading(
    tmp_path: Path,
) -> None:
    before = Image.MAX_IMAGE_PIXELS

    ImageLoader().load(
        _write_png(
            tmp_path / "image.png",
            10,
            10,
        ),
        _limits(),
    )

    assert Image.MAX_IMAGE_PIXELS == before


def test_library_pixel_bound_is_restored_after_a_rejection(
    tmp_path: Path,
) -> None:
    before = Image.MAX_IMAGE_PIXELS

    with pytest.raises(ImageTooLargeError):
        ImageLoader().load(
            _write_png(
                tmp_path / "image.png",
                40,
                30,
            ),
            _limits(
                maximum_pixel_count=100,
                processing_pixel_count=100,
            ),
        )

    assert Image.MAX_IMAGE_PIXELS == before


def test_truncated_images_are_not_silently_completed() -> None:
    """
    The library can be told to accept truncated data. It must not be.
    """
    from PIL import ImageFile

    assert ImageFile.LOAD_TRUNCATED_IMAGES is False


def test_enforcement_does_not_change_an_input_within_the_limits(
    tmp_path: Path,
) -> None:
    """
    The bounds are a gate, not a transform.

    A caller choosing a stricter profile must get the same result for
    every input that profile still accepts, or the profile would be a
    quality setting in disguise. Compared on the pixels rather than on
    the dimensions, because a check that rescaled would preserve those.
    """
    path = _write_png(
        tmp_path / "within.png",
        120,
        90,
    )

    strict = ImageLoader().load(
        path,
        _limits(
            maximum_width=128,
            maximum_height=128,
            maximum_pixel_count=16_384,
        ),
    )

    permissive = ImageLoader().load(
        path,
        _limits(
            maximum_width=100_000,
            maximum_height=100_000,
            maximum_pixel_count=1_000_000_000,
        ),
    )

    assert strict.width == permissive.width
    assert strict.height == permissive.height
    assert strict.pixels == permissive.pixels
