# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from collections.abc import Iterable

from pbn.models import (
    RegionMergeCandidate,
    RegionMergeCost,
    RegionMergeMetrics,
)

from .merge_cost_calculator import RegionMergeCostCalculator

RawCandidateEvaluation = tuple[
    RegionMergeCandidate,
    RegionMergeMetrics,
]

RankedCandidateEvaluation = tuple[
    RegionMergeCandidate,
    RegionMergeMetrics,
    RegionMergeCost,
]


class RegionMergeCandidateRanker:
    """
    Calculate merge costs and rank directed merge candidates deterministically.
    """

    def __init__(
        self,
        cost_calculator: RegionMergeCostCalculator,
    ) -> None:
        self._cost_calculator = cost_calculator

    def rank(
        self,
        evaluations: tuple[
            RawCandidateEvaluation,
            ...,
        ],
    ) -> tuple[
        RankedCandidateEvaluation,
        ...,
    ]:
        """
        Calculate costs and return candidates in deterministic order.
        """
        evaluated = (
            (
                candidate,
                metrics,
                self._cost_calculator.calculate(
                    metrics,
                ),
            )
            for candidate, metrics in evaluations
        )

        return self.order(
            evaluated,
        )

    def order(
        self,
        evaluations: Iterable[RankedCandidateEvaluation],
    ) -> tuple[
        RankedCandidateEvaluation,
        ...,
    ]:
        """
        Order already calculated candidate evaluations deterministically.
        """
        return tuple(
            sorted(
                evaluations,
                key=lambda evaluation: (
                    evaluation[2].value,
                    evaluation[0].source_id,
                    evaluation[0].target_id,
                ),
            ),
        )
