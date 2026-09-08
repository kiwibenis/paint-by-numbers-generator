# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pbn.models import Lab


class ColorDistance(Protocol):
    """
    Calculates the distance between two CIELAB colors.
    """

    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        """
        Return the color distance between two CIELAB colors.
        """
        ...


@runtime_checkable
class ColorDistanceRanking(Protocol):
    """
    Provides an order-preserving value for color-distance comparisons.
    """

    def ranking_value(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        """
        Return a value preserving the ordering of the color distance.
        """
        ...


@runtime_checkable
class ColorDistanceSquaredProjectionLowerBound(Protocol):
    """
    Provides a scalar lower bound for ranking comparisons.

    The squared difference between two projections must not exceed the
    ranking value between the corresponding colors.
    """

    def projection(
        self,
        color: Lab,
    ) -> float:
        """
        Return the scalar projection used for ranking lower bounds.
        """
        ...
