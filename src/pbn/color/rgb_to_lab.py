# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import RGB, Lab

from .rgb_to_xyz import RgbToXyzConverter
from .xyz_to_lab import XyzToLabConverter


class RgbToLabConverter:
    """
    Converts sRGB colors directly to CIELAB.
    """

    def __init__(self) -> None:
        self._rgb_to_xyz = RgbToXyzConverter()
        self._xyz_to_lab = XyzToLabConverter()

    def convert(
        self,
        rgb: RGB,
    ) -> Lab:
        xyz = self._rgb_to_xyz.convert(rgb)

        return self._xyz_to_lab.convert(xyz)
