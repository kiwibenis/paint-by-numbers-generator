# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

from .orientation import Orientation
from .page_size import PageSize


@dataclass(frozen=True, slots=True)
class PhysicalOutputGeometry:
    """
    Immutable physical output geometry.
    """

    page_size: PageSize
    orientation: Orientation

    @property
    def width_mm(self) -> float:
        if self.orientation is Orientation.PORTRAIT:
            return self.page_size.width_mm

        return self.page_size.height_mm

    @property
    def height_mm(self) -> float:
        if self.orientation is Orientation.PORTRAIT:
            return self.page_size.height_mm

        return self.page_size.width_mm
