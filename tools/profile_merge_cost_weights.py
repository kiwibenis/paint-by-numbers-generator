# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The merge-cost weighting a developer tool measures, taken from the profile.

Several tools build their own experimental subclass of
`RegionMergeCostCalculator`. Each one needs the four base weights, and each
one used to inherit them from a default inside the Core class that read
`0.40 / 0.20 / 0.20 / 0.20` while every shipped profile says
`0.40 / 0.25 / 0.15 / 0.20`. The experiments were therefore measured against
a weighting the project does not ship.

The weights are returned as keyword arguments so a call site reads as one
decision rather than four, and so an added weight reaches every tool through
one edit.
"""

from __future__ import annotations

from typing import TypedDict

from pbn.config import GeneratorConfig


class MergeCostWeights(TypedDict):
    """
    The four base merge-cost weights, in constructor keyword form.
    """

    color_weight: float
    affected_area_weight: float
    border_weight: float
    geometry_weight: float


def profile_merge_cost_weights(
    config: GeneratorConfig,
) -> MergeCostWeights:
    """
    Return the base merge-cost weights the given profile specifies.
    """
    merge_cost = config.region_complexity.merge_cost

    return MergeCostWeights(
        color_weight=merge_cost.color_weight,
        affected_area_weight=(merge_cost.affected_area_weight),
        border_weight=merge_cost.border_weight,
        geometry_weight=merge_cost.geometry_weight,
    )
