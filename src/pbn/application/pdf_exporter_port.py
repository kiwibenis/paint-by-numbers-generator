# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import Protocol

from pbn.config import PdfLegendConfig
from pbn.models import (
    ImagePlacementGeometry,
    Palette,
    PhysicalOutputGeometry,
    VectorDocument,
)


class PdfExporterPort(Protocol):
    def write(
        self,
        document: VectorDocument,
        geometry: PhysicalOutputGeometry,
        legend_geometry: PhysicalOutputGeometry,
        placement: ImagePlacementGeometry,
        palette: Palette,
        legend_config: PdfLegendConfig,
        margin_mm: float,
        font_size_pt: int,
        line_width_pt: float,
        line_color: str,
        number_color: str,
    ) -> bytes: ...
