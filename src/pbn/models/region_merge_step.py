# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import dataclass

from .region_merge_candidate import RegionMergeCandidate
from .region_merge_cost import RegionMergeCost
from .region_merge_metrics import RegionMergeMetrics


@dataclass(frozen=True, slots=True)
class RegionMergeStep:
    """
    Record one accepted directed region merge at selection time.
    """

    candidate: RegionMergeCandidate
    metrics: RegionMergeMetrics
    cost: RegionMergeCost
