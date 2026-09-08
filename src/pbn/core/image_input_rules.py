# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from math import floor, sqrt
from typing import Protocol

from pbn.exceptions import ImageTooLargeError
from pbn.models import ImageSize


class ImageInputLimits(Protocol):
    """
    Structural type for the bounds an input image must satisfy.

    ``maximum_pixel_count``, ``maximum_width`` and ``maximum_height``
    bound what may be decoded at all. ``processing_pixel_count`` is the
    resolution an accepted image is reduced to before pixel data is
    materialized.
    """

    @property
    def maximum_pixel_count(self) -> int: ...

    @property
    def maximum_width(self) -> int: ...

    @property
    def maximum_height(self) -> int: ...

    @property
    def processing_pixel_count(self) -> int: ...


class ImageInputRules:
    """
    Decide whether an input image is acceptable and how it is reduced.

    The rules operate on dimensions alone and never on pixel data, so they
    can be applied before any unbounded allocation.
    """

    def validate_limits(
        self,
        limits: ImageInputLimits,
    ) -> None:
        """
        Reject limit values that cannot bound anything.
        """
        if limits.maximum_pixel_count < 1:
            raise ValueError(
                "maximum_pixel_count must be at least one",
            )

        if limits.maximum_width < 1:
            raise ValueError(
                "maximum_width must be at least one",
            )

        if limits.maximum_height < 1:
            raise ValueError(
                "maximum_height must be at least one",
            )

        if limits.processing_pixel_count < 1:
            raise ValueError(
                "processing_pixel_count must be at least one",
            )

        if limits.processing_pixel_count > limits.maximum_pixel_count:
            raise ValueError(
                "processing_pixel_count must not exceed " "maximum_pixel_count",
            )

    def ensure_within_limits(
        self,
        size: ImageSize,
        limits: ImageInputLimits,
    ) -> None:
        """
        Raise when the decoded dimensions exceed the accepted bounds.
        """
        if size.width < 1 or size.height < 1:
            raise ImageTooLargeError(
                "Image has no pixels.",
            )

        if size.width > limits.maximum_width:
            raise ImageTooLargeError(
                f"Image width {size.width} exceeds the accepted maximum "
                f"of {limits.maximum_width}.",
            )

        if size.height > limits.maximum_height:
            raise ImageTooLargeError(
                f"Image height {size.height} exceeds the accepted maximum "
                f"of {limits.maximum_height}.",
            )

        pixel_count = size.width * size.height

        if pixel_count > limits.maximum_pixel_count:
            raise ImageTooLargeError(
                f"Image pixel count {pixel_count} exceeds the accepted "
                f"maximum of {limits.maximum_pixel_count}.",
            )

    def processing_size(
        self,
        size: ImageSize,
        limits: ImageInputLimits,
    ) -> ImageSize:
        """
        Return the size an accepted image is processed at.

        Images at or below the processing resolution are returned unchanged.
        Larger images are reduced proportionally so that the resulting pixel
        count does not exceed the processing resolution. Both edges stay at
        least one pixel.
        """
        pixel_count = size.width * size.height

        if pixel_count <= limits.processing_pixel_count:
            return size

        scale = sqrt(
            limits.processing_pixel_count / pixel_count,
        )

        width = max(
            1,
            floor(
                size.width * scale,
            ),
        )
        height = max(
            1,
            floor(
                size.height * scale,
            ),
        )

        # Clamping an edge back up to one pixel can push an extreme aspect
        # ratio above the target again, so bound the longer edge explicitly.
        if width * height > limits.processing_pixel_count:
            if width >= height:
                width = max(
                    1,
                    limits.processing_pixel_count // height,
                )
            else:
                height = max(
                    1,
                    limits.processing_pixel_count // width,
                )

        return ImageSize(
            width=width,
            height=height,
        )
