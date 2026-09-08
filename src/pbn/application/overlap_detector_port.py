# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import Protocol

from pbn.models import Outline

RegionPair = tuple[int, int]


class OverlapDetectorPort(Protocol):
    """
    Detects pairwise positive-area overlap between region outlines.
    """

    def overlapping_region_pairs(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[RegionPair]: ...
