# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

from pbn.models import Region

from .adjacency import RegionAdjacency
from .circle_fit import RegionCircleFit


@dataclass(frozen=True, slots=True)
class RegionPaintabilityStatus:
    """
    Describe undersized regions after mandatory paintability processing.
    """

    undersized_region_ids: tuple[int, ...]
    mergeable_undersized_region_ids: tuple[int, ...]


class RegionPaintabilityVerifier:
    """
    Verify the state produced by mandatory paintability merging.
    """

    def __init__(self) -> None:
        self._adjacency = RegionAdjacency()
        self._circle_fit = RegionCircleFit()

    def evaluate(
        self,
        regions: tuple[Region, ...],
        minimum_circle_diameter_px: int,
    ) -> RegionPaintabilityStatus:
        """
        Report undersized regions and those that still have merge targets.
        """
        undersized_region_ids = tuple(
            sorted(
                region.id
                for region in regions
                if not self._circle_fit.fits(
                    region=region,
                    diameter_px=minimum_circle_diameter_px,
                )
            ),
        )

        if not undersized_region_ids:
            return RegionPaintabilityStatus(
                undersized_region_ids=(),
                mergeable_undersized_region_ids=(),
            )

        shared_borders = self._adjacency.shared_borders(
            regions,
        )

        mergeable_undersized_region_ids = tuple(
            region_id
            for region_id in undersized_region_ids
            if shared_borders[region_id]
        )

        return RegionPaintabilityStatus(
            undersized_region_ids=undersized_region_ids,
            mergeable_undersized_region_ids=(mergeable_undersized_region_ids),
        )
