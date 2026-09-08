# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import Outline


class FakeOverlapDetector:
    """
    Deterministic overlap detector for Application-layer tests.
    """

    def overlapping_region_pairs(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[tuple[int, int]]:
        return set()
