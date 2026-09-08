# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.models import RegionMergeCost


def _cost() -> RegionMergeCost:
    return RegionMergeCost(
        color_penalty=0.4,
        affected_area_penalty=0.2,
        border_penalty=0.3,
        geometry_penalty=0.1,
        value=0.3,
    )


def test_region_merge_cost_stores_calculated_components() -> None:
    cost = _cost()

    assert cost.color_penalty == 0.4
    assert cost.affected_area_penalty == 0.2
    assert cost.border_penalty == 0.3
    assert cost.geometry_penalty == 0.1
    assert cost.value == 0.3


def test_region_merge_cost_is_immutable() -> None:
    cost = _cost()

    with pytest.raises(FrozenInstanceError):
        # The assignment is the assertion: the model is frozen, so
        # mypy is right that this is a static error and the test
        # exists to prove it is a runtime one too.
        cost.value = 0.5  # type: ignore[misc]


@pytest.mark.parametrize(
    "field",
    (
        "color_penalty",
        "affected_area_penalty",
        "border_penalty",
        "geometry_penalty",
        "value",
    ),
)
@pytest.mark.parametrize(
    "invalid_value",
    (
        -0.01,
        1.01,
        float("nan"),
    ),
)
def test_region_merge_cost_rejects_values_outside_normalized_range(
    field: str,
    invalid_value: float,
) -> None:
    values = {
        "color_penalty": 0.4,
        "affected_area_penalty": 0.2,
        "border_penalty": 0.3,
        "geometry_penalty": 0.1,
        "value": 0.3,
    }
    values[field] = invalid_value

    with pytest.raises(
        ValueError,
        match="Region merge cost values must be between zero and one",
    ):
        RegionMergeCost(
            **values,
        )
