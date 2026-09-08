# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError
from math import pi

import pytest

from pbn.models import RegionMergeMetrics


def _metrics() -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=12.5,
        source_area=20,
        target_area=80,
        merged_area=100,
        affected_area_ratio=0.2,
        shared_border_length=7,
        source_perimeter=18,
        target_perimeter=36,
        merged_perimeter=40,
    )


def test_region_merge_metrics_store_raw_values() -> None:
    metrics = _metrics()

    assert metrics.color_difference == 12.5
    assert metrics.source_area == 20
    assert metrics.target_area == 80
    assert metrics.merged_area == 100
    assert metrics.affected_area_ratio == 0.2
    assert metrics.shared_border_length == 7
    assert metrics.source_perimeter == 18
    assert metrics.target_perimeter == 36
    assert metrics.merged_perimeter == 40


def test_region_merge_metrics_calculate_source_compactness() -> None:
    metrics = _metrics()

    assert metrics.source_compactness == pytest.approx(
        20.0 * pi / 81.0,
    )


def test_region_merge_metrics_calculate_source_non_compactness() -> None:
    metrics = _metrics()

    assert metrics.source_non_compactness == pytest.approx(
        1.0 - 20.0 * pi / 81.0,
    )


def test_region_merge_metrics_are_immutable() -> None:
    metrics = _metrics()

    with pytest.raises(FrozenInstanceError):
        # The assignment is the assertion: the model is frozen, so
        # mypy is right that this is a static error and the test
        # exists to prove it is a runtime one too.
        metrics.source_area = 30  # type: ignore[misc]
