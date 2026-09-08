# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Benchmark geometry validation inside reduced complex outline simplification.

This developer-only module instruments the actual topology simplifier so that
individual outline-geometry validation and pairwise overlap validation can be
measured separately without changing production behavior.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter

from pbn.application.region_merge_cost_calculator_factory import (
    build_region_merge_cost_calculator,
)
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import Outline, Region
from pbn.outline.geometry_validator import (
    OutlineGeometryValidator,
)
from pbn.outline.topology_simplifier import (
    OutlineTopologySimplifier,
)
from tools.benchmark_region_complexity import (
    REPOSITORY_ROOT,
    SUPPORTED_COLOR_DISTANCES,
    execute_reduction,
    palette_path,
    prepare_case,
    resolve_color_distance,
)

BENCHMARK_CASE = "complex"


@dataclass(frozen=True, slots=True)
class GeometryValidationCall:
    """
    Timing and result counts for one real geometry-validation call.
    """

    outline_count: int
    region_filter_count: int | None
    invalid_outline_region_count: int
    overlapping_region_pair_count: int
    invalid_outline_seconds: float
    overlapping_region_pairs_seconds: float

    @property
    def total_seconds(self) -> float:
        """
        Return total time spent in the two measured validation paths.
        """
        return self.invalid_outline_seconds + self.overlapping_region_pairs_seconds


@dataclass(frozen=True, slots=True)
class OutlineGeometryValidationBenchmark:
    """
    Geometry-validation timings from one complete simplification.
    """

    reduced_region_count: int
    resulting_outline_count: int
    complete_simplification_seconds: float
    validation_calls: tuple[
        GeometryValidationCall,
        ...,
    ]

    @property
    def validation_call_count(self) -> int:
        """
        Return the number of actual invalid-region validation calls.
        """
        return len(
            self.validation_calls,
        )

    @property
    def invalid_outline_seconds(self) -> float:
        """
        Return cumulative individual-outline validation time.
        """
        return sum(call.invalid_outline_seconds for call in self.validation_calls)

    @property
    def overlapping_region_pairs_seconds(self) -> float:
        """
        Return cumulative pairwise overlap-validation time.
        """
        return sum(
            call.overlapping_region_pairs_seconds for call in self.validation_calls
        )

    @property
    def geometry_validation_seconds(self) -> float:
        """
        Return cumulative measured geometry-validation time.
        """
        return self.invalid_outline_seconds + self.overlapping_region_pairs_seconds

    @property
    def non_validation_seconds(self) -> float:
        """
        Return simplification time outside the measured validator paths.
        """
        return max(
            0.0,
            self.complete_simplification_seconds - self.geometry_validation_seconds,
        )

    @property
    def overlap_fraction_of_validation(self) -> float:
        """
        Return overlap validation's share of measured validator time.
        """
        validation_seconds = self.geometry_validation_seconds

        if validation_seconds == 0.0:
            return 0.0

        return self.overlapping_region_pairs_seconds / validation_seconds

    @property
    def overlap_fraction_of_complete_simplification(
        self,
    ) -> float:
        """
        Return overlap validation's share of complete simplification.
        """
        if self.complete_simplification_seconds == 0.0:
            return 0.0

        return (
            self.overlapping_region_pairs_seconds / self.complete_simplification_seconds
        )


class InstrumentedOutlineGeometryValidator(
    OutlineGeometryValidator,
):
    """
    Measure the two validation paths used by invalid_region_ids.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float],
    ) -> None:
        self._clock = clock
        self._calls: list[GeometryValidationCall] = []

    @property
    def calls(
        self,
    ) -> tuple[
        GeometryValidationCall,
        ...,
    ]:
        """
        Return validation calls in their actual execution order.
        """
        return tuple(
            self._calls,
        )

    def invalid_region_ids(
        self,
        outlines: tuple[Outline, ...],
        *,
        region_ids: set[int] | None = None,
    ) -> set[int]:
        """
        Preserve validator behavior while timing its two sub-operations.
        """
        invalid_outline_started_at = self._clock()

        invalid_outline_region_ids = self.invalid_outline_region_ids(
            outlines,
            region_ids=region_ids,
        )

        invalid_outline_finished_at = self._clock()

        overlap_started_at = self._clock()

        overlapping_region_pairs = self.overlapping_region_pairs(
            outlines,
            region_ids=region_ids,
        )

        overlap_finished_at = self._clock()

        self._calls.append(
            GeometryValidationCall(
                outline_count=len(
                    outlines,
                ),
                region_filter_count=(
                    None
                    if region_ids is None
                    else len(
                        region_ids,
                    )
                ),
                invalid_outline_region_count=len(
                    invalid_outline_region_ids,
                ),
                overlapping_region_pair_count=len(
                    overlapping_region_pairs,
                ),
                invalid_outline_seconds=(
                    invalid_outline_finished_at - invalid_outline_started_at
                ),
                overlapping_region_pairs_seconds=(
                    overlap_finished_at - overlap_started_at
                ),
            ),
        )

        invalid_region_ids = set(
            invalid_outline_region_ids,
        )

        for (
            first_region_id,
            second_region_id,
        ) in overlapping_region_pairs:
            invalid_region_ids.add(
                first_region_id,
            )
            invalid_region_ids.add(
                second_region_id,
            )

        return invalid_region_ids


def benchmark_outline_geometry_validation(
    *,
    reduced_regions: tuple[Region, ...],
    tolerance: float,
    clock: Callable[[], float],
) -> OutlineGeometryValidationBenchmark:
    """
    Instrument one actual topology-simplification execution.
    """
    if not reduced_regions:
        raise ValueError(
            "reduced_regions must not be empty",
        )

    validator = InstrumentedOutlineGeometryValidator(
        clock=clock,
    )

    simplifier = OutlineTopologySimplifier()

    # This developer-only benchmark deliberately replaces the internal
    # validator so the production simplification orchestration itself remains
    # unchanged while the real validation calls are observed.
    simplifier._geometry_validator = validator

    started_at = clock()

    outlines = simplifier.simplify(
        reduced_regions,
        tolerance=tolerance,
    )

    finished_at = clock()

    return OutlineGeometryValidationBenchmark(
        reduced_region_count=len(
            reduced_regions,
        ),
        resulting_outline_count=len(
            outlines,
        ),
        complete_simplification_seconds=(finished_at - started_at),
        validation_calls=validator.calls,
    )


def format_validation_summary(
    benchmark: OutlineGeometryValidationBenchmark,
) -> str:
    """
    Format the aggregate geometry-validation result.
    """
    return (
        "geometry_validation_summary: "
        "reduced_regions="
        f"{benchmark.reduced_region_count}, "
        "resulting_outlines="
        f"{benchmark.resulting_outline_count}, "
        "validation_calls="
        f"{benchmark.validation_call_count}, "
        "complete_simplification="
        f"{benchmark.complete_simplification_seconds:.6f}s, "
        "invalid_outline_validation="
        f"{benchmark.invalid_outline_seconds:.6f}s, "
        "overlapping_region_pairs="
        f"{benchmark.overlapping_region_pairs_seconds:.6f}s, "
        "geometry_validation_total="
        f"{benchmark.geometry_validation_seconds:.6f}s, "
        "non_validation="
        f"{benchmark.non_validation_seconds:.6f}s, "
        "overlap_of_validation="
        f"{benchmark.overlap_fraction_of_validation * 100.0:.2f}%, "
        "overlap_of_complete="
        f"{benchmark.overlap_fraction_of_complete_simplification * 100.0:.2f}%"
    )


def format_validation_call(
    call: GeometryValidationCall,
    *,
    call_number: int,
) -> str:
    """
    Format one actual validator invocation.
    """
    region_filter = (
        "all"
        if call.region_filter_count is None
        else str(
            call.region_filter_count,
        )
    )

    return (
        "geometry_validation_call="
        f"{call_number}: "
        f"outlines={call.outline_count}, "
        f"region_filter={region_filter}, "
        "invalid_outline_regions="
        f"{call.invalid_outline_region_count}, "
        "overlap_pairs="
        f"{call.overlapping_region_pair_count}, "
        "invalid_outline_validation="
        f"{call.invalid_outline_seconds:.6f}s, "
        "overlapping_region_pairs="
        f"{call.overlapping_region_pairs_seconds:.6f}s, "
        f"total={call.total_seconds:.6f}s"
    )


def build_parser() -> ArgumentParser:
    """
    Build the reduced-complex geometry benchmark parser.
    """
    parser = ArgumentParser(
        description=(
            "Benchmark individual outline validation and "
            "pairwise overlap validation inside reduced "
            "complex topology simplification."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
    )

    parser.add_argument(
        "--palette",
        default=None,
    )

    parser.add_argument(
        "--palette-version",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--color-distance",
        choices=SUPPORTED_COLOR_DISTANCES,
        default=None,
    )

    parser.add_argument(
        "--minimum-region-size-mm",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--target-fraction",
        type=float,
        default=0.5,
    )

    return parser


def main() -> None:
    """
    Benchmark geometry validation on the reduced complex result.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.minimum_region_size_mm is not None and args.minimum_region_size_mm <= 0.0:
        parser.error(
            "--minimum-region-size-mm must be greater than zero",
        )

    if not 0.0 < args.target_fraction <= 1.0:
        parser.error(
            "--target-fraction must be greater than zero and at most one",
        )

    loaded_config = load_config(
        args.config,
    )

    config = (
        loaded_config
        if args.minimum_region_size_mm is None
        else replace(
            loaded_config,
            minimum_region_size_mm=(args.minimum_region_size_mm),
        )
    )

    selected_palette = args.palette if args.palette is not None else config.palette

    selected_palette_version = (
        args.palette_version
        if args.palette_version is not None
        else config.palette_version
    )

    selected_color_distance = (
        args.color_distance
        if args.color_distance is not None
        else config.color_distance
    )

    palette = load_palette(
        palette_path(
            palette_id=selected_palette,
            palette_version=(selected_palette_version),
        ),
    )

    color_distance = resolve_color_distance(
        selected_color_distance,
    )

    cost_calculator = build_region_merge_cost_calculator(
        config.region_complexity.merge_cost,
    )

    prepared = prepare_case(
        case=BENCHMARK_CASE,
        config=config,
        palette=palette,
        color_distance=color_distance,
    )

    execution = execute_reduction(
        case=BENCHMARK_CASE,
        regions=prepared.regions,
        color_distance=color_distance,
        minimum_circle_diameter_px=(prepared.minimum_circle_diameter_px),
        target_fraction=args.target_fraction,
        maximum_merge_cost=(config.region_complexity.maximum_merge_cost),
        cost_calculator=cost_calculator,
    )

    print(
        (
            f"case={BENCHMARK_CASE}, "
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            "minimum_region_size_mm="
            f"{config.minimum_region_size_mm:g}, "
            "maximum_merge_cost="
            f"{config.region_complexity.maximum_merge_cost:g}, "
            "target_fraction="
            f"{args.target_fraction:g}"
        ),
    )

    print(
        (
            "reduction_preparation: "
            "mandatory_regions="
            f"{len(prepared.regions)}, "
            "max_regions="
            f"{execution.result.max_regions}, "
            "reduced_regions="
            f"{len(execution.regions)}, "
            "accepted_merges="
            f"{len(prepared.regions) - len(execution.regions)}, "
            "reduction_seconds="
            f"{execution.result.reduction_seconds:.6f}s"
        ),
    )

    benchmark = benchmark_outline_geometry_validation(
        reduced_regions=execution.regions,
        tolerance=(config.outline_simplification_tolerance_px),
        clock=perf_counter,
    )

    print(
        format_validation_summary(
            benchmark,
        ),
    )

    for call_number, call in enumerate(
        benchmark.validation_calls,
        start=1,
    ):
        print(
            format_validation_call(
                call,
                call_number=call_number,
            ),
        )


if __name__ == "__main__":
    main()
