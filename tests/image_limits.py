# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Input limits used by tests that load images directly.

Loading requires explicit limits, so tests state them rather than relying
on a default. This profile accepts the small fixtures the tests create and
performs no reduction unless a test asks for it.
"""

from __future__ import annotations

from pbn.config import ImageInputLimitsConfig

TEST_IMAGE_INPUT_LIMITS = ImageInputLimitsConfig(
    maximum_pixel_count=50_000_000,
    maximum_width=20_000,
    maximum_height=20_000,
    processing_pixel_count=50_000_000,
)
