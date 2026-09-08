# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.color import XyzToLabConverter
from pbn.models import XYZ


def test_black() -> None:
    converter = XyzToLabConverter()

    lab = converter.convert(
        XYZ(
            x=0.0,
            y=0.0,
            z=0.0,
        )
    )

    assert lab.l == pytest.approx(0.0, abs=0.001)
    assert lab.a == pytest.approx(0.0, abs=0.001)
    assert lab.b == pytest.approx(0.0, abs=0.001)


def test_white() -> None:
    converter = XyzToLabConverter()

    lab = converter.convert(
        XYZ(
            x=0.95047,
            y=1.00000,
            z=1.08883,
        )
    )

    assert lab.l == pytest.approx(100.0, abs=0.01)
    assert lab.a == pytest.approx(0.0, abs=0.01)
    assert lab.b == pytest.approx(0.0, abs=0.01)


def test_gray() -> None:
    converter = XyzToLabConverter()

    lab = converter.convert(
        XYZ(
            x=0.20344,
            y=0.21404,
            z=0.23305,
        )
    )

    assert lab.l == pytest.approx(53.4, abs=0.2)
