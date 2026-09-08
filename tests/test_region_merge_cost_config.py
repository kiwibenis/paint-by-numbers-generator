# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.application.generator_config_builder import (
    build_region_merge_cost_config,
)
from pbn.config import RegionMergeCostConfig
from pbn.exceptions import ConfigurationError


def create_values() -> dict[str, object]:
    return {
        "merge_cost_color_weight": 0.40,
        "merge_cost_affected_area_weight": 0.25,
        "merge_cost_border_weight": 0.15,
        "merge_cost_geometry_weight": 0.20,
        "merge_cost_enclosure_strength": 0.50,
        "merge_cost_compactness_strength": 0.15,
    }


def test_region_merge_cost_config_preserves_policy_values() -> None:
    config = RegionMergeCostConfig(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )

    assert config.color_weight == 0.40
    assert config.affected_area_weight == 0.25
    assert config.border_weight == 0.15
    assert config.geometry_weight == 0.20
    assert config.enclosure_strength == 0.50
    assert config.compactness_strength == 0.15


def test_region_merge_cost_config_is_immutable() -> None:
    config = RegionMergeCostConfig(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )

    with pytest.raises(FrozenInstanceError):
        # The assignment is the assertion: the model is frozen, so
        # mypy is right that this is a static error and the test
        # exists to prove it is a runtime one too.
        config.color_weight = 0.50  # type: ignore[misc]


def test_build_region_merge_cost_config_preserves_values() -> None:
    config = build_region_merge_cost_config(
        create_values(),
    )

    assert config == RegionMergeCostConfig(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )


def test_build_region_merge_cost_config_requires_every_value() -> None:
    values = create_values()
    del values["merge_cost_geometry_weight"]

    with pytest.raises(
        ConfigurationError,
        match=(
            "Missing required merge-cost configuration values: "
            "merge_cost_geometry_weight"
        ),
    ):
        build_region_merge_cost_config(
            values,
        )


def test_build_region_merge_cost_config_rejects_non_numeric_value() -> None:
    values = create_values()
    values["merge_cost_color_weight"] = "0.40"

    with pytest.raises(
        ConfigurationError,
        match=("Configuration value merge_cost_color_weight " "must be a number"),
    ):
        build_region_merge_cost_config(
            values,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "expected_error"),
    (
        (
            "merge_cost_color_weight",
            -0.01,
            "merge_cost.color_weight must not be negative",
        ),
        (
            "merge_cost_color_weight",
            float("nan"),
            "merge_cost.color_weight must be finite",
        ),
        (
            "merge_cost_border_weight",
            float("inf"),
            "merge_cost.border_weight must be finite",
        ),
    ),
)
def test_build_region_merge_cost_config_rejects_invalid_weight(
    field_name: str,
    value: float,
    expected_error: str,
) -> None:
    values = create_values()
    values[field_name] = value

    with pytest.raises(
        ConfigurationError,
        match=expected_error,
    ):
        build_region_merge_cost_config(
            values,
        )


def test_build_region_merge_cost_config_requires_weight_sum_one() -> None:
    values = create_values()
    values["merge_cost_color_weight"] = 0.50

    with pytest.raises(
        ConfigurationError,
        match="merge-cost component weights must sum to 1.0",
    ):
        build_region_merge_cost_config(
            values,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "expected_error"),
    (
        (
            "merge_cost_enclosure_strength",
            -0.01,
            "merge_cost.enclosure_strength must be between 0.0 and 1.0",
        ),
        (
            "merge_cost_enclosure_strength",
            1.01,
            "merge_cost.enclosure_strength must be between 0.0 and 1.0",
        ),
        (
            "merge_cost_compactness_strength",
            float("nan"),
            "merge_cost.compactness_strength must be finite",
        ),
        (
            "merge_cost_compactness_strength",
            float("inf"),
            "merge_cost.compactness_strength must be finite",
        ),
    ),
)
def test_build_region_merge_cost_config_rejects_invalid_strength(
    field_name: str,
    value: float,
    expected_error: str,
) -> None:
    values = create_values()
    values[field_name] = value

    with pytest.raises(
        ConfigurationError,
        match=expected_error,
    ):
        build_region_merge_cost_config(
            values,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "merge_cost_enclosure_strength",
        "merge_cost_compactness_strength",
    ),
)
@pytest.mark.parametrize(
    "value",
    (
        0.0,
        1.0,
    ),
)
def test_build_region_merge_cost_config_accepts_strength_boundaries(
    field_name: str,
    value: float,
) -> None:
    values = create_values()
    values[field_name] = value

    config = build_region_merge_cost_config(
        values,
    )

    config_field_name = field_name.removeprefix(
        "merge_cost_",
    )

    assert (
        getattr(
            config,
            config_field_name,
        )
        == value
    )
