# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegionMergeCost:
    """
    Normalized calculated cost for one directed region merge.
    """

    color_penalty: float

    affected_area_penalty: float

    border_penalty: float

    geometry_penalty: float

    value: float

    def __post_init__(self) -> None:
        values = (
            self.color_penalty,
            self.affected_area_penalty,
            self.border_penalty,
            self.geometry_penalty,
            self.value,
        )

        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError(
                "Region merge cost values must be between zero and one",
            )
