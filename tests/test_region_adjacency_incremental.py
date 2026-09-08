# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.regions import RegionAdjacency


def test_update_after_merge_combines_source_borders_into_target() -> None:
    shared_borders = {
        1: {
            2: 2,
            3: 4,
        },
        2: {
            1: 2,
            3: 3,
            4: 1,
        },
        3: {
            1: 4,
            2: 3,
        },
        4: {
            2: 1,
        },
    }

    RegionAdjacency().update_after_merge(
        shared_borders,
        source_id=2,
        target_id=1,
    )

    assert shared_borders == {
        1: {
            3: 7,
            4: 1,
        },
        3: {
            1: 7,
        },
        4: {
            1: 1,
        },
    }
