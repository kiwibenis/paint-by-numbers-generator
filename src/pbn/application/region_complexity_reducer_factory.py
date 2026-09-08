# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.color.color_distance import ColorDistance
from pbn.config import RegionComplexityConfig
from pbn.models import Region
from pbn.regions.complexity_reducer import RegionComplexityReducer

from .region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)


class ConfiguredRegionComplexityReducer:
    """
    Apply validated region-complexity policy through the Core reducer.
    """

    def __init__(
        self,
        reducer: RegionComplexityReducer,
        *,
        max_regions: int,
        maximum_merge_cost: float,
    ) -> None:
        self._reducer = reducer
        self._max_regions = max_regions
        self._maximum_merge_cost = maximum_merge_cost

    def reduce(
        self,
        regions: tuple[Region, ...],
        *,
        minimum_circle_diameter_px: int,
    ) -> tuple[Region, ...]:
        """
        Apply optional complexity reduction with configured policy values.
        """
        return self._reducer.reduce(
            regions,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
            max_regions=self._max_regions,
            maximum_merge_cost=self._maximum_merge_cost,
        )


def build_region_complexity_reducer(
    config: RegionComplexityConfig,
    color_distance: ColorDistance,
) -> ConfiguredRegionComplexityReducer | None:
    """
    Build the configured optional Core reducer when reduction is enabled.
    """
    if not config.reduction_enabled:
        return None

    cost_calculator = build_region_merge_cost_calculator(
        config.merge_cost,
    )

    reducer = RegionComplexityReducer(
        color_distance=color_distance,
        cost_calculator=cost_calculator,
    )

    return ConfiguredRegionComplexityReducer(
        reducer,
        max_regions=config.max_regions,
        maximum_merge_cost=config.maximum_merge_cost,
    )
