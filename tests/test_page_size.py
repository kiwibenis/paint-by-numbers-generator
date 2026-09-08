# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.models import A3, A4, PageSize


def test_a4_page_size() -> None:
    assert A4.width_mm == 210.0
    assert A4.height_mm == 297.0


def test_a3_page_size() -> None:
    assert A3.width_mm == 297.0
    assert A3.height_mm == 420.0


def test_page_size_is_immutable() -> None:
    page_size = PageSize(
        width_mm=210.0,
        height_mm=297.0,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(  # noqa: B010
            page_size,
            "width_mm",
            300.0,
        )
