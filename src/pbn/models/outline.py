# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[int, int]
Ring = tuple[Point, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class Outline:
    """
    Polygon describing the border of a region.
    """

    region_id: int
    points: Ring
    hole_rings: tuple[Ring, ...] = ()
