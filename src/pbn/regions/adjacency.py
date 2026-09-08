# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.models import Region
from pbn.models.pixel_index import ROW_STRIDE


class RegionAdjacency:
    """
    Determines neighboring regions.
    """

    def neighbors(
        self,
        regions: tuple[Region, ...],
    ) -> dict[int, set[int]]:
        shared_borders = self.shared_borders(
            regions,
        )

        return {
            region_id: set(border_lengths)
            for region_id, border_lengths in shared_borders.items()
        }

    def shared_borders(
        self,
        regions: tuple[Region, ...],
    ) -> dict[int, dict[int, int]]:
        shared_borders, _ = self.shared_borders_with_overlap_status(
            regions,
        )

        return shared_borders

    def shared_borders_with_overlap_status(
        self,
        regions: tuple[Region, ...],
    ) -> tuple[
        dict[int, dict[int, int]],
        bool,
    ]:
        """
        Return shared borders and whether region pixels overlap.
        """
        pixel_owners, has_overlap = self._pixel_owners(
            regions,
        )

        if has_overlap:
            return (
                self._shared_borders_with_overlap(
                    regions,
                ),
                True,
            )

        return (
            self._shared_borders_disjoint(
                regions,
                pixel_owners,
            ),
            False,
        )

    def update_after_merge(
        self,
        shared_borders: dict[int, dict[int, int]],
        *,
        source_id: int,
        target_id: int,
    ) -> None:
        """
        Update disjoint-region adjacency after merging source into target.
        """
        source_borders = shared_borders.pop(
            source_id,
        )
        target_borders = shared_borders[target_id]

        target_borders.pop(
            source_id,
            None,
        )

        for neighbor_id, source_border_length in source_borders.items():
            if neighbor_id == target_id:
                continue

            border_length = (
                target_borders.get(
                    neighbor_id,
                    0,
                )
                + source_border_length
            )

            target_borders[neighbor_id] = border_length

            neighbor_borders = shared_borders[neighbor_id]
            neighbor_borders.pop(
                source_id,
                None,
            )
            neighbor_borders[target_id] = border_length

    def _shared_borders_disjoint(
        self,
        regions: tuple[Region, ...],
        pixel_owners: dict[int, int],
    ) -> dict[int, dict[int, int]]:
        borders: dict[int, dict[int, int]] = {region.id: {} for region in regions}

        for pixel, region_id in pixel_owners.items():
            try:
                right_id = pixel_owners[pixel + 1]
            except KeyError:
                pass
            else:
                if right_id != region_id:
                    self._add_border(
                        borders,
                        region_id,
                        right_id,
                    )

            try:
                lower_id = pixel_owners[pixel + ROW_STRIDE]
            except KeyError:
                pass
            else:
                if lower_id != region_id:
                    self._add_border(
                        borders,
                        region_id,
                        lower_id,
                    )

        return borders

    def _shared_borders_with_overlap(
        self,
        regions: tuple[Region, ...],
    ) -> dict[int, dict[int, int]]:
        borders: dict[int, dict[int, int]] = {region.id: {} for region in regions}

        for first in regions:
            for second in regions:
                if first.id == second.id:
                    continue

                length = self._shared_border_length(
                    first,
                    second,
                )

                if length > 0:
                    borders[first.id][second.id] = length

        return borders

    def _shared_border_length(
        self,
        first: Region,
        second: Region,
    ) -> int:
        second_pixels = second.pixels

        length = 0

        # A neighbor is reached by integer arithmetic rather than by
        # building a coordinate tuple for every probe.
        for pixel in first.pixels:
            if pixel - 1 in second_pixels:
                length += 1

            if pixel + 1 in second_pixels:
                length += 1

            if pixel - ROW_STRIDE in second_pixels:
                length += 1

            if pixel + ROW_STRIDE in second_pixels:
                length += 1

        return length

    def _add_border(
        self,
        borders: dict[int, dict[int, int]],
        first_id: int,
        second_id: int,
    ) -> None:
        first_borders = borders[first_id]
        first_borders[second_id] = (
            first_borders.get(
                second_id,
                0,
            )
            + 1
        )

        second_borders = borders[second_id]
        second_borders[first_id] = (
            second_borders.get(
                first_id,
                0,
            )
            + 1
        )

    def _pixel_owners(
        self,
        regions: tuple[Region, ...],
    ) -> tuple[
        dict[int, int],
        bool,
    ]:
        owners: dict[int, int] = {}
        has_overlap = False

        for region in regions:
            for pixel in region.pixels:
                existing_owner = owners.get(
                    pixel,
                )

                if existing_owner is not None and existing_owner != region.id:
                    has_overlap = True

                owners[pixel] = region.id

        return (
            owners,
            has_overlap,
        )
