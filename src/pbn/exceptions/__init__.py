# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from .base import PbnError
from .configuration import ConfigurationError
from .geometry import (
    GeometryAccelerationError,
    GeometryError,
    GeometryUnavailableError,
)
from .image import (
    CorruptedImageError,
    ImageError,
    ImageNotFoundError,
    ImageTooLargeError,
    UnsupportedImageFormatError,
)
from .internal import InvariantViolationError
from .palette import (
    InvalidPaletteError,
    PaletteCatalogueError,
    PaletteError,
    PaletteNotFoundError,
)
from .pdf import PdfExportError
from .quantization import (
    QuantizationError,
    QuantizationPaletteError,
)
from .region import (
    RegionError,
    RegionPaintabilityError,
)

__all__ = [
    "ConfigurationError",
    "CorruptedImageError",
    "GeometryAccelerationError",
    "GeometryError",
    "GeometryUnavailableError",
    "ImageError",
    "ImageNotFoundError",
    "ImageTooLargeError",
    "InvalidPaletteError",
    "InvariantViolationError",
    "PaletteCatalogueError",
    "PaletteError",
    "PaletteNotFoundError",
    "PbnError",
    "PdfExportError",
    "QuantizationError",
    "QuantizationPaletteError",
    "RegionError",
    "RegionPaintabilityError",
    "UnsupportedImageFormatError",
]
