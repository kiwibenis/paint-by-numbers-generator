# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.config import RegionMergeCostConfig
from pbn.regions.merge_cost_calculator import (
    DetailPreservingRegionMergeCostCalculator,
)


def build_region_merge_cost_calculator(
    config: RegionMergeCostConfig,
) -> DetailPreservingRegionMergeCostCalculator:
    """
    Build the Core merge-cost calculator from validated application config.
    """

    return DetailPreservingRegionMergeCostCalculator(
        color_weight=config.color_weight,
        affected_area_weight=config.affected_area_weight,
        border_weight=config.border_weight,
        geometry_weight=config.geometry_weight,
        enclosure_strength=config.enclosure_strength,
        compactness_strength=config.compactness_strength,
    )
