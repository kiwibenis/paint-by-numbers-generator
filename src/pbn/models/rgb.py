# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass

MAXIMUM_CHANNEL_VALUE = 255


@dataclass(frozen=True, slots=True)
class RGB:
    """
    Represents one RGB color.
    """

    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        """
        Reject channel values outside the representable range.

        Validating here covers every construction path rather than only
        the ones a caller remembered to check.
        """
        for name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{name} must be an integer.",
                )

            if not 0 <= value <= MAXIMUM_CHANNEL_VALUE:
                raise ValueError(
                    f"{name} must be between 0 and " f"{MAXIMUM_CHANNEL_VALUE}.",
                )

    def as_tuple(self) -> tuple[int, int, int]:
        """Return the color as an RGB tuple."""
        return (
            self.red,
            self.green,
            self.blue,
        )
