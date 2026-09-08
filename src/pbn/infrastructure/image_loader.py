# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from pbn.core.image_input_rules import ImageInputLimits, ImageInputRules
from pbn.exceptions import (
    CorruptedImageError,
    ImageError,
    ImageNotFoundError,
    ImageTooLargeError,
    UnsupportedImageFormatError,
)
from pbn.models import ImageSize, InputImage

from .image_decoder_policy import (
    SUPPORTED_IMAGE_FORMATS,
    restrict_image_decoders,
)

# Applied at import so that no caller can reach the loader while
# unsupported decoders are still registered.
restrict_image_decoders()

_EXTENSION_FORMATS = {
    ".bmp": "BMP",
    ".jpeg": "JPEG",
    ".jpg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}

_SUPPORTED_EXTENSIONS = frozenset(_EXTENSION_FORMATS)

_MULTI_PICTURE_FORMAT = "MPO"
"""
The format the library reports for a JPEG carrying an MPF index.

Not a separate file type. Phones attach auxiliary frames, a depth or
gain map, inside an ordinary JPEG, and the JPEG factory reclasses the
opened image when it finds the index. Such a file is a JPEG by every
other measure, including its extension and the first bytes on disk.
"""

_MP_ENTRY_TAG = 0xB002
"""
The MPF tag holding one entry per embedded frame, in order.
"""

_PRIMARY_MP_TYPE = "Baseline MP Primary Image"
"""
The only MP type that designates a primary image.

The remaining values the library decodes are thumbnails, panorama and
multi-angle frames, and `Undefined` for a code it does not know. A first
entry carrying any of those is not a container whose frame zero is the
picture, so it is refused.
"""

_MP_JPEG_DATA_FORMAT = "JPEG"


class ImageLoader:
    """
    Central image loading service.

    Every load applies the configured input limits. The limits are a
    required argument rather than an optional caller responsibility, so
    that no interface can reach decoding without them.
    """

    def __init__(self) -> None:
        self._rules = ImageInputRules()

    def load(
        self,
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage:
        """
        Load and normalize an image within the given limits.

        The returned image is independent of Pillow and represents
        normalized RGB pixel data.

        Every failure leaves as an `ImageError`, per ADR-0019. Decoders
        raise more than `OSError` on hostile content, and the set is not
        enumerable from their documentation, so anything that is not
        already a decision of this loader is translated here rather than
        reaching a caller as an unhandled exception. The original is
        kept as the cause, so the operator still sees what happened.
        """
        try:
            return self._load(
                image_path,
                limits,
            )

        except ImageError:
            # A decision this loader already made and classified.
            raise

        except Exception as exc:
            raise CorruptedImageError(
                f"Unable to read image: {image_path}",
            ) from exc

    def _load(
        self,
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage:
        if not image_path.exists():
            raise ImageNotFoundError(
                f"Image does not exist: {image_path}",
            )

        if not image_path.is_file():
            raise ImageNotFoundError(
                f"Not a file: {image_path}",
            )

        suffix = image_path.suffix.lower()

        if suffix not in _SUPPORTED_EXTENSIONS:
            raise UnsupportedImageFormatError(
                f"Unsupported image format: {image_path.suffix}",
            )

        return self._load_raster(
            image_path,
            limits,
        )

    def _load_raster(
        self,
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage:
        expected_format = _EXTENSION_FORMATS[image_path.suffix.lower()]

        try:
            with (
                self._decompression_bombs_as_errors(limits),
                Image.open(image_path) as image,
            ):
                self._ensure_accepted_format(
                    image_path,
                    image,
                    expected_format,
                )

                # Header only so far. The declared dimensions decide
                # acceptance before any pixel data is materialized.
                self._rules.ensure_within_limits(
                    ImageSize(
                        width=image.width,
                        height=image.height,
                    ),
                    limits,
                )

                target = self._rules.processing_size(
                    ImageSize(
                        width=image.width,
                        height=image.height,
                    ),
                    limits,
                )

                # Lets a JPEG decode directly at a reduced scale and is
                # a no-op for the other supported formats.
                image.draft(
                    "RGB",
                    (
                        target.width,
                        target.height,
                    ),
                )

                # A separate name, because the opened handle and the
                # processed image are different types.
                processed = ImageOps.exif_transpose(
                    image,
                )
                processed = self._reduce(
                    processed,
                    target,
                )

                return self._to_input_image(
                    processed.convert("RGB"),
                )

        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            # Neither derives from OSError, so both need naming here. The
            # promoted warning arrives as an exception, and both mean the
            # declared dimensions exceed the accepted maximum.
            raise ImageTooLargeError(
                f"Image exceeds the accepted pixel limit: {image_path}",
            ) from exc

        except UnidentifiedImageError as exc:
            raise CorruptedImageError(
                f"Unable to decode image: {image_path}",
            ) from exc

        except OSError as exc:
            # Covers truncated and otherwise unreadable input.
            raise CorruptedImageError(
                f"Unable to decode image: {image_path}",
            ) from exc

    @staticmethod
    @contextmanager
    def _decompression_bombs_as_errors(
        limits: ImageInputLimits,
    ) -> Iterator[None]:
        """
        Make the imaging library's own pixel bound take effect.

        The library reports images above its pixel limit as a warning that
        a caller may ignore, and only raises above twice that limit. The
        warning is promoted to an error for the duration of one decode, and
        the limit is set to the configured maximum.
        """
        previous_limit = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = limits.maximum_pixel_count

        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "error",
                    Image.DecompressionBombWarning,
                )

                yield
        finally:
            Image.MAX_IMAGE_PIXELS = previous_limit

    @staticmethod
    def _reduce(
        image: Image.Image,
        target: ImageSize,
    ) -> Image.Image:
        """
        Reduce an accepted image to the processing resolution.
        """
        if (image.width, image.height) == (
            target.width,
            target.height,
        ):
            return image

        return image.resize(
            (
                target.width,
                target.height,
            ),
            Image.Resampling.LANCZOS,
        )

    @staticmethod
    def _to_input_image(
        image: Image.Image,
    ) -> InputImage:
        """
        Materialize normalized pixel data.

        The compact representation is the decoder's own byte buffer, so no
        per-pixel object is created here.
        """
        width, height = image.size

        return InputImage(
            width=width,
            height=height,
            pixels=image.tobytes(),
        )

    @staticmethod
    def _ensure_accepted_format(
        image_path: Path,
        image: Image.Image,
        expected_format: str,
    ) -> None:
        """
        Reject content whose detected format is not the expected one.

        The extension only states which format is claimed. The decoder is
        chosen by content, so the detected format decides acceptance.

        One exception, and only one: a JPEG the library reports as `MPO`
        because it carries auxiliary frames. See `_is_jpeg_with_auxiliary_frames`
        for what has to hold. Everything else is refused as before.
        """
        detected_format = image.format

        if detected_format is None:
            raise UnsupportedImageFormatError(
                f"Image format could not be detected: {image_path}",
            )

        if ImageLoader._is_jpeg_with_auxiliary_frames(
            image,
            detected_format,
            expected_format,
        ):
            return

        if detected_format not in SUPPORTED_IMAGE_FORMATS:
            raise UnsupportedImageFormatError(
                f"Unsupported image format: {detected_format}",
            )

        if detected_format != expected_format:
            raise UnsupportedImageFormatError(
                f"Image content is {detected_format} but the file "
                f"extension claims {expected_format}: {image_path}",
            )

    @staticmethod
    def _is_jpeg_with_auxiliary_frames(
        image: Image.Image,
        detected_format: str,
        expected_format: str,
    ) -> bool:
        """
        Report whether this is a JPEG carrying an MPF index.

        Three conditions, all required. The extension must claim JPEG,
        so this never widens what a file of another name may be. The
        library must have reported `MPO`, which it does only through the
        JPEG factory: `MPO` is removed from the decoder registry, so no
        file reaches this by being sniffed as one. And the first MPF
        entry must declare a JPEG primary image, which is what makes
        frame zero the picture rather than one member of a set.

        Anything malformed is a `False` rather than an error, so such a
        file is refused with the same message as any other unsupported
        format and a caller learns nothing from the difference.

        Only frame zero is ever read. Nothing here seeks, and the loader
        does not either, so the auxiliary frames are neither decoded nor
        counted against the limits, which were applied to frame zero's
        declared size.
        """
        if expected_format != "JPEG":
            return False

        if detected_format != _MULTI_PICTURE_FORMAT:
            return False

        entries = getattr(
            image,
            "mpinfo",
            None,
        )

        if not isinstance(
            entries,
            dict,
        ):
            return False

        frames = entries.get(
            _MP_ENTRY_TAG,
        )

        if (
            not isinstance(
                frames,
                list,
            )
            or not frames
        ):
            return False

        primary = frames[0]

        if not isinstance(
            primary,
            dict,
        ):
            return False

        attributes = primary.get(
            "Attribute",
        )

        if not isinstance(
            attributes,
            dict,
        ):
            return False

        return (
            attributes.get(
                "ImageDataFormat",
            )
            == _MP_JPEG_DATA_FORMAT
            and attributes.get(
                "MPType",
            )
            == _PRIMARY_MP_TYPE
        )


def load_image(
    image_path: Path,
    limits: ImageInputLimits,
) -> InputImage:
    """
    Load and normalize an image within the given limits.
    """
    return ImageLoader().load(
        image_path,
        limits,
    )
