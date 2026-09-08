# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import math

from pbn.models import Lab


class DeltaE76:
    """
    Calculates CIE76 color differences in the CIELAB color space.
    """

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        """
        Return the CIE76 color difference between two CIELAB colors.
        """

        return math.sqrt(
            self.ranking_value(
                first,
                second,
            ),
        )

    def ranking_value(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        """
        Return the squared CIE76 distance for ordering comparisons.
        """

        delta_l = first.l - second.l
        delta_a = first.a - second.a
        delta_b = first.b - second.b

        return delta_l * delta_l + delta_a * delta_a + delta_b * delta_b

    def projection(
        self,
        color: Lab,
    ) -> float:
        """
        Return Lab lightness for squared-distance lower bounds.
        """

        return color.l
