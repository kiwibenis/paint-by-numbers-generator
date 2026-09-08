# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import XYZ


def test_xyz_model() -> None:
    color = XYZ(
        x=12.5,
        y=22.7,
        z=91.2,
    )

    assert color.x == 12.5
    assert color.y == 22.7
    assert color.z == 91.2

    assert color.as_tuple() == (
        12.5,
        22.7,
        91.2,
    )
