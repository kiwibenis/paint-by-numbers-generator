# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Constants used for color space conversions.

Reference:
IEC 61966-2-1 (sRGB)
CIE 1931 XYZ
D65 reference white
"""

from __future__ import annotations

# D65 reference white (normalized)

REF_X = 0.95047
REF_Y = 1.00000
REF_Z = 1.08883

# sRGB -> XYZ conversion matrix

RGB_TO_XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
