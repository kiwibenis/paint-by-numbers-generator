# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.models import ImageSize


def test_image_size_stores_dimensions() -> None:
    image_size = ImageSize(
        width=4032,
        height=3024,
    )

    assert image_size.width == 4032
    assert image_size.height == 3024


def test_image_size_is_immutable() -> None:
    image_size = ImageSize(
        width=4032,
        height=3024,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(  # noqa: B010
            image_size,
            "width",
            3000,
        )
