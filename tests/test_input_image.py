# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.models import (
    RGB,
    InputImage,
)


def test_input_image_stores_dimensions_and_pixels() -> None:
    black = RGB(
        red=0,
        green=0,
        blue=0,
    )

    white = RGB(
        red=255,
        green=255,
        blue=255,
    )

    image = InputImage.from_rows(
        (
            (
                black,
                white,
            ),
        )
    )

    assert image.width == 2
    assert image.height == 1
    assert tuple(image.rows()) == (
        (
            black,
            white,
        ),
    )


def test_input_image_is_immutable() -> None:
    image = InputImage.from_rows(
        (
            (
                RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
            ),
        )
    )

    attribute_name = "width"

    with pytest.raises(FrozenInstanceError):
        setattr(
            image,
            attribute_name,
            2,
        )
