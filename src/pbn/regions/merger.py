# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from collections import deque

from pbn.models import Region

from .adjacency import RegionAdjacency
from .circle_fit import RegionCircleFit


class RegionMerger:
    """
    Merges regions that cannot contain the minimum required circle.
    """

    def __init__(self) -> None:
        self._adjacency = RegionAdjacency()
        self._circle_fit = RegionCircleFit()

    def merge(
        self,
        regions: tuple[Region, ...],
        minimum_circle_diameter_px: int,
    ) -> tuple[Region, ...]:
        active_regions = {region.id: region for region in regions}
        active_generations = {region.id: 0 for region in regions}
        pending = deque((region.id, 0) for region in regions)

        shared_borders: dict[int, dict[int, int]] | None = None
        supports_incremental_update: bool | None = None
        fit_cache: dict[int, tuple[Region, bool]] = {}
        deferred_fit_cache: dict[int, bool] = {}
        deferred_pixels: dict[
            int,
            set[int],
        ] = {}

        while pending:
            region_id, generation = pending.popleft()

            region = active_regions.get(
                region_id,
            )

            if region is None or active_generations.get(region_id) != generation:
                continue

            region_pixels = deferred_pixels.get(
                region.id,
            )

            if region_pixels is None:
                fits = self._fits(
                    region,
                    minimum_circle_diameter_px,
                    fit_cache,
                )
            else:
                fits = self._fits_deferred(
                    region.id,
                    region_pixels,
                    minimum_circle_diameter_px,
                    deferred_fit_cache,
                )

            if fits:
                continue

            if shared_borders is None:
                current_regions = tuple(
                    active_regions.values(),
                )

                (
                    shared_borders,
                    has_overlapping_pixels,
                ) = self._adjacency.shared_borders_with_overlap_status(
                    current_regions,
                )

                supports_incremental_update = not has_overlapping_pixels

            target = self._find_merge_target(
                region,
                active_regions,
                shared_borders,
            )

            if target is None:
                continue

            if supports_incremental_update is True:
                target_known_to_fit = self._is_known_to_fit(
                    target,
                    fit_cache,
                    deferred_fit_cache,
                )

                self._defer_merge(
                    target,
                    region,
                    deferred_pixels,
                )

                active_regions.pop(
                    region.id,
                )
                active_regions.pop(
                    target.id,
                )
                active_regions[target.id] = target

                active_generations.pop(
                    region.id,
                )

                fit_cache.pop(
                    region.id,
                    None,
                )
                deferred_fit_cache.pop(
                    region.id,
                    None,
                )

                if not target_known_to_fit:
                    target_generation = active_generations[target.id] + 1
                    active_generations[target.id] = target_generation

                    pending.append(
                        (
                            target.id,
                            target_generation,
                        ),
                    )

                    fit_cache.pop(
                        target.id,
                        None,
                    )
                    deferred_fit_cache.pop(
                        target.id,
                        None,
                    )
            else:
                merged_region = self._merge(
                    target,
                    region,
                )

                target_generation = active_generations[target.id] + 1

                active_regions.pop(
                    region.id,
                )
                active_regions.pop(
                    target.id,
                )
                active_regions[merged_region.id] = merged_region

                active_generations.pop(
                    region.id,
                )
                active_generations[target.id] = target_generation

                pending.append(
                    (
                        merged_region.id,
                        target_generation,
                    ),
                )

                fit_cache.pop(
                    region.id,
                    None,
                )
                fit_cache.pop(
                    target.id,
                    None,
                )
                deferred_fit_cache.pop(
                    region.id,
                    None,
                )
                deferred_fit_cache.pop(
                    target.id,
                    None,
                )

            if supports_incremental_update:
                self._adjacency.update_after_merge(
                    shared_borders,
                    source_id=region.id,
                    target_id=target.id,
                )
            else:
                shared_borders = None
                supports_incremental_update = None

        return self._materialize_regions(
            active_regions,
            deferred_pixels,
        )

    def _fits(
        self,
        region: Region,
        minimum_circle_diameter_px: int,
        fit_cache: dict[int, tuple[Region, bool]],
    ) -> bool:
        cached = fit_cache.get(
            region.id,
        )

        if cached is not None and cached[0] is region:
            return cached[1]

        fits = self._circle_fit.fits(
            region=region,
            diameter_px=minimum_circle_diameter_px,
        )

        fit_cache[region.id] = (
            region,
            fits,
        )

        return fits

    def _fits_deferred(
        self,
        region_id: int,
        pixels: set[int],
        minimum_circle_diameter_px: int,
        fit_cache: dict[int, bool],
    ) -> bool:
        cached = fit_cache.get(
            region_id,
        )

        if cached is not None:
            return cached

        fits = self._circle_fit.fits_pixels(
            pixels=pixels,
            diameter_px=minimum_circle_diameter_px,
        )

        fit_cache[region_id] = fits

        return fits

    def _is_known_to_fit(
        self,
        region: Region,
        fit_cache: dict[int, tuple[Region, bool]],
        deferred_fit_cache: dict[int, bool],
    ) -> bool:
        if region.id in deferred_fit_cache:
            return deferred_fit_cache[region.id]

        cached = fit_cache.get(
            region.id,
        )

        return cached is not None and cached[0] is region and cached[1]

    def _find_merge_target(
        self,
        region: Region,
        regions: dict[int, Region],
        shared_borders: dict[int, dict[int, int]],
    ) -> Region | None:
        border_lengths = shared_borders[region.id]

        if not border_lengths:
            return None

        neighbor_id = min(
            border_lengths,
            key=lambda region_id: (
                -border_lengths[region_id],
                region_id,
            ),
        )

        return regions.get(
            neighbor_id,
        )

    def _defer_merge(
        self,
        target: Region,
        source: Region,
        deferred_pixels: dict[
            int,
            set[int],
        ],
    ) -> None:
        target_pixels = deferred_pixels.get(
            target.id,
        )

        if target_pixels is None:
            target_pixels = set(
                target.pixels,
            )
            deferred_pixels[target.id] = target_pixels

        source_pixels = deferred_pixels.pop(
            source.id,
            None,
        )

        if source_pixels is None:
            target_pixels.update(
                source.pixels,
            )
        else:
            target_pixels.update(
                source_pixels,
            )

    def _materialize_regions(
        self,
        active_regions: dict[int, Region],
        deferred_pixels: dict[
            int,
            set[int],
        ],
    ) -> tuple[Region, ...]:
        materialized: list[Region] = []

        for region in active_regions.values():
            pixels = deferred_pixels.get(
                region.id,
            )

            if pixels is None:
                materialized.append(
                    region,
                )
                continue

            materialized.append(
                Region(
                    id=region.id,
                    color=region.color,
                    pixels=frozenset(
                        pixels,
                    ),
                ),
            )

        return tuple(
            materialized,
        )

    def _merge(
        self,
        target: Region,
        source: Region,
    ) -> Region:
        return Region(
            id=target.id,
            color=target.color,
            pixels=frozenset(
                target.pixels | source.pixels,
            ),
        )
