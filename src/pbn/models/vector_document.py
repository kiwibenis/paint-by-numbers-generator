# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

from .label import Label
from .outline import Outline


@dataclass(frozen=True, slots=True)
class VectorDocument:
    """
    Format-independent outlines and labels in a coordinate space.

    The generated document carries project-owned vector geometry and palette
    identity without depending on a concrete output serialization format.
    """

    outlines: tuple[Outline, ...]
    labels: tuple[Label, ...]
    palette_id: str | None = None
    palette_version: int | None = None

    def __post_init__(self) -> None:
        if (self.palette_id is None) != (self.palette_version is None):
            raise ValueError(
                "palette_id and palette_version must be provided together",
            )
