# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations


def srgb_to_linear(value: int) -> float:
    """
    Convert one 8-bit sRGB component into linear RGB.
    """

    channel = value / 255.0

    if channel <= 0.04045:
        return channel / 12.92

    return float(((channel + 0.055) / 1.055) ** 2.4)


def lab_f(value: float) -> float:
    """
    CIE helper function used for XYZ -> Lab conversion.
    """

    delta = 6 / 29

    if value > delta**3:
        return float(value ** (1 / 3))

    return value / (3 * delta**2) + (4 / 29)
