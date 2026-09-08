# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from PIL import Image

SUPPORTED_IMAGE_FORMATS: tuple[str, ...] = (
    "BMP",
    "JPEG",
    "PNG",
    "WEBP",
)
"""
Formats this project accepts.

TIFF is absent deliberately, per ADR-0016. Every widely used RAW format
is TIFF-based, so accepting TIFF accepts the container all of them
arrive in.
"""


def restrict_image_decoders(
    supported_formats: tuple[str, ...] = SUPPORTED_IMAGE_FORMATS,
) -> tuple[str, ...]:
    """
    Remove every decoder the project does not support from the registry.

    The imaging library detects formats by content, so an extension
    allowlist does not decide which decoder runs. Unsupported decoders are
    therefore removed from the registry itself and become unreachable
    rather than merely undocumented.

    This mutates process-wide state of the imaging library and is applied
    when this package's image loading module is imported, so that no caller
    can reach the loader without the restriction being in effect.

    Removing an entry from the registry does not remove every code path
    that a plugin can still be reached through. The JPEG factory can still
    produce an MPO image from JPEG-compatible content, for example. The
    loader therefore also validates the detected format of an opened image
    against the supported set, so that such a path is rejected rather than
    processed.

    ADR-0016 admits that MPO result only under its narrow JPEG
    auxiliary-frame exception. `MPO` stays out of this registry: the
    exception is reachable only through the JPEG factory after the
    extension has been checked, and registering the decoder would make it
    reachable by content sniffing behind any accepted name.

    Returns the format identifiers that were removed.
    """
    Image.init()

    removed = tuple(
        sorted(
            set(Image.OPEN) - set(supported_formats),
        ),
    )

    for format_id in removed:
        Image.OPEN.pop(
            format_id,
            None,
        )

        if format_id in Image.ID:
            Image.ID.remove(
                format_id,
            )

    for format_id in list(
        Image.MIME,
    ):
        if format_id not in supported_formats:
            Image.MIME.pop(
                format_id,
                None,
            )

    for extension, format_id in list(
        Image.EXTENSION.items(),
    ):
        if format_id not in supported_formats:
            Image.EXTENSION.pop(
                extension,
                None,
            )

    return removed


def reachable_image_decoders() -> tuple[str, ...]:
    """
    Return the format identifiers that can currently be decoded.
    """
    return tuple(
        sorted(
            Image.OPEN,
        ),
    )
