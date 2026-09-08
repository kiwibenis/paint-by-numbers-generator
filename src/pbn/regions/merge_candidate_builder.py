# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    Region,
    RegionMergeCandidate,
    RegionMergeMetrics,
)

from .adjacency import RegionAdjacency
from .merge_metrics_calculator import RegionMergeMetricsCalculator


class RegionMergeCandidateBuilder:
    """
    Build initial directed merge candidates and their raw metrics.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
    ) -> None:
        self._adjacency = RegionAdjacency()
        self._metrics_calculator = RegionMergeMetricsCalculator(
            color_distance=color_distance,
        )

    def build(
        self,
        regions: tuple[Region, ...],
    ) -> tuple[
        tuple[
            RegionMergeCandidate,
            RegionMergeMetrics,
        ],
        ...,
    ]:
        """
        Return deterministic directed candidates between adjacent regions.
        """
        shared_borders = self._adjacency.shared_borders(
            regions,
        )
        regions_by_id = {region.id: region for region in regions}

        return self.build_from_shared_borders(
            regions_by_id=regions_by_id,
            shared_borders=shared_borders,
            touching_region_ids=None,
        )

    def build_from_shared_borders(
        self,
        *,
        regions_by_id: dict[int, Region],
        shared_borders: dict[int, dict[int, int]],
        touching_region_ids: frozenset[int] | None,
    ) -> tuple[
        tuple[
            RegionMergeCandidate,
            RegionMergeMetrics,
        ],
        ...,
    ]:
        """
        Build candidates from existing adjacency information.
        """
        candidates = tuple(
            RegionMergeCandidate(
                source_id=source_id,
                target_id=target_id,
            )
            for source_id in sorted(
                shared_borders,
            )
            for target_id in sorted(
                shared_borders[source_id],
            )
            if (
                touching_region_ids is None
                or source_id in touching_region_ids
                or target_id in touching_region_ids
            )
        )

        return tuple(
            (
                candidate,
                self._metrics_calculator.calculate(
                    candidate=candidate,
                    regions=regions_by_id,
                    shared_borders=shared_borders,
                ),
            )
            for candidate in candidates
        )
