# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Input limits for developer-only measurement utilities.

The generation pipeline requires explicit input limits for every load.
Benchmarks and evaluations are not an untrusted boundary, and they must
keep measuring the same workload as before those limits existed. This
profile therefore accepts the repository's reference images unchanged and
performs no reduction, so that measured values stay comparable.

It is not a default and must not be used by the application.
"""

from __future__ import annotations

from pbn.config import ImageInputLimitsConfig

DEVELOPER_IMAGE_INPUT_LIMITS = ImageInputLimitsConfig(
    maximum_pixel_count=400_000_000,
    maximum_width=20_000,
    maximum_height=20_000,
    processing_pixel_count=400_000_000,
)
