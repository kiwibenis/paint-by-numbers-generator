# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.application import (
    build_region_merge_cost_calculator,
    region_merge_cost_calculator_factory,
)
from pbn.config import RegionMergeCostConfig
from pbn.regions.merge_cost_calculator import (
    DetailPreservingRegionMergeCostCalculator,
)


def test_build_region_merge_cost_calculator_returns_core_calculator() -> None:
    config = RegionMergeCostConfig(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
        enclosure_strength=0.50,
        compactness_strength=0.15,
    )

    calculator = build_region_merge_cost_calculator(
        config,
    )

    assert isinstance(
        calculator,
        DetailPreservingRegionMergeCostCalculator,
    )


def test_build_region_merge_cost_calculator_passes_all_policy_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = RegionMergeCostConfig(
        color_weight=0.10,
        affected_area_weight=0.20,
        border_weight=0.30,
        geometry_weight=0.40,
        enclosure_strength=0.60,
        compactness_strength=0.70,
    )

    captured: dict[str, float] = {}

    class FakeDetailPreservingRegionMergeCostCalculator:
        def __init__(
            self,
            *,
            color_weight: float,
            affected_area_weight: float,
            border_weight: float,
            geometry_weight: float,
            enclosure_strength: float,
            compactness_strength: float,
        ) -> None:
            captured["color_weight"] = color_weight
            captured["affected_area_weight"] = affected_area_weight
            captured["border_weight"] = border_weight
            captured["geometry_weight"] = geometry_weight
            captured["enclosure_strength"] = enclosure_strength
            captured["compactness_strength"] = compactness_strength

    monkeypatch.setattr(
        region_merge_cost_calculator_factory,
        "DetailPreservingRegionMergeCostCalculator",
        FakeDetailPreservingRegionMergeCostCalculator,
    )

    build_region_merge_cost_calculator(
        config,
    )

    assert captured == {
        "color_weight": 0.10,
        "affected_area_weight": 0.20,
        "border_weight": 0.30,
        "geometry_weight": 0.40,
        "enclosure_strength": 0.60,
        "compactness_strength": 0.70,
    }
