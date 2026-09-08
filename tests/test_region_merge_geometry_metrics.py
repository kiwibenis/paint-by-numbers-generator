# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

import pytest

from pbn.models import RegionMergeMetrics


def _metrics() -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=12.5,
        source_area=2,
        target_area=4,
        merged_area=6,
        affected_area_ratio=2 / 6,
        shared_border_length=2,
        source_perimeter=6,
        target_perimeter=8,
        merged_perimeter=10,
    )


def test_calculate_source_geometry_complexity() -> None:
    metrics = _metrics()

    assert metrics.source_geometry_complexity == pytest.approx(
        18.0,
    )


def test_calculate_target_geometry_complexity() -> None:
    metrics = _metrics()

    assert metrics.target_geometry_complexity == pytest.approx(
        16.0,
    )


def test_calculate_merged_geometry_complexity() -> None:
    metrics = _metrics()

    assert metrics.merged_geometry_complexity == pytest.approx(
        100 / 6,
    )


def test_geometry_change_is_relative_to_directed_target() -> None:
    metrics = _metrics()

    assert metrics.geometry_change == pytest.approx(
        (100 / 6) - 16,
    )


def test_geometry_change_preserves_improvement_direction() -> None:
    metrics = RegionMergeMetrics(
        color_difference=12.5,
        source_area=4,
        target_area=2,
        merged_area=6,
        affected_area_ratio=4 / 6,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=6,
        merged_perimeter=10,
    )

    assert metrics.geometry_change == pytest.approx(
        (100 / 6) - 18,
    )
    assert metrics.geometry_change < 0
