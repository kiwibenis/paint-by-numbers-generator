# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pathlib import Path

import pytest

from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.models import (
    RGB,
    ImageSize,
    Lab,
    PaletteColor,
    Region,
    RegionMergeMetrics,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.merge_cost_calculator import RegionMergeCostCalculator
from tools.benchmark_region_complexity import (
    REPOSITORY_ROOT,
    ComplexityReductionResult,
    build_candidate_diagnostics,
    build_region_preview_bmp,
    evaluate_matrix,
    evaluate_reduction,
    format_candidate_diagnostic,
    format_result,
    preview_output_path,
    resolve_max_regions,
    resolve_merge_cost_calculator,
)


class ConstantColorDistance(ColorDistance):
    def distance(
        self,
        first: Lab,
        second: Lab,
    ) -> float:
        return 0.0


def _color(
    number: int,
) -> PaletteColor:
    return PaletteColor(
        number=number,
        name=f"Color {number}",
        rgb=RGB(
            red=number,
            green=number,
            blue=number,
        ),
        lab=Lab(
            l=float(number),
            a=0.0,
            b=0.0,
        ),
    )


def _block_region(
    region_id: int,
    *,
    start_x: int,
) -> Region:
    return Region(
        id=region_id,
        color=_color(region_id),
        pixels=pack_pixels(
            {
                (x, y)
                for x in range(
                    start_x,
                    start_x + 4,
                )
                for y in range(4)
            },
        ),
    )


def _pixel_region(
    region_id: int,
    *,
    x: int,
    rgb: RGB,
) -> Region:
    return Region(
        id=region_id,
        color=PaletteColor(
            number=region_id,
            name=f"Color {region_id}",
            rgb=rgb,
            lab=Lab(
                l=0.0,
                a=0.0,
                b=0.0,
            ),
        ),
        pixels=pack_pixels(
            {
                (x, 0),
            },
        ),
    )


def _weighting_metrics() -> RegionMergeMetrics:
    """
    Return metrics that give every cost component a non-zero value.

    A weighting comparison over metrics that zero a component cannot see a
    difference in that component's weight.
    """
    return RegionMergeMetrics(
        color_difference=20.0,
        source_area=2,
        target_area=4,
        merged_area=8,
        affected_area_ratio=0.25,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=8,
        merged_perimeter=12,
    )


def _base_calculator() -> RegionMergeCostCalculator:
    """
    Return the weighting these tests are written against.

    Stated here rather than left to the calculator, which no longer supplies
    a weighting of its own.
    """
    return RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.25,
        border_weight=0.15,
        geometry_weight=0.20,
    )


def test_resolve_max_regions_uses_target_fraction() -> None:
    assert (
        resolve_max_regions(
            baseline_region_count=10,
            target_fraction=0.75,
        )
        == 8
    )

    assert (
        resolve_max_regions(
            baseline_region_count=10,
            target_fraction=0.50,
        )
        == 5
    )

    assert (
        resolve_max_regions(
            baseline_region_count=10,
            target_fraction=0.01,
        )
        == 1
    )


@pytest.mark.parametrize(
    ("baseline_region_count", "target_fraction"),
    (
        (0, 0.5),
        (10, 0.0),
        (10, -0.1),
        (10, 1.1),
    ),
)
def test_resolve_max_regions_rejects_invalid_values(
    baseline_region_count: int,
    target_fraction: float,
) -> None:
    with pytest.raises(ValueError):
        resolve_max_regions(
            baseline_region_count=baseline_region_count,
            target_fraction=target_fraction,
        )


def test_evaluate_reduction_reports_target_reached() -> None:
    regions = (
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
    )

    result = evaluate_reduction(
        case="test",
        regions=regions,
        color_distance=ConstantColorDistance(),
        minimum_circle_diameter_px=2,
        target_fraction=0.5,
        maximum_merge_cost=1.0,
        cost_calculator=_base_calculator(),
    )

    assert result.baseline_region_count == 2
    assert result.max_regions == 1
    assert result.final_region_count == 1
    assert result.target_reached
    assert result.stop_reason == "target_reached"
    assert result.reduction_fraction == pytest.approx(
        0.5,
    )


def test_evaluate_reduction_reports_quality_boundary_stop() -> None:
    regions = (
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
    )

    result = evaluate_reduction(
        case="test",
        regions=regions,
        color_distance=ConstantColorDistance(),
        minimum_circle_diameter_px=2,
        target_fraction=0.5,
        maximum_merge_cost=0.0,
        cost_calculator=_base_calculator(),
    )

    assert result.final_region_count == 2
    assert not result.target_reached
    assert result.stop_reason == "quality_boundary_or_no_candidate"


def test_evaluate_matrix_preserves_requested_sweep_order() -> None:
    regions = (
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
        _block_region(
            region_id=3,
            start_x=8,
        ),
        _block_region(
            region_id=4,
            start_x=12,
        ),
    )

    results = evaluate_matrix(
        case="test",
        regions=regions,
        color_distance=ConstantColorDistance(),
        minimum_circle_diameter_px=2,
        target_fractions=(
            0.75,
            0.50,
        ),
        maximum_merge_costs=(
            0.0,
            1.0,
        ),
        cost_calculator=_base_calculator(),
    )

    assert tuple(
        (
            result.target_fraction,
            result.maximum_merge_cost,
        )
        for result in results
    ) == (
        (0.75, 0.0),
        (0.75, 1.0),
        (0.50, 0.0),
        (0.50, 1.0),
    )


def test_format_result_reports_reduction_parameters() -> None:
    result = ComplexityReductionResult(
        case="simple",
        baseline_region_count=100,
        target_fraction=0.5,
        max_regions=50,
        maximum_merge_cost=0.25,
        final_region_count=60,
        reduction_seconds=1.25,
    )

    assert format_result(result) == (
        "  target_fraction=0.500, "
        "max_regions=50, "
        "maximum_merge_cost=0.250, "
        "final_regions=60, "
        "reduction=40.00%, "
        "stop=quality_boundary_or_no_candidate, "
        "reducer=1.250s"
    )


def test_build_region_preview_bmp_preserves_palette_colors() -> None:
    regions = (
        _pixel_region(
            region_id=1,
            x=0,
            rgb=RGB(
                red=1,
                green=2,
                blue=3,
            ),
        ),
        _pixel_region(
            region_id=2,
            x=1,
            rgb=RGB(
                red=4,
                green=5,
                blue=6,
            ),
        ),
    )

    bmp = build_region_preview_bmp(
        regions=regions,
        image_size=ImageSize(
            width=2,
            height=1,
        ),
    )

    assert bmp[:2] == b"BM"

    file_size = int.from_bytes(
        bmp[2:6],
        byteorder="little",
    )
    assert file_size == 62

    stored_height = int.from_bytes(
        bmp[22:26],
        byteorder="little",
        signed=True,
    )
    assert stored_height == -1

    assert bmp[54:60] == bytes(
        (
            3,
            2,
            1,
            6,
            5,
            4,
        ),
    )
    assert bmp[60:62] == b"\x00\x00"


def test_build_region_preview_bmp_rejects_out_of_bounds_pixel() -> None:
    region = Region(
        id=1,
        color=_color(1),
        pixels=pack_pixels(
            {
                (2, 0),
            },
        ),
    )

    with pytest.raises(
        ValueError,
        match="Region pixel is outside the preview image",
    ):
        build_region_preview_bmp(
            regions=(region,),
            image_size=ImageSize(
                width=2,
                height=1,
            ),
        )


def test_preview_output_path_identifies_baseline() -> None:
    result = preview_output_path(
        output_directory=Path("output"),
        case="simple",
        result=None,
    )

    assert result == Path(
        "output/region-complexity-simple-baseline.bmp",
    )


def test_preview_output_path_identifies_reduction_parameters() -> None:
    reduction_result = ComplexityReductionResult(
        case="simple",
        baseline_region_count=33,
        target_fraction=0.75,
        max_regions=25,
        maximum_merge_cost=0.35,
        final_region_count=25,
        reduction_seconds=1.0,
    )

    result = preview_output_path(
        output_directory=Path("output"),
        case="simple",
        result=reduction_result,
    )

    assert result == Path(
        "output/" "region-complexity-simple-" "max-25-cost-0p350.bmp",
    )


def test_preview_output_path_identifies_experimental_weights() -> None:
    reduction_result = ComplexityReductionResult(
        case="simple",
        baseline_region_count=33,
        target_fraction=0.75,
        max_regions=25,
        maximum_merge_cost=0.35,
        final_region_count=25,
        reduction_seconds=1.0,
    )

    result = preview_output_path(
        output_directory=Path("output"),
        case="simple",
        result=reduction_result,
        weighting_strategy="color_focused",
    )

    assert result == Path(
        "output/"
        "region-complexity-simple-"
        "max-25-cost-0p350-"
        "weights-color-focused.bmp",
    )


def test_production_weighting_is_the_shipped_weighting() -> None:
    """
    The strategy named after production measures what production ships.

    It used to return `None`, which reached the Core class as a weighting of
    its own: `0.40 / 0.20 / 0.20 / 0.20`, while every shipped profile says
    `0.40 / 0.25 / 0.15 / 0.20`. Every run recorded under this strategy
    described a weighting the project does not ship.
    """
    config = load_config(
        REPOSITORY_ROOT / "config" / "example.toml",
    )

    merge_cost = config.region_complexity.merge_cost

    metrics = _weighting_metrics()

    assert resolve_merge_cost_calculator(
        "production",
        config,
    ).calculate(
        metrics,
    ) == RegionMergeCostCalculator(
        color_weight=merge_cost.color_weight,
        affected_area_weight=(merge_cost.affected_area_weight),
        border_weight=merge_cost.border_weight,
        geometry_weight=merge_cost.geometry_weight,
    ).calculate(
        metrics,
    )


def test_production_weighting_is_not_the_former_implicit_weighting() -> None:
    """
    Why the test above says something: the two weightings differ, so the
    comparison would fail if the strategy fell back to the former one.
    """
    config = load_config(
        REPOSITORY_ROOT / "config" / "example.toml",
    )

    metrics = _weighting_metrics()

    assert resolve_merge_cost_calculator(
        "production",
        config,
    ).calculate(
        metrics,
    ) != RegionMergeCostCalculator(
        color_weight=0.40,
        affected_area_weight=0.20,
        border_weight=0.20,
        geometry_weight=0.20,
    ).calculate(
        metrics,
    )


def test_color_focused_weighting_uses_expected_weights() -> None:
    config = load_config(
        REPOSITORY_ROOT / "config" / "example.toml",
    )

    calculator = resolve_merge_cost_calculator(
        "color_focused",
        config,
    )

    metrics = RegionMergeMetrics(
        color_difference=20.0,
        source_area=2,
        target_area=4,
        merged_area=8,
        affected_area_ratio=0.25,
        shared_border_length=2,
        source_perimeter=8,
        target_perimeter=8,
        merged_perimeter=12,
    )

    cost = calculator.calculate(
        metrics,
    )

    assert cost.value == pytest.approx(
        0.60 * (2 / 3) + 0.15 * 0.25 + 0.15 * 0.75 + 0.10 * (1 / 9),
    )


def test_build_candidate_diagnostics_orders_equal_costs_by_ids() -> None:
    regions = (
        _block_region(
            region_id=3,
            start_x=8,
        ),
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
    )

    diagnostics = build_candidate_diagnostics(
        regions=regions,
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    )

    assert tuple(
        (
            diagnostic.candidate.source_id,
            diagnostic.candidate.target_id,
        )
        for diagnostic in diagnostics
    ) == (
        (1, 2),
        (2, 1),
        (2, 3),
        (3, 2),
    )


def test_build_candidate_diagnostics_includes_region_identity() -> None:
    regions = (
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
    )

    diagnostic = build_candidate_diagnostics(
        regions=regions,
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    )[0]

    assert diagnostic.source_color_number == 1
    assert diagnostic.source_color_name == "Color 1"
    assert diagnostic.target_color_number == 2
    assert diagnostic.target_color_name == "Color 2"
    assert diagnostic.source_bounds == (
        0,
        0,
        3,
        3,
    )
    assert diagnostic.target_bounds == (
        4,
        0,
        7,
        3,
    )


def test_format_candidate_diagnostic_reports_raw_metrics() -> None:
    regions = (
        _block_region(
            region_id=1,
            start_x=0,
        ),
        _block_region(
            region_id=2,
            start_x=4,
        ),
    )

    diagnostic = build_candidate_diagnostics(
        regions=regions,
        color_distance=ConstantColorDistance(),
        cost_calculator=_base_calculator(),
    )[0]

    formatted = format_candidate_diagnostic(
        diagnostic,
        rank=1,
    )

    assert "rank=1" in formatted
    assert "source_id=1" in formatted
    assert "target_id=2" in formatted
    assert "source_bounds=(0, 0, 3, 3)" in formatted
    assert "target_bounds=(4, 0, 7, 3)" in formatted
    assert "color_difference=0.000000" in formatted
    assert "source_area=16" in formatted
    assert "target_area=16" in formatted
    assert "merged_area=32" in formatted
    assert "affected_area_ratio=0.500000" in formatted
    assert "shared_border_length=4" in formatted
    assert "source_perimeter=16" in formatted
    assert "target_perimeter=16" in formatted
    assert "merged_perimeter=24" in formatted
    assert "source_shared_border_ratio=0.250000" in formatted
    assert "target_shared_border_ratio=0.250000" in formatted
    assert "geometry_change=2.000000" in formatted
    assert "color_penalty=0.000000" in formatted
    assert "affected_area_penalty=0.500000" in formatted
    assert "border_penalty=0.750000" in formatted
    assert "geometry_penalty=" in formatted
    assert "cost=" in formatted
