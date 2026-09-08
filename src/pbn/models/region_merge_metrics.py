# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from dataclasses import dataclass
from math import pi


@dataclass(frozen=True, slots=True)
class RegionMergeMetrics:
    """
    Raw measurements for evaluating one directed region merge.
    """

    color_difference: float

    source_area: int

    target_area: int

    merged_area: int

    affected_area_ratio: float

    shared_border_length: int

    source_perimeter: int

    target_perimeter: int

    merged_perimeter: int

    @property
    def source_shared_border_ratio(
        self,
    ) -> float:
        """
        Return the fraction of the source perimeter shared with the target.
        """
        return self.shared_border_length / self.source_perimeter

    @property
    def target_shared_border_ratio(
        self,
    ) -> float:
        """
        Return the fraction of the target perimeter shared with the source.
        """
        return self.shared_border_length / self.target_perimeter

    @property
    def source_compactness(
        self,
    ) -> float:
        """
        Return normalized isoperimetric compactness of the source region.
        """
        compactness = (
            4.0
            * pi
            * self.source_area
            / (self.source_perimeter * self.source_perimeter)
        )

        return min(
            1.0,
            compactness,
        )

    @property
    def source_non_compactness(
        self,
    ) -> float:
        """
        Return normalized deviation from compact source geometry.
        """
        return 1.0 - self.source_compactness

    @property
    def source_geometry_complexity(
        self,
    ) -> float:
        """
        Return the source region's perimeter-squared-to-area ratio.
        """
        return self._geometry_complexity(
            area=self.source_area,
            perimeter=self.source_perimeter,
        )

    @property
    def target_geometry_complexity(
        self,
    ) -> float:
        """
        Return the target region's perimeter-squared-to-area ratio.
        """
        return self._geometry_complexity(
            area=self.target_area,
            perimeter=self.target_perimeter,
        )

    @property
    def merged_geometry_complexity(
        self,
    ) -> float:
        """
        Return the merged region's perimeter-squared-to-area ratio.
        """
        return self._geometry_complexity(
            area=self.merged_area,
            perimeter=self.merged_perimeter,
        )

    @property
    def geometry_change(
        self,
    ) -> float:
        """
        Return the directed geometry-complexity change of the target.
        """
        return self.merged_geometry_complexity - self.target_geometry_complexity

    @staticmethod
    def _geometry_complexity(
        *,
        area: int,
        perimeter: int,
    ) -> float:
        return perimeter * perimeter / area
