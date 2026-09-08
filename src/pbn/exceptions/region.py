# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class RegionError(PbnError):
    """
    Base class for region-related errors.
    """

    public_message: ClassVar[str] = (
        "The image could not be converted into paintable regions."
    )
    caused_by_request: ClassVar[bool] = True


class RegionPaintabilityError(RegionError):
    """
    Mandatory paintability processing could not satisfy the constraint.

    Whether an image can be reduced to paintable regions depends on the
    image, so this is attributed to the request even though the
    configured minimum size is operator data.
    """

    public_message: ClassVar[str] = (
        "The image could not be converted into paintable regions."
    )
    caused_by_request: ClassVar[bool] = True
