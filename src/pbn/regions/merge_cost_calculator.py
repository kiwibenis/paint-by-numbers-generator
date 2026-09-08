# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from math import isclose, isfinite

from pbn.models import (
    RegionMergeCost,
    RegionMergeMetrics,
)

_COLOR_SCALE = 10.0


class RegionMergeCostCalculator:
    """
    Calculate normalized base cost for a directed region merge.
    """

    def __init__(
        self,
        *,
        color_weight: float,
        affected_area_weight: float,
        border_weight: float,
        geometry_weight: float,
    ) -> None:
        weights = (
            color_weight,
            affected_area_weight,
            border_weight,
            geometry_weight,
        )

        if any(
            not isfinite(weight) or weight < 0.0 for weight in weights
        ) or not isclose(
            sum(weights),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "Region merge-cost weights must be finite, "
                "non-negative and sum to one.",
            )

        self._color_weight = color_weight
        self._affected_area_weight = affected_area_weight
        self._border_weight = border_weight
        self._geometry_weight = geometry_weight

    def calculate(
        self,
        metrics: RegionMergeMetrics,
    ) -> RegionMergeCost:
        """
        Calculate normalized cost components and their weighted total.
        """
        color_penalty = metrics.color_difference / (
            metrics.color_difference + _COLOR_SCALE
        )

        affected_area_penalty = metrics.affected_area_ratio

        border_penalty = 1.0 - metrics.source_shared_border_ratio

        geometry_penalty = self._geometry_penalty(
            metrics,
        )

        value = (
            self._color_weight * color_penalty
            + self._affected_area_weight * affected_area_penalty
            + self._border_weight * border_penalty
            + self._geometry_weight * geometry_penalty
        )

        return RegionMergeCost(
            color_penalty=color_penalty,
            affected_area_penalty=affected_area_penalty,
            border_penalty=border_penalty,
            geometry_penalty=geometry_penalty,
            value=value,
        )

    @staticmethod
    def _geometry_penalty(
        metrics: RegionMergeMetrics,
    ) -> float:
        positive_geometry_change = max(
            0.0,
            metrics.geometry_change,
        )

        if positive_geometry_change == 0.0:
            return 0.0

        return positive_geometry_change / (
            metrics.target_geometry_complexity + positive_geometry_change
        )


class DetailPreservingRegionMergeCostCalculator(
    RegionMergeCostCalculator,
):
    """
    Calculate the configured detail-preserving directed merge cost.
    """

    def __init__(
        self,
        *,
        color_weight: float,
        affected_area_weight: float,
        border_weight: float,
        geometry_weight: float,
        enclosure_strength: float,
        compactness_strength: float,
    ) -> None:
        _validate_unit_interval(
            name="enclosure_strength",
            value=enclosure_strength,
        )
        _validate_unit_interval(
            name="compactness_strength",
            value=compactness_strength,
        )

        super().__init__(
            color_weight=color_weight,
            affected_area_weight=affected_area_weight,
            border_weight=border_weight,
            geometry_weight=geometry_weight,
        )

        self._enclosure_strength = enclosure_strength
        self._compactness_strength = compactness_strength

    def calculate(
        self,
        metrics: RegionMergeMetrics,
    ) -> RegionMergeCost:
        """
        Apply configured enclosure and compactness protection.
        """
        base_cost = super().calculate(
            metrics,
        )

        enclosure_penalty = (
            metrics.source_shared_border_ratio
            * base_cost.color_penalty
            * (1.0 - metrics.affected_area_ratio)
        )

        enclosure_adjusted_cost = self._adjusted_cost(
            base_cost=base_cost.value,
            protection_penalty=enclosure_penalty,
            strength=self._enclosure_strength,
        )

        compactness_penalty = (
            metrics.source_non_compactness
            * base_cost.color_penalty
            * (1.0 - metrics.affected_area_ratio)
        )

        final_cost = self._adjusted_cost(
            base_cost=enclosure_adjusted_cost,
            protection_penalty=compactness_penalty,
            strength=self._compactness_strength,
        )

        return RegionMergeCost(
            color_penalty=base_cost.color_penalty,
            affected_area_penalty=(base_cost.affected_area_penalty),
            border_penalty=base_cost.border_penalty,
            geometry_penalty=base_cost.geometry_penalty,
            value=final_cost,
        )

    @staticmethod
    def _adjusted_cost(
        *,
        base_cost: float,
        protection_penalty: float,
        strength: float,
    ) -> float:
        return base_cost + strength * protection_penalty * (1.0 - base_cost)


def _validate_unit_interval(
    *,
    name: str,
    value: float,
) -> None:
    """
    Validate one normalized merge-cost configuration value.
    """
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{name} must be finite and between zero and one.",
        )
