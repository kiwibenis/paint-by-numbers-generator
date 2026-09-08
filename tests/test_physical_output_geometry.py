# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.models import (
    A3,
    A4,
    Orientation,
    PhysicalOutputGeometry,
)


def test_physical_output_geometry_is_immutable() -> None:
    geometry = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.PORTRAIT,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(  # noqa: B010
            geometry,
            "page_size",
            A3,
        )


def test_a4_portrait_geometry() -> None:
    geometry = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.PORTRAIT,
    )

    assert geometry.width_mm == 210.0
    assert geometry.height_mm == 297.0


def test_a4_landscape_geometry() -> None:
    geometry = PhysicalOutputGeometry(
        page_size=A4,
        orientation=Orientation.LANDSCAPE,
    )

    assert geometry.width_mm == 297.0
    assert geometry.height_mm == 210.0


def test_a3_portrait_geometry() -> None:
    geometry = PhysicalOutputGeometry(
        page_size=A3,
        orientation=Orientation.PORTRAIT,
    )

    assert geometry.width_mm == 297.0
    assert geometry.height_mm == 420.0


def test_a3_landscape_geometry() -> None:
    geometry = PhysicalOutputGeometry(
        page_size=A3,
        orientation=Orientation.LANDSCAPE,
    )

    assert geometry.width_mm == 420.0
    assert geometry.height_mm == 297.0
