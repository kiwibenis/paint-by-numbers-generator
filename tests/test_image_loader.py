# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pathlib import Path

import pytest
from PIL import Image

from pbn.exceptions import (
    ImageNotFoundError,
)
from pbn.infrastructure import (
    ImageLoader,
    load_image,
)
from pbn.models import (
    RGB,
    InputImage,
)
from tests.image_limits import TEST_IMAGE_INPUT_LIMITS


@pytest.mark.parametrize(
    ("suffix", "image_format"),
    (
        (".jpg", "JPEG"),
        (".jpeg", "JPEG"),
        (".png", "PNG"),
        (".bmp", "BMP"),
        (".webp", "WEBP"),
    ),
)
def test_load_normalizes_supported_raster_formats(
    tmp_path: Path,
    suffix: str,
    image_format: str,
) -> None:
    image_file = tmp_path / f"input{suffix}"

    with Image.new(
        "RGB",
        (2, 1),
        (10, 20, 30),
    ) as image:
        image.putpixel(
            (1, 0),
            (40, 50, 60),
        )
        image.save(
            image_file,
            format=image_format,
        )

    loader = ImageLoader()

    result = loader.load(
        image_file,
        TEST_IMAGE_INPUT_LIMITS,
    )

    assert isinstance(result, InputImage)

    assert result.width == 2
    assert result.height == 1

    assert len(tuple(result.rows())) == 1
    assert len(result.rows_at(0)) == 2

    for pixel in result.rows_at(0):
        assert isinstance(pixel, RGB)


def test_load_returns_normalized_input_image(tmp_path: Path) -> None:
    image_file = tmp_path / "input.png"

    with Image.new(
        "RGBA",
        (2, 1),
        (10, 20, 30, 255),
    ) as image:
        image.putpixel(
            (1, 0),
            (40, 50, 60, 255),
        )
        image.save(image_file)

    loader = ImageLoader()

    result = loader.load(
        image_file,
        TEST_IMAGE_INPUT_LIMITS,
    )

    assert isinstance(result, InputImage)

    assert result.width == 2
    assert result.height == 1

    assert tuple(result.rows()) == (
        (
            RGB(
                red=10,
                green=20,
                blue=30,
            ),
            RGB(
                red=40,
                green=50,
                blue=60,
            ),
        ),
    )


def test_load_preserves_raster_row_order(
    tmp_path: Path,
) -> None:
    image_file = tmp_path / "input.png"

    with Image.new(
        "RGB",
        (2, 2),
    ) as image:
        image.putpixel(
            (0, 0),
            (10, 20, 30),
        )
        image.putpixel(
            (1, 0),
            (40, 50, 60),
        )
        image.putpixel(
            (0, 1),
            (70, 80, 90),
        )
        image.putpixel(
            (1, 1),
            (100, 110, 120),
        )
        image.save(image_file)

    result = ImageLoader().load(
        image_file,
        TEST_IMAGE_INPUT_LIMITS,
    )

    assert tuple(result.rows()) == (
        (
            RGB(
                red=10,
                green=20,
                blue=30,
            ),
            RGB(
                red=40,
                green=50,
                blue=60,
            ),
        ),
        (
            RGB(
                red=70,
                green=80,
                blue=90,
            ),
            RGB(
                red=100,
                green=110,
                blue=120,
            ),
        ),
    )


def test_missing_file() -> None:
    with pytest.raises(ImageNotFoundError):
        load_image(
            Path("does_not_exist.jpg"),
            TEST_IMAGE_INPUT_LIMITS,
        )
