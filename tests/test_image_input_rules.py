# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.config import ImageInputLimitsConfig
from pbn.core.image_input_rules import ImageInputRules
from pbn.exceptions import ImageTooLargeError
from pbn.models import ImageSize

PROCESSING_PIXEL_COUNT = 1_600_000


def _limits(
    *,
    maximum_pixel_count: int = 50_000_000,
    maximum_width: int = 20_000,
    maximum_height: int = 20_000,
    processing_pixel_count: int = PROCESSING_PIXEL_COUNT,
) -> ImageInputLimitsConfig:
    return ImageInputLimitsConfig(
        maximum_pixel_count=maximum_pixel_count,
        maximum_width=maximum_width,
        maximum_height=maximum_height,
        processing_pixel_count=processing_pixel_count,
    )


def _size(
    width: int,
    height: int,
) -> ImageSize:
    return ImageSize(
        width=width,
        height=height,
    )


def test_accepted_size_passes() -> None:
    ImageInputRules().ensure_within_limits(
        _size(1000, 1000),
        _limits(),
    )


def test_exact_limits_are_accepted() -> None:
    ImageInputRules().ensure_within_limits(
        _size(20_000, 2_500),
        _limits(maximum_pixel_count=50_000_000),
    )


def test_excessive_width_is_rejected() -> None:
    with pytest.raises(ImageTooLargeError):
        ImageInputRules().ensure_within_limits(
            _size(20_001, 10),
            _limits(),
        )


def test_excessive_height_is_rejected() -> None:
    with pytest.raises(ImageTooLargeError):
        ImageInputRules().ensure_within_limits(
            _size(10, 20_001),
            _limits(),
        )


def test_excessive_pixel_count_is_rejected() -> None:
    with pytest.raises(ImageTooLargeError):
        ImageInputRules().ensure_within_limits(
            _size(19_000, 19_000),
            _limits(),
        )


def test_empty_image_is_rejected() -> None:
    with pytest.raises(ImageTooLargeError):
        ImageInputRules().ensure_within_limits(
            _size(0, 100),
            _limits(),
        )


def test_small_image_is_not_reduced() -> None:
    size = _size(800, 600)

    assert (
        ImageInputRules().processing_size(
            size,
            _limits(),
        )
        == size
    )


def test_image_at_the_processing_limit_is_not_reduced() -> None:
    size = _size(1600, 1000)

    assert (
        ImageInputRules().processing_size(
            size,
            _limits(),
        )
        == size
    )


def test_large_image_is_reduced_below_the_processing_limit() -> None:
    result = ImageInputRules().processing_size(
        _size(6000, 4000),
        _limits(),
    )

    assert result.width * result.height <= PROCESSING_PIXEL_COUNT


def test_reduction_preserves_the_aspect_ratio() -> None:
    original = _size(6000, 4000)

    result = ImageInputRules().processing_size(
        original,
        _limits(),
    )

    assert abs(result.width / result.height - original.width / original.height) < 0.01


def test_reduction_uses_the_available_resolution() -> None:
    result = ImageInputRules().processing_size(
        _size(6000, 4000),
        _limits(),
    )

    assert result.width * result.height > PROCESSING_PIXEL_COUNT * 0.99


@pytest.mark.parametrize(
    "width,height",
    [
        (1_000_000, 2),
        (2, 1_000_000),
        (100_000, 1),
        (1, 100_000),
        (7919, 7919),
        (3, 5),
    ],
)
def test_reduction_never_exceeds_the_processing_limit(
    width: int,
    height: int,
) -> None:
    result = ImageInputRules().processing_size(
        _size(width, height),
        _limits(processing_pixel_count=1000),
    )

    assert result.width >= 1
    assert result.height >= 1
    assert result.width * result.height <= 1000


def test_reduction_keeps_both_edges_at_least_one_pixel() -> None:
    result = ImageInputRules().processing_size(
        _size(1_000_000, 2),
        _limits(processing_pixel_count=1000),
    )

    assert result.height >= 1


def test_limit_validation_accepts_usable_values() -> None:
    ImageInputRules().validate_limits(
        _limits(),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"maximum_pixel_count": 0},
        {"maximum_width": 0},
        {"maximum_height": 0},
        {"processing_pixel_count": 0},
        {"maximum_pixel_count": -1},
    ],
)
def test_limit_validation_rejects_non_positive_values(
    overrides: dict[str, int],
) -> None:
    with pytest.raises(ValueError):
        ImageInputRules().validate_limits(
            _limits(**overrides),
        )


def test_processing_resolution_must_not_exceed_the_maximum() -> None:
    with pytest.raises(ValueError):
        ImageInputRules().validate_limits(
            _limits(
                maximum_pixel_count=1000,
                processing_pixel_count=1001,
            ),
        )
