# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.color.color_distance import ColorDistance
from pbn.models import (
    Region,
    RegionMergeCandidate,
    RegionMergeCost,
    RegionMergeMetrics,
    RegionMergeStep,
)

from .adjacency import RegionAdjacency
from .circle_fit import RegionCircleFit
from .merge_candidate_builder import RegionMergeCandidateBuilder
from .merge_candidate_ranker import (
    RankedCandidateEvaluation,
    RegionMergeCandidateRanker,
)
from .merge_cost_calculator import RegionMergeCostCalculator

CandidateEvaluationCache = dict[
    RegionMergeCandidate,
    RankedCandidateEvaluation,
]

SelectedCandidate = tuple[
    RegionMergeCandidate,
    RegionMergeMetrics,
    RegionMergeCost,
    frozenset[int],
]


class RegionComplexityReducer:
    """
    Reduce optional region complexity using quality-bounded directed merges.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
        cost_calculator: RegionMergeCostCalculator,
    ) -> None:
        self._adjacency = RegionAdjacency()
        self._candidate_builder = RegionMergeCandidateBuilder(
            color_distance=color_distance,
        )
        self._candidate_ranker = RegionMergeCandidateRanker(
            cost_calculator=cost_calculator,
        )
        self._circle_fit = RegionCircleFit()

    def reduce(
        self,
        regions: tuple[Region, ...],
        *,
        minimum_circle_diameter_px: int,
        max_regions: int,
        maximum_merge_cost: float,
    ) -> tuple[Region, ...]:
        """
        Reduce regions until the target or quality boundary stops reduction.
        """
        reduced_regions, _ = self._reduce(
            regions,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            capture_merge_steps=False,
        )

        return reduced_regions

    def reduce_with_trace(
        self,
        regions: tuple[Region, ...],
        *,
        minimum_circle_diameter_px: int,
        max_regions: int,
        maximum_merge_cost: float,
    ) -> tuple[
        tuple[Region, ...],
        tuple[RegionMergeStep, ...],
    ]:
        """
        Reduce regions and return the actual accepted merge sequence.
        """
        return self._reduce(
            regions,
            minimum_circle_diameter_px=minimum_circle_diameter_px,
            max_regions=max_regions,
            maximum_merge_cost=maximum_merge_cost,
            capture_merge_steps=True,
        )

    def _reduce(
        self,
        regions: tuple[Region, ...],
        *,
        minimum_circle_diameter_px: int,
        max_regions: int,
        maximum_merge_cost: float,
        capture_merge_steps: bool,
    ) -> tuple[
        tuple[Region, ...],
        tuple[RegionMergeStep, ...],
    ]:
        active_regions = {region.id: region for region in regions}

        merge_steps: list[RegionMergeStep] | None = [] if capture_merge_steps else None

        if len(active_regions) <= max_regions:
            return (
                self._ordered_regions(
                    active_regions,
                ),
                (),
            )

        current_regions = self._ordered_regions(
            active_regions,
        )

        (
            shared_borders,
            has_overlapping_pixels,
        ) = self._adjacency.shared_borders_with_overlap_status(
            current_regions,
        )

        supports_incremental_update = not has_overlapping_pixels

        candidate_evaluations = self._build_candidate_evaluations(
            active_regions=active_regions,
            shared_borders=shared_borders,
            touching_region_ids=None,
        )

        while len(active_regions) > max_regions:
            ranked_candidates = self._candidate_ranker.order(
                candidate_evaluations.values(),
            )

            selected = self._select_candidate(
                ranked_candidates,
                active_regions,
                minimum_circle_diameter_px,
                maximum_merge_cost,
            )

            if selected is None:
                break

            (
                candidate,
                metrics,
                cost,
                merged_pixels,
            ) = selected

            if merge_steps is not None:
                merge_steps.append(
                    RegionMergeStep(
                        candidate=candidate,
                        metrics=metrics,
                        cost=cost,
                    ),
                )

            source = active_regions[candidate.source_id]
            target = active_regions[candidate.target_id]

            active_regions.pop(
                source.id,
            )
            active_regions[target.id] = Region(
                id=target.id,
                color=target.color,
                pixels=merged_pixels,
            )

            if supports_incremental_update:
                self._adjacency.update_after_merge(
                    shared_borders,
                    source_id=source.id,
                    target_id=target.id,
                )

                self._refresh_candidate_evaluations(
                    candidate_evaluations=candidate_evaluations,
                    active_regions=active_regions,
                    shared_borders=shared_borders,
                    source_id=source.id,
                    target_id=target.id,
                )
            else:
                current_regions = self._ordered_regions(
                    active_regions,
                )

                (
                    shared_borders,
                    has_overlapping_pixels,
                ) = self._adjacency.shared_borders_with_overlap_status(
                    current_regions,
                )

                supports_incremental_update = not has_overlapping_pixels

                candidate_evaluations = self._build_candidate_evaluations(
                    active_regions=active_regions,
                    shared_borders=shared_borders,
                    touching_region_ids=None,
                )

        accepted_merge_steps = (
            tuple(
                merge_steps,
            )
            if merge_steps is not None
            else ()
        )

        return (
            self._ordered_regions(
                active_regions,
            ),
            accepted_merge_steps,
        )

    def _build_candidate_evaluations(
        self,
        *,
        active_regions: dict[int, Region],
        shared_borders: dict[int, dict[int, int]],
        touching_region_ids: frozenset[int] | None,
    ) -> CandidateEvaluationCache:
        raw_evaluations = self._candidate_builder.build_from_shared_borders(
            regions_by_id=active_regions,
            shared_borders=shared_borders,
            touching_region_ids=touching_region_ids,
        )

        ranked_evaluations = self._candidate_ranker.rank(
            raw_evaluations,
        )

        return {evaluation[0]: evaluation for evaluation in ranked_evaluations}

    def _refresh_candidate_evaluations(
        self,
        *,
        candidate_evaluations: CandidateEvaluationCache,
        active_regions: dict[int, Region],
        shared_borders: dict[int, dict[int, int]],
        source_id: int,
        target_id: int,
    ) -> None:
        affected_region_ids = frozenset(
            {
                source_id,
                target_id,
            },
        )

        stale_candidates = tuple(
            candidate
            for candidate in candidate_evaluations
            if (
                candidate.source_id in affected_region_ids
                or candidate.target_id in affected_region_ids
            )
        )

        for candidate in stale_candidates:
            candidate_evaluations.pop(
                candidate,
            )

        updated_evaluations = self._build_candidate_evaluations(
            active_regions=active_regions,
            shared_borders=shared_borders,
            touching_region_ids=frozenset(
                {
                    target_id,
                },
            ),
        )

        candidate_evaluations.update(
            updated_evaluations,
        )

    def _select_candidate(
        self,
        ranked_candidates: tuple[
            RankedCandidateEvaluation,
            ...,
        ],
        active_regions: dict[int, Region],
        minimum_circle_diameter_px: int,
        maximum_merge_cost: float,
    ) -> SelectedCandidate | None:
        for candidate, metrics, cost in ranked_candidates:
            if cost.value > maximum_merge_cost:
                return None

            source = active_regions[candidate.source_id]
            target = active_regions[candidate.target_id]

            merged_pixels = frozenset(
                target.pixels | source.pixels,
            )

            if self._merge_preserves_paintability(
                target=target,
                merged_pixels=merged_pixels,
                minimum_circle_diameter_px=minimum_circle_diameter_px,
            ):
                return (
                    candidate,
                    metrics,
                    cost,
                    merged_pixels,
                )

        return None

    def _merge_preserves_paintability(
        self,
        *,
        target: Region,
        merged_pixels: frozenset[int],
        minimum_circle_diameter_px: int,
    ) -> bool:
        if self._circle_fit.fits(
            region=target,
            diameter_px=minimum_circle_diameter_px,
        ):
            return True

        return self._circle_fit.fits_pixels(
            pixels=merged_pixels,
            diameter_px=minimum_circle_diameter_px,
        )

    @staticmethod
    def _ordered_regions(
        regions: dict[int, Region],
    ) -> tuple[Region, ...]:
        return tuple(
            regions[region_id]
            for region_id in sorted(
                regions,
            )
        )
