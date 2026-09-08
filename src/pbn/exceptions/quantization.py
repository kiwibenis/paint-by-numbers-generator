# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class QuantizationError(PbnError):
    """
    Base class for quantization failures.
    """

    public_message: ClassVar[str] = "The image could not be reduced to the palette."
    caused_by_request: ClassVar[bool] = True


class QuantizationPaletteError(QuantizationError):
    """
    The image uses more palette colors than an index byte can address.

    Attributed to the request rather than to the operation: the palette
    is operator data, but which of its colors an image reaches is a
    property of the image.
    """

    public_message: ClassVar[str] = (
        "The image uses too many colors for the selected palette."
    )
    caused_by_request: ClassVar[bool] = True
