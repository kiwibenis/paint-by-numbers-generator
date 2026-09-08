# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from collections.abc import Callable
from typing import cast

import pytest

from pbn.color import DeltaE76
from pbn.models import Lab


def test_identical_colors_have_zero_distance() -> None:
    delta = DeltaE76()

    color = Lab(
        l=50.0,
        a=20.0,
        b=-10.0,
    )

    assert delta.distance(
        color,
        color,
    ) == pytest.approx(0.0)


def test_distance_uses_euclidean_lab_distance() -> None:
    delta = DeltaE76()

    first = Lab(
        l=10.0,
        a=20.0,
        b=30.0,
    )

    second = Lab(
        l=13.0,
        a=24.0,
        b=30.0,
    )

    assert delta.distance(
        first,
        second,
    ) == pytest.approx(5.0)


def test_distance_is_symmetric() -> None:
    delta = DeltaE76()

    first = Lab(
        l=40.0,
        a=10.0,
        b=-20.0,
    )

    second = Lab(
        l=70.0,
        a=-5.0,
        b=15.0,
    )

    assert delta.distance(
        first,
        second,
    ) == pytest.approx(
        delta.distance(
            second,
            first,
        ),
    )


def test_ranking_value_uses_squared_euclidean_lab_distance() -> None:
    delta = DeltaE76()

    first = Lab(
        l=10.0,
        a=20.0,
        b=30.0,
    )

    second = Lab(
        l=13.0,
        a=24.0,
        b=30.0,
    )

    assert delta.ranking_value(
        first,
        second,
    ) == pytest.approx(25.0)


def test_projection_uses_lab_lightness() -> None:
    delta = DeltaE76()

    color = Lab(
        l=42.5,
        a=18.0,
        b=-7.0,
    )

    projection = cast(
        Callable[[Lab], float],
        delta.projection,
    )

    assert projection(
        color,
    ) == pytest.approx(42.5)


def test_squared_projection_difference_is_ranking_lower_bound() -> None:
    delta = DeltaE76()

    first = Lab(
        l=10.0,
        a=20.0,
        b=30.0,
    )

    second = Lab(
        l=13.0,
        a=24.0,
        b=35.0,
    )

    projection = cast(
        Callable[[Lab], float],
        delta.projection,
    )

    projection_difference = projection(first) - projection(second)

    assert projection_difference * projection_difference <= delta.ranking_value(
        first,
        second,
    )
