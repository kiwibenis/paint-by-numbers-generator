# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.color import RgbToLabConverter
from pbn.models import RGB


def test_white() -> None:
    converter = RgbToLabConverter()

    lab = converter.convert(
        RGB(
            red=255,
            green=255,
            blue=255,
        )
    )

    assert lab.l == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert lab.a == pytest.approx(
        0.0,
        abs=0.02,
    )

    assert lab.b == pytest.approx(
        0.0,
        abs=0.02,
    )
