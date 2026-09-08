# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import (
    RegionMergeCandidate,
    RegionMergeCost,
    RegionMergeMetrics,
)
from tools.benchmark_region_complexity import CandidateDiagnostic
from tools.evaluate_region_detail_preservation import (
    DetailPreservationEvaluation,
)
from tools.evaluate_region_source_compactness import (
    format_initial_source_shape_evaluation,
    format_source_shape_diagnostic,
)


def _metrics(
    *,
    source_area: int,
    source_perimeter: int,
) -> RegionMergeMetrics:
    return RegionMergeMetrics(
        color_difference=20.0,
        source_area=source_area,
        target_area=100,
        merged_area=source_area + 100,
        affected_area_ratio=(source_area / (source_area + 100)),
        shared_border_length=10,
        source_perimeter=source_perimeter,
        target_perimeter=40,
        merged_perimeter=(source_perimeter + 20),
    )


def _diagnostic(
    *,
    source_area: int,
    source_perimeter: int,
) -> CandidateDiagnostic:
    metrics = _metrics(
        source_area=source_area,
        source_perimeter=source_perimeter,
    )

    return CandidateDiagnostic(
        candidate=RegionMergeCandidate(
            source_id=1,
            target_id=2,
        ),
        source_color_number=101,
        source_color_name="Source",
        target_color_number=102,
        target_color_name="Target",
        source_bounds=(0, 0, 9, 9),
        target_bounds=(0, 0, 19, 19),
        metrics=metrics,
        cost=RegionMergeCost(
            color_penalty=0.5,
            affected_area_penalty=(metrics.affected_area_ratio),
            border_penalty=0.5,
            geometry_penalty=0.0,
            value=0.4,
        ),
    )


def test_format_source_shape_diagnostic_reports_shape_metrics() -> None:
    diagnostic = _diagnostic(
        source_area=100,
        source_perimeter=40,
    )

    formatted = format_source_shape_diagnostic(
        diagnostic,
        step_number=3,
    )

    assert "step=3" in formatted
    assert "source_id=1" in formatted
    assert "target_id=2" in formatted
    assert "source_area=100" in formatted
    assert "source_perimeter=40" in formatted
    assert "source_geometry_complexity=16.000000" in formatted
    assert "source_compactness=0.785398" in formatted
    assert "source_non_compactness=0.214602" in formatted


def test_format_initial_source_shape_reports_adjusted_ranking() -> None:
    diagnostic = _diagnostic(
        source_area=100,
        source_perimeter=40,
    )

    evaluation = DetailPreservationEvaluation(
        diagnostic=diagnostic,
        protection_penalty=0.25,
        adjusted_cost=0.55,
    )

    formatted = format_initial_source_shape_evaluation(
        evaluation,
        rank=7,
    )

    assert "rank=7" in formatted
    assert "source_id=1" in formatted
    assert "target_id=2" in formatted
    assert "base_cost=0.400000" in formatted
    assert "adjusted_cost=0.550000" in formatted
    assert "detail_preservation_penalty=0.250000" in formatted
    assert "source_area=100" in formatted
    assert "source_perimeter=40" in formatted
    assert "source_geometry_complexity=16.000000" in formatted
    assert "source_compactness=0.785398" in formatted
    assert "source_non_compactness=0.214602" in formatted
    assert "source_shared_border_ratio=0.250000" in formatted
