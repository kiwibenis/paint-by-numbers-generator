# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import math

from pbn.models import Lab

_DEGREES_TO_RADIANS = math.pi / 180.0
_RADIANS_TO_DEGREES = 180.0 / math.pi
_CHROMA_REFERENCE_TO_SEVENTH = 25.0**7


class DeltaE2000:
    """
    Calculates CIEDE2000 color differences in the CIELAB color space.
    """

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        """
        Return the CIEDE2000 color difference between two CIELAB colors.
        """

        chroma_first = math.hypot(
            first.a,
            first.b,
        )
        chroma_second = math.hypot(
            second.a,
            second.b,
        )

        mean_chroma = (chroma_first + chroma_second) / 2.0

        mean_chroma_to_seventh = mean_chroma**7

        adjustment = 0.5 * (
            1.0
            - math.sqrt(
                mean_chroma_to_seventh
                / (mean_chroma_to_seventh + _CHROMA_REFERENCE_TO_SEVENTH)
            )
        )

        adjusted_a_first = (1.0 + adjustment) * first.a
        adjusted_a_second = (1.0 + adjustment) * second.a

        adjusted_chroma_first = math.hypot(
            adjusted_a_first,
            first.b,
        )
        adjusted_chroma_second = math.hypot(
            adjusted_a_second,
            second.b,
        )

        hue_first = (
            math.atan2(
                first.b,
                adjusted_a_first,
            )
            * _RADIANS_TO_DEGREES
        ) % 360.0

        hue_second = (
            math.atan2(
                second.b,
                adjusted_a_second,
            )
            * _RADIANS_TO_DEGREES
        ) % 360.0

        delta_lightness = second.l - first.l

        delta_chroma = adjusted_chroma_second - adjusted_chroma_first

        chroma_product = adjusted_chroma_first * adjusted_chroma_second

        hue_difference = hue_second - hue_first

        if chroma_product == 0.0:
            delta_hue_angle = 0.0
        elif abs(hue_difference) <= 180.0:
            delta_hue_angle = hue_difference
        elif hue_difference > 180.0:
            delta_hue_angle = hue_difference - 360.0
        else:
            delta_hue_angle = hue_difference + 360.0

        delta_hue = (
            2.0
            * math.sqrt(
                chroma_product,
            )
            * math.sin((delta_hue_angle / 2.0) * _DEGREES_TO_RADIANS)
        )

        mean_lightness = (first.l + second.l) / 2.0

        mean_adjusted_chroma = (adjusted_chroma_first + adjusted_chroma_second) / 2.0

        hue_sum = hue_first + hue_second
        absolute_hue_difference = abs(hue_first - hue_second)

        if chroma_product == 0.0:
            mean_hue = hue_sum
        elif absolute_hue_difference <= 180.0:
            mean_hue = hue_sum / 2.0
        elif hue_sum < 360.0:
            mean_hue = (hue_sum + 360.0) / 2.0
        else:
            mean_hue = (hue_sum - 360.0) / 2.0

        hue_weight = (
            1.0
            - 0.17 * math.cos((mean_hue - 30.0) * _DEGREES_TO_RADIANS)
            + 0.24 * math.cos((2.0 * mean_hue) * _DEGREES_TO_RADIANS)
            + 0.32 * math.cos((3.0 * mean_hue + 6.0) * _DEGREES_TO_RADIANS)
            - 0.20 * math.cos((4.0 * mean_hue - 63.0) * _DEGREES_TO_RADIANS)
        )

        rotation_angle = 30.0 * math.exp(-(((mean_hue - 275.0) / 25.0) ** 2))

        mean_adjusted_chroma_to_seventh = mean_adjusted_chroma**7

        rotation_chroma = 2.0 * math.sqrt(
            mean_adjusted_chroma_to_seventh
            / (mean_adjusted_chroma_to_seventh + _CHROMA_REFERENCE_TO_SEVENTH)
        )

        lightness_offset = mean_lightness - 50.0

        lightness_weight = 1.0 + (0.015 * lightness_offset**2) / math.sqrt(
            20.0 + lightness_offset**2
        )

        chroma_weight = 1.0 + 0.045 * mean_adjusted_chroma

        hue_scale = 1.0 + 0.015 * mean_adjusted_chroma * hue_weight

        rotation_term = (
            -math.sin((2.0 * rotation_angle) * _DEGREES_TO_RADIANS) * rotation_chroma
        )

        lightness_component = delta_lightness / lightness_weight
        chroma_component = delta_chroma / chroma_weight
        hue_component = delta_hue / hue_scale

        return math.sqrt(
            lightness_component**2
            + chroma_component**2
            + hue_component**2
            + (rotation_term * chroma_component * hue_component)
        )
