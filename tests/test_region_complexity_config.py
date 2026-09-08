# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.application.generator_config_builder import (
    build_region_complexity_config,
)
from pbn.config import (
    RegionComplexityConfig,
    RegionMergeCostConfig,
)
from pbn.exceptions import ConfigurationError


def create_merge_cost_config() -> RegionMergeCostConfig:
    return RegionMergeCostConfig(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )


def create_values() -> dict[str, object]:
    return {
        "region_complexity_reduction_enabled": True,
        "max_regions": 500,
        "maximum_merge_cost": 0.300,
        "merge_cost_color_weight": 0.40,
        "merge_cost_affected_area_weight": 0.25,
        "merge_cost_border_weight": 0.15,
        "merge_cost_geometry_weight": 0.20,
        "merge_cost_enclosure_strength": 0.50,
        "merge_cost_compactness_strength": 0.15,
    }


def test_region_complexity_config_preserves_policy_values() -> None:
    merge_cost = create_merge_cost_config()

    config = RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=500,
        maximum_merge_cost=0.300,
        merge_cost=merge_cost,
    )

    assert config.reduction_enabled is True
    assert config.max_regions == 500
    assert config.maximum_merge_cost == 0.300
    assert config.merge_cost is merge_cost


def test_region_complexity_config_is_immutable() -> None:
    config = RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=500,
        maximum_merge_cost=0.300,
        merge_cost=create_merge_cost_config(),
    )

    with pytest.raises(FrozenInstanceError):
        # The assignment is the assertion: the model is frozen, so
        # mypy is right that this is a static error and the test
        # exists to prove it is a runtime one too.
        config.max_regions = 400  # type: ignore[misc]


def test_build_region_complexity_config_preserves_policy_values() -> None:
    config = build_region_complexity_config(
        create_values(),
    )

    assert config == RegionComplexityConfig(
        reduction_enabled=True,
        max_regions=500,
        maximum_merge_cost=0.300,
        merge_cost=create_merge_cost_config(),
    )


def test_build_region_complexity_config_requires_every_value() -> None:
    values = create_values()
    del values["maximum_merge_cost"]

    with pytest.raises(
        ConfigurationError,
        match=(
            "Missing required region-complexity configuration values: "
            "maximum_merge_cost"
        ),
    ):
        build_region_complexity_config(
            values,
        )


def test_build_region_complexity_config_requires_policy_when_disabled() -> None:
    values = create_values()
    values["region_complexity_reduction_enabled"] = False
    del values["max_regions"]

    with pytest.raises(
        ConfigurationError,
        match=(
            "Missing required region-complexity configuration values: " "max_regions"
        ),
    ):
        build_region_complexity_config(
            values,
        )


def test_build_region_complexity_config_requires_boolean_enabled() -> None:
    values = create_values()
    values["region_complexity_reduction_enabled"] = 1

    with pytest.raises(
        ConfigurationError,
        match=(
            "Configuration value region_complexity_reduction_enabled "
            "must be a boolean"
        ),
    ):
        build_region_complexity_config(
            values,
        )


@pytest.mark.parametrize(
    "value",
    (
        0,
        -1,
    ),
)
def test_build_region_complexity_config_rejects_non_positive_max_regions(
    value: int,
) -> None:
    values = create_values()
    values["max_regions"] = value

    with pytest.raises(
        ConfigurationError,
        match="region_complexity.max_regions must be greater than zero",
    ):
        build_region_complexity_config(
            values,
        )


@pytest.mark.parametrize(
    ("value", "expected_error"),
    (
        (
            float("nan"),
            "region_complexity.maximum_merge_cost must be finite",
        ),
        (
            float("inf"),
            "region_complexity.maximum_merge_cost must be finite",
        ),
        (
            -0.01,
            "region_complexity.maximum_merge_cost must be between 0.0 and 1.0",
        ),
        (
            1.01,
            "region_complexity.maximum_merge_cost must be between 0.0 and 1.0",
        ),
    ),
)
def test_build_region_complexity_config_rejects_invalid_maximum_merge_cost(
    value: float,
    expected_error: str,
) -> None:
    values = create_values()
    values["maximum_merge_cost"] = value

    with pytest.raises(
        ConfigurationError,
        match=expected_error,
    ):
        build_region_complexity_config(
            values,
        )


@pytest.mark.parametrize(
    "value",
    (
        0.0,
        1.0,
    ),
)
def test_build_region_complexity_config_accepts_merge_cost_boundaries(
    value: float,
) -> None:
    values = create_values()
    values["maximum_merge_cost"] = value

    config = build_region_complexity_config(
        values,
    )

    assert config.maximum_merge_cost == value
