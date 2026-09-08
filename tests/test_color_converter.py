# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.color import (
    DeltaE2000,
    ImageQuantizer,
    NearestPaletteColorFinder,
    RgbToXyzConverter,
    XyzToLabConverter,
)


def test_color_classes_exist() -> None:
    assert RgbToXyzConverter() is not None
    assert XyzToLabConverter() is not None
    assert DeltaE2000() is not None
    assert (
        NearestPaletteColorFinder(
            color_distance=DeltaE2000(),
        )
        is not None
    )
    assert (
        ImageQuantizer(
            color_distance=DeltaE2000(),
        )
        is not None
    )
