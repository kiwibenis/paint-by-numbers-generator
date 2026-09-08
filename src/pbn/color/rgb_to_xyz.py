# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import RGB, XYZ

from .constants import RGB_TO_XYZ
from .math import srgb_to_linear


def _channel_contributions(
    matrix_column: int,
) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        (
            linear * RGB_TO_XYZ[0][matrix_column],
            linear * RGB_TO_XYZ[1][matrix_column],
            linear * RGB_TO_XYZ[2][matrix_column],
        )
        for linear in (srgb_to_linear(value) for value in range(256))
    )


_RED_CONTRIBUTIONS = _channel_contributions(0)
_GREEN_CONTRIBUTIONS = _channel_contributions(1)
_BLUE_CONTRIBUTIONS = _channel_contributions(2)


class RgbToXyzConverter:
    """
    Converts sRGB colors to the CIE XYZ color space (D65).
    """

    def convert(
        self,
        rgb: RGB,
    ) -> XYZ:
        """
        Convert an sRGB color to CIE XYZ.
        """

        red_x, red_y, red_z = _RED_CONTRIBUTIONS[rgb.red]
        green_x, green_y, green_z = _GREEN_CONTRIBUTIONS[rgb.green]
        blue_x, blue_y, blue_z = _BLUE_CONTRIBUTIONS[rgb.blue]

        return XYZ(
            x=red_x + green_x + blue_x,
            y=red_y + green_y + blue_y,
            z=red_z + green_z + blue_z,
        )
