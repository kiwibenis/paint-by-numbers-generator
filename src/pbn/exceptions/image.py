# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class ImageError(PbnError):
    """
    Base class for image-related errors.
    """

    public_message: ClassVar[str] = "The input image could not be processed."
    caused_by_request: ClassVar[bool] = True


class ImageNotFoundError(ImageError):
    """
    Input image could not be found.

    The public message does not distinguish a missing file from one that
    is not a regular file, because that distinction answers questions
    about the file system rather than about the input.
    """

    public_message: ClassVar[str] = "The input image could not be read."
    caused_by_request: ClassVar[bool] = True


class UnsupportedImageFormatError(ImageError):
    """
    Unsupported image format.
    """

    public_message: ClassVar[str] = "The image format is not supported."
    caused_by_request: ClassVar[bool] = True


class ImageTooLargeError(ImageError):
    """
    Image exceeds configured limits.
    """

    public_message: ClassVar[str] = "The image exceeds the accepted limits."
    caused_by_request: ClassVar[bool] = True


class CorruptedImageError(ImageError):
    """
    Image cannot be decoded.
    """

    public_message: ClassVar[str] = "The image could not be decoded."
    caused_by_request: ClassVar[bool] = True
