# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from PIL import Image

from pbn.infrastructure.image_decoder_policy import (
    SUPPORTED_IMAGE_FORMATS,
    reachable_image_decoders,
    restrict_image_decoders,
)

# Importing the loader must apply the restriction as a side effect.
import pbn.infrastructure.image_loader  # noqa: F401  isort:skip

_KNOWN_VULNERABLE_DECODERS = (
    "EPS",
    "PSD",
)


def test_only_supported_decoders_remain_reachable() -> None:
    assert reachable_image_decoders() == tuple(
        sorted(SUPPORTED_IMAGE_FORMATS),
    )


def test_decoders_with_known_vulnerability_history_are_unreachable() -> None:
    reachable = reachable_image_decoders()

    for format_id in _KNOWN_VULNERABLE_DECODERS:
        assert format_id not in reachable


def test_extensions_of_removed_decoders_are_unregistered() -> None:
    for extension, format_id in Image.EXTENSION.items():
        assert format_id in SUPPORTED_IMAGE_FORMATS, extension


def test_mime_types_of_removed_decoders_are_unregistered() -> None:
    for format_id in Image.MIME:
        assert format_id in SUPPORTED_IMAGE_FORMATS


def test_identifier_list_matches_the_reachable_decoders() -> None:
    assert set(Image.ID) <= set(SUPPORTED_IMAGE_FORMATS)


def test_restriction_is_idempotent() -> None:
    before = reachable_image_decoders()

    assert restrict_image_decoders() == ()
    assert reachable_image_decoders() == before


def test_every_supported_format_remains_reachable() -> None:
    for format_id in SUPPORTED_IMAGE_FORMATS:
        assert format_id in Image.OPEN
