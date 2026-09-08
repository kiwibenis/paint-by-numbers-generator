# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageSize:
    """
    Immutable physical page size in millimetres.
    """

    width_mm: float
    height_mm: float


A4 = PageSize(
    width_mm=210.0,
    height_mm=297.0,
)

A3 = PageSize(
    width_mm=297.0,
    height_mm=420.0,
)
