# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.application import (
    ConfiguredRegionComplexityReducer,
    build_region_complexity_reducer,
    region_complexity_reducer_factory,
)
from pbn.color import DeltaE76
from pbn.config import (
    RegionComplexityConfig,
    RegionMergeCostConfig,
)


def create_config(
    *,
    reduction_enabled: bool,
) -> RegionComplexityConfig:
    return RegionComplexityConfig(
        reduction_enabled=reduction_enabled,
        max_regions=500,
        maximum_merge_cost=0.300,
        merge_cost=RegionMergeCostConfig(
            color_weight=0.40,
            affected_area_weight=0.25,
            border_weight=0.15,
            geometry_weight=0.20,
            enclosure_strength=0.50,
            compactness_strength=0.15,
        ),
    )


def test_build_region_complexity_reducer_returns_none_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_build_merge_cost_calculator(
        config: RegionMergeCostConfig,
    ) -> object:
        raise AssertionError(
            "Merge-cost calculator must not be built when disabled.",
        )

    monkeypatch.setattr(
        region_complexity_reducer_factory,
        "build_region_merge_cost_calculator",
        fail_build_merge_cost_calculator,
    )

    reducer = build_region_complexity_reducer(
        create_config(
            reduction_enabled=False,
        ),
        DeltaE76(),
    )

    assert reducer is None


def test_build_region_complexity_reducer_builds_core_reducer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = create_config(
        reduction_enabled=True,
    )
    color_distance = DeltaE76()
    cost_calculator = object()
    captured: dict[str, object] = {}

    def fake_build_merge_cost_calculator(
        merge_cost_config: RegionMergeCostConfig,
    ) -> object:
        captured["merge_cost_config"] = merge_cost_config
        return cost_calculator

    class FakeRegionComplexityReducer:
        def __init__(
            self,
            *,
            color_distance: object,
            cost_calculator: object,
        ) -> None:
            captured["color_distance"] = color_distance
            captured["cost_calculator"] = cost_calculator

        def reduce(
            self,
            regions: tuple[object, ...],
            *,
            minimum_circle_diameter_px: int,
            max_regions: int,
            maximum_merge_cost: float,
        ) -> tuple[object, ...]:
            captured["regions"] = regions
            captured["minimum_circle_diameter_px"] = minimum_circle_diameter_px
            captured["max_regions"] = max_regions
            captured["maximum_merge_cost"] = maximum_merge_cost

            return regions

    monkeypatch.setattr(
        region_complexity_reducer_factory,
        "build_region_merge_cost_calculator",
        fake_build_merge_cost_calculator,
    )
    monkeypatch.setattr(
        region_complexity_reducer_factory,
        "RegionComplexityReducer",
        FakeRegionComplexityReducer,
    )

    reducer = build_region_complexity_reducer(
        config,
        color_distance,
    )

    assert isinstance(
        reducer,
        ConfiguredRegionComplexityReducer,
    )

    assert captured["merge_cost_config"] is config.merge_cost
    assert captured["color_distance"] is color_distance
    assert captured["cost_calculator"] is cost_calculator

    result = reducer.reduce(
        (),
        minimum_circle_diameter_px=6,
    )

    assert result == ()
    assert captured["regions"] == ()
    assert captured["minimum_circle_diameter_px"] == 6
    assert captured["max_regions"] == 500
    assert captured["maximum_merge_cost"] == 0.300
