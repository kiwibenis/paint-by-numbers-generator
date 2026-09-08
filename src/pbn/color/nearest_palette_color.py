# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable

from pbn.exceptions import InvariantViolationError
from pbn.models import Lab, Palette, PaletteColor

from .color_distance import (
    ColorDistance,
    ColorDistanceRanking,
    ColorDistanceSquaredProjectionLowerBound,
)

_INFINITY = float("inf")


class NearestPaletteColorFinder:
    """
    Finds the nearest palette color using a configured color distance.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
    ) -> None:
        self._color_distance = color_distance

        self._ranking_value: Callable[
            [Lab, Lab],
            float,
        ]

        if isinstance(
            self._color_distance,
            ColorDistanceRanking,
        ):
            self._ranking_value = self._color_distance.ranking_value
        else:
            self._ranking_value = self._color_distance.distance

        self._projection: (
            Callable[
                [Lab],
                float,
            ]
            | None
        ) = None

        if isinstance(
            self._color_distance,
            ColorDistanceRanking,
        ) and isinstance(
            self._color_distance,
            ColorDistanceSquaredProjectionLowerBound,
        ):
            self._projection = self._color_distance.projection

        self._projected_palette: Palette | None = None

        self._projected_candidates: tuple[
            tuple[
                float,
                int,
                PaletteColor,
            ],
            ...,
        ] = ()

        self._projection_values: tuple[
            float,
            ...,
        ] = ()

    def find(
        self,
        color: Lab,
        palette: Palette,
    ) -> PaletteColor:
        """
        Find the closest color in the palette.
        """

        colors = palette.colors

        if not colors:
            raise ValueError("Palette contains no colors.")

        projection = self._projection

        if projection is None:
            return self._find_linear(
                color,
                colors,
            )

        if palette is not self._projected_palette:
            projected_candidates = [
                (
                    projection(candidate.lab),
                    index,
                    candidate,
                )
                for index, candidate in enumerate(
                    colors,
                )
            ]

            projected_candidates.sort(
                key=lambda item: item[0],
            )

            self._projected_candidates = tuple(
                projected_candidates,
            )

            self._projection_values = tuple(item[0] for item in projected_candidates)

            self._projected_palette = palette

        return self._find_projected(
            color,
            projection(color),
        )

    def _find_linear(
        self,
        color: Lab,
        colors: tuple[PaletteColor, ...],
    ) -> PaletteColor:
        ranking_value = self._ranking_value
        candidates = iter(colors)

        nearest = next(candidates)
        shortest_ranking_value = ranking_value(
            color,
            nearest.lab,
        )

        for candidate in candidates:
            candidate_ranking_value = ranking_value(
                color,
                candidate.lab,
            )

            if candidate_ranking_value < shortest_ranking_value:
                shortest_ranking_value = candidate_ranking_value
                nearest = candidate

        return nearest

    def _find_projected(
        self,
        color: Lab,
        projection: float,
    ) -> PaletteColor:
        candidates = self._projected_candidates
        projection_values = self._projection_values
        ranking_value = self._ranking_value
        candidate_count = len(candidates)
        infinity = _INFINITY

        right = bisect_left(
            projection_values,
            projection,
        )
        left = right - 1

        if left >= 0:
            left_difference = projection - projection_values[left]
            left_lower_bound = left_difference * left_difference
        else:
            left_lower_bound = infinity

        if right < candidate_count:
            right_difference = projection_values[right] - projection
            right_lower_bound = right_difference * right_difference
        else:
            right_lower_bound = infinity

        nearest: PaletteColor | None = None
        nearest_index = candidate_count
        shortest_ranking_value = infinity

        while left >= 0 or right < candidate_count:
            if right_lower_bound <= left_lower_bound:
                if right_lower_bound > shortest_ranking_value:
                    break

                _, candidate_index, candidate = candidates[right]
                right += 1

                if right < candidate_count:
                    right_difference = projection_values[right] - projection
                    right_lower_bound = right_difference * right_difference
                else:
                    right_lower_bound = infinity
            else:
                if left_lower_bound > shortest_ranking_value:
                    break

                _, candidate_index, candidate = candidates[left]
                left -= 1

                if left >= 0:
                    left_difference = projection - projection_values[left]
                    left_lower_bound = left_difference * left_difference
                else:
                    left_lower_bound = infinity

            candidate_ranking_value = ranking_value(
                color,
                candidate.lab,
            )

            if candidate_ranking_value < shortest_ranking_value or (
                candidate_ranking_value == shortest_ranking_value
                and candidate_index < nearest_index
            ):
                shortest_ranking_value = candidate_ranking_value
                nearest_index = candidate_index
                nearest = candidate

        if nearest is None:
            raise InvariantViolationError(
                "Projected palette search produced no candidate.",
            )

        return nearest
