# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import XYZ, Lab

from .constants import (
    REF_X,
    REF_Y,
    REF_Z,
)
from .math import lab_f


class XyzToLabConverter:
    """
    Converts XYZ colors to the CIELAB color space (D65).
    """

    def convert(
        self,
        xyz: XYZ,
    ) -> Lab:
        """
        Convert a CIE XYZ color to CIELAB.
        """

        x = lab_f(xyz.x / REF_X)
        y = lab_f(xyz.y / REF_Y)
        z = lab_f(xyz.z / REF_Z)

        return Lab(
            l=(116 * y) - 16,
            a=500 * (x - y),
            b=200 * (y - z),
        )
