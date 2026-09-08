# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pbn.core.image_input_rules import ImageInputLimits
from pbn.models import InputImage


class ImageLoaderPort(Protocol):
    """
    Loads and normalizes an input image within the given limits.

    Generation reaches its input only through this boundary, so that
    validation is a precondition of generation rather than something a
    caller may have performed. The limits are an argument rather than a
    property of the implementation, so an implementation cannot decide
    which limits apply.
    """

    def load(
        self,
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage: ...
