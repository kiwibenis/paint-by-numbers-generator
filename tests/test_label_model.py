# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.models import Label


def test_label() -> None:
    label = Label(
        region_id=7,
        text="7",
        position=(10.5, 20.5),
    )

    assert label.region_id == 7
    assert label.text == "7"
    assert label.position == (
        10.5,
        20.5,
    )
