# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import ImagePlacement


def test_image_placement_values() -> None:
    assert ImagePlacement.FIT.value == "fit"
    assert ImagePlacement.CROP.value == "crop"
