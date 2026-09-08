# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.exceptions import InvariantViolationError
from pbn.models import Outline, Region
from pbn.models.pixel_index import pack_pixel

from .geometry_validator import (
    OutlineGeometryValidator,
    OverlapDetector,
)
from .simplifier import DouglasPeuckerSimplifier
from .tracer import OutlineTracer

Point = tuple[int, int]
Ring = tuple[Point, ...]
BoundaryChain = tuple[Point, ...]
PixelOwners = dict[int, int]

FALLBACK_TOLERANCE_FACTORS = (
    1.0,
    0.5,
    0.25,
    0.125,
    0.0,
)


class OutlineTopologySimplifier:
    """
    Simplifies region outlines while preserving shared boundaries.
    """

    def __init__(
        self,
        overlap_detector: OverlapDetector | None = None,
    ) -> None:
        self._tracer = OutlineTracer()
        self._simplifier = DouglasPeuckerSimplifier()
        self._geometry_validator = OutlineGeometryValidator(
            overlap_detector=overlap_detector,
        )

    def simplify(
        self,
        regions: tuple[Region, ...],
        *,
        tolerance: float,
    ) -> tuple[Outline, ...]:
        pixel_owners = self._build_pixel_owners(
            regions,
        )

        raw_outlines = tuple(
            self._tracer.trace_raw(
                region,
            )
            for region in regions
        )

        invalid_raw_region_ids = self._geometry_validator.invalid_region_ids(
            raw_outlines,
        )

        if invalid_raw_region_ids:
            invalid_raw_outline_region_ids = (
                self._geometry_validator.invalid_outline_region_ids(
                    raw_outlines,
                )
            )
            overlapping_raw_region_pairs = (
                self._geometry_validator.overlapping_region_pairs(
                    raw_outlines,
                )
            )

            raise InvariantViolationError(
                "Outline tracing produced invalid polygon geometry "
                "for region ids: "
                f"{sorted(invalid_raw_region_ids)}. "
                "Invalid individual region ids: "
                f"{sorted(invalid_raw_outline_region_ids)}. "
                "Overlapping region pairs: "
                f"{sorted(overlapping_raw_region_pairs)}."
            )

        fallback_region_levels: dict[int, int] = {}
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ] = {}

        previous_outlines: tuple[Outline, ...] | None = None
        previous_invalid_region_ids: set[int] = set()

        while True:
            outlines = self._simplify_regions(
                regions,
                raw_outlines=raw_outlines,
                pixel_owners=pixel_owners,
                tolerance=tolerance,
                fallback_region_levels=fallback_region_levels,
                fallback_chain_levels=fallback_chain_levels,
            )

            validation_region_ids: set[int] | None

            if previous_outlines is None:
                validation_region_ids = None
            else:
                validation_region_ids = (
                    previous_invalid_region_ids
                    | self._changed_region_ids(
                        previous_outlines,
                        outlines,
                    )
                )

            invalid_region_ids = self._geometry_validator.invalid_region_ids(
                outlines,
                region_ids=validation_region_ids,
            )

            if not invalid_region_ids:
                return outlines

            fallback_extended = self._reduce_fallback_tolerances(
                regions,
                raw_outlines=raw_outlines,
                invalid_region_ids=invalid_region_ids,
                pixel_owners=pixel_owners,
                tolerance=tolerance,
                fallback_region_levels=fallback_region_levels,
                fallback_chain_levels=fallback_chain_levels,
            )

            if not fallback_extended:
                raise InvariantViolationError(
                    "Outline simplification could not produce valid polygon "
                    "geometry even at zero tolerance for region ids: "
                    f"{sorted(invalid_region_ids)}."
                )

            previous_outlines = outlines
            previous_invalid_region_ids = invalid_region_ids

    def _simplify_regions(
        self,
        regions: tuple[Region, ...],
        *,
        raw_outlines: tuple[Outline, ...],
        pixel_owners: PixelOwners,
        tolerance: float,
        fallback_region_levels: dict[int, int],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
    ) -> tuple[Outline, ...]:
        simplified_chains: dict[
            BoundaryChain,
            BoundaryChain,
        ] = {}
        simplified_closed_rings: dict[
            Ring,
            Ring,
        ] = {}

        return tuple(
            self._simplify_region(
                region,
                outline=outline,
                pixel_owners=pixel_owners,
                simplified_chains=simplified_chains,
                simplified_closed_rings=simplified_closed_rings,
                tolerance=tolerance,
                fallback_region_levels=fallback_region_levels,
                fallback_chain_levels=fallback_chain_levels,
            )
            for region, outline in zip(
                regions,
                raw_outlines,
                strict=True,
            )
        )

    def _simplify_region(
        self,
        region: Region,
        *,
        outline: Outline,
        pixel_owners: PixelOwners,
        simplified_chains: dict[
            BoundaryChain,
            BoundaryChain,
        ],
        simplified_closed_rings: dict[
            Ring,
            Ring,
        ],
        tolerance: float,
        fallback_region_levels: dict[int, int],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
    ) -> Outline:
        points = self._simplify_ring(
            region,
            points=outline.points,
            pixel_owners=pixel_owners,
            simplified_chains=simplified_chains,
            simplified_closed_rings=simplified_closed_rings,
            tolerance=tolerance,
            fallback_region_levels=fallback_region_levels,
            fallback_chain_levels=fallback_chain_levels,
        )
        hole_rings = tuple(
            self._simplify_ring(
                region,
                points=ring,
                pixel_owners=pixel_owners,
                simplified_chains=simplified_chains,
                simplified_closed_rings=simplified_closed_rings,
                tolerance=tolerance,
                fallback_region_levels=fallback_region_levels,
                fallback_chain_levels=fallback_chain_levels,
            )
            for ring in outline.hole_rings
        )

        return Outline(
            region_id=region.id,
            points=points,
            hole_rings=hole_rings,
        )

    def _simplify_ring(
        self,
        region: Region,
        *,
        points: Ring,
        pixel_owners: PixelOwners,
        simplified_chains: dict[
            BoundaryChain,
            BoundaryChain,
        ],
        simplified_closed_rings: dict[
            Ring,
            Ring,
        ],
        tolerance: float,
        fallback_region_levels: dict[int, int],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
    ) -> Ring:
        if len(points) <= 3:
            return points

        neighbor_ids = self._ring_neighbor_ids(
            region_id=region.id,
            points=points,
            pixel_owners=pixel_owners,
        )
        chains = self._build_ring_boundary_chains(
            points,
            neighbor_ids=neighbor_ids,
        )

        if chains:
            return self._simplify_ring_from_chains(
                chains,
                simplified_chains=simplified_chains,
                fallback_chain_levels=fallback_chain_levels,
                tolerance=tolerance,
            )

        if neighbor_ids and neighbor_ids[0] is not None:
            return self._simplify_shared_closed_ring(
                region_id=region.id,
                points=points,
                simplified_closed_rings=simplified_closed_rings,
                fallback_chain_levels=fallback_chain_levels,
                tolerance=tolerance,
            )

        fallback_level = fallback_region_levels.get(
            region.id,
            0,
        )
        simplified_outline = self._simplifier.simplify(
            Outline(
                region_id=region.id,
                points=points,
            ),
            tolerance=self._fallback_tolerance(
                tolerance,
                fallback_level=fallback_level,
            ),
        )

        return simplified_outline.points

    def _simplify_ring_from_chains(
        self,
        chains: tuple[BoundaryChain, ...],
        *,
        simplified_chains: dict[
            BoundaryChain,
            BoundaryChain,
        ],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
        tolerance: float,
    ) -> Ring:
        simplified_points: list[Point] = []

        for chain in chains:
            simplified_chain = self._simplify_boundary_chain(
                chain,
                simplified_chains=simplified_chains,
                fallback_chain_levels=fallback_chain_levels,
                tolerance=tolerance,
            )

            if not simplified_points:
                simplified_points.extend(
                    simplified_chain,
                )
            else:
                simplified_points.extend(
                    simplified_chain[1:],
                )

        if len(simplified_points) > 1 and simplified_points[0] == simplified_points[-1]:
            simplified_points.pop()

        return tuple(
            simplified_points,
        )

    def _simplify_shared_closed_ring(
        self,
        *,
        region_id: int,
        points: Ring,
        simplified_closed_rings: dict[
            Ring,
            Ring,
        ],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
        tolerance: float,
    ) -> Ring:
        canonical_ring = self._canonical_ring(
            points,
        )
        simplified = simplified_closed_rings.get(
            canonical_ring,
        )

        if simplified is None:
            fallback_level = fallback_chain_levels.get(
                canonical_ring,
                0,
            )
            simplified = self._simplifier.simplify(
                Outline(
                    region_id=region_id,
                    points=canonical_ring,
                ),
                tolerance=self._fallback_tolerance(
                    tolerance,
                    fallback_level=fallback_level,
                ),
            ).points
            simplified_closed_rings[canonical_ring] = simplified

        return self._orient_ring_like(
            simplified,
            points,
        )

    def _ring_neighbor_ids(
        self,
        *,
        region_id: int,
        points: Ring,
        pixel_owners: PixelOwners,
    ) -> tuple[int | None, ...]:
        return tuple(
            self._neighbor_region_id(
                region_id=region_id,
                start=points[index],
                end=points[(index + 1) % len(points)],
                pixel_owners=pixel_owners,
            )
            for index in range(
                len(points),
            )
        )

    def _build_ring_boundary_chains(
        self,
        points: Ring,
        *,
        neighbor_ids: tuple[int | None, ...],
    ) -> tuple[BoundaryChain, ...]:
        junction_indices = tuple(
            index
            for index in range(
                len(points),
            )
            if (neighbor_ids[(index - 1) % len(points)] != neighbor_ids[index])
        )

        if not junction_indices:
            return ()

        return self._build_boundary_chains(
            points,
            junction_indices=junction_indices,
        )

    def _reduce_fallback_tolerances(
        self,
        regions: tuple[Region, ...],
        *,
        raw_outlines: tuple[Outline, ...],
        invalid_region_ids: set[int],
        pixel_owners: PixelOwners,
        tolerance: float,
        fallback_region_levels: dict[int, int],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
    ) -> bool:
        if tolerance <= 0.0:
            return False

        fallback_extended = False
        reduced_chains: set[BoundaryChain] = set()

        for region, outline in zip(
            regions,
            raw_outlines,
            strict=True,
        ):
            if region.id not in invalid_region_ids:
                continue

            reduce_region_fallback = False

            for points in (
                outline.points,
                *outline.hole_rings,
            ):
                if len(points) <= 3:
                    continue

                neighbor_ids = self._ring_neighbor_ids(
                    region_id=region.id,
                    points=points,
                    pixel_owners=pixel_owners,
                )
                chains = self._build_ring_boundary_chains(
                    points,
                    neighbor_ids=neighbor_ids,
                )

                if chains:
                    for chain in chains:
                        fallback_extended = (
                            self._reduce_chain_fallback(
                                chain,
                                reduced_chains=reduced_chains,
                                fallback_chain_levels=(fallback_chain_levels),
                            )
                            or fallback_extended
                        )
                    continue

                if neighbor_ids and neighbor_ids[0] is not None:
                    fallback_extended = (
                        self._reduce_chain_fallback(
                            self._canonical_ring(
                                points,
                            ),
                            reduced_chains=reduced_chains,
                            fallback_chain_levels=(fallback_chain_levels),
                        )
                        or fallback_extended
                    )
                    continue

                reduce_region_fallback = True

            if reduce_region_fallback:
                current_level = fallback_region_levels.get(
                    region.id,
                    0,
                )
                next_level = self._next_fallback_level(
                    current_level,
                )

                if next_level is not None:
                    fallback_region_levels[region.id] = next_level
                    fallback_extended = True

        return fallback_extended

    def _reduce_chain_fallback(
        self,
        chain: BoundaryChain,
        *,
        reduced_chains: set[BoundaryChain],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
    ) -> bool:
        canonical_chain = self._canonical_chain(
            chain,
        )

        if canonical_chain in reduced_chains:
            return False

        reduced_chains.add(
            canonical_chain,
        )

        current_level = fallback_chain_levels.get(
            canonical_chain,
            0,
        )
        next_level = self._next_fallback_level(
            current_level,
        )

        if next_level is None:
            return False

        fallback_chain_levels[canonical_chain] = next_level

        return True

    @staticmethod
    def _next_fallback_level(
        current_level: int,
    ) -> int | None:
        next_level = current_level + 1

        if next_level >= len(
            FALLBACK_TOLERANCE_FACTORS,
        ):
            return None

        return next_level

    @staticmethod
    def _fallback_tolerance(
        tolerance: float,
        *,
        fallback_level: int,
    ) -> float:
        return tolerance * FALLBACK_TOLERANCE_FACTORS[fallback_level]

    @staticmethod
    def _changed_region_ids(
        previous_outlines: tuple[Outline, ...],
        outlines: tuple[Outline, ...],
    ) -> set[int]:
        previous_by_region = {
            outline.region_id: outline for outline in previous_outlines
        }

        return {
            outline.region_id
            for outline in outlines
            if previous_by_region.get(
                outline.region_id,
            )
            != outline
        }

    @staticmethod
    def _build_pixel_owners(
        regions: tuple[Region, ...],
    ) -> PixelOwners:
        pixel_owners: PixelOwners = {}

        for region in regions:
            for pixel in region.pixels:
                existing_owner = pixel_owners.get(
                    pixel,
                )

                if existing_owner is not None and existing_owner != region.id:
                    raise ValueError(
                        "Region pixels must not overlap.",
                    )

                pixel_owners[pixel] = region.id

        return pixel_owners

    @staticmethod
    def _neighbor_region_id(
        *,
        region_id: int,
        start: Point,
        end: Point,
        pixel_owners: PixelOwners,
    ) -> int | None:
        if start[1] == end[1]:
            x = min(
                start[0],
                end[0],
            )
            y = start[1]

            first_pixel = pack_pixel(
                x,
                y - 1,
            )
            second_pixel = pack_pixel(
                x,
                y,
            )
        elif start[0] == end[0]:
            x = start[0]
            y = min(
                start[1],
                end[1],
            )

            first_pixel = pack_pixel(
                x - 1,
                y,
            )
            second_pixel = pack_pixel(
                x,
                y,
            )
        else:
            raise ValueError(
                "Outline edges must follow the pixel grid.",
            )

        first_owner = pixel_owners.get(
            first_pixel,
        )
        second_owner = pixel_owners.get(
            second_pixel,
        )

        if first_owner == region_id:
            return second_owner

        if second_owner == region_id:
            return first_owner

        raise ValueError(
            "Outline edge does not border its region.",
        )

    @staticmethod
    def _build_boundary_chains(
        points: tuple[Point, ...],
        *,
        junction_indices: tuple[int, ...],
    ) -> tuple[BoundaryChain, ...]:
        chains: list[BoundaryChain] = []

        point_count = len(points)
        junction_count = len(
            junction_indices,
        )

        for index in range(
            junction_count,
        ):
            start_index = junction_indices[index]
            end_index = junction_indices[(index + 1) % junction_count]

            chain = [
                points[start_index],
            ]

            current_index = start_index

            while current_index != end_index:
                current_index = (current_index + 1) % point_count

                chain.append(
                    points[current_index],
                )

            chains.append(
                tuple(chain),
            )

        return tuple(chains)

    def _simplify_boundary_chain(
        self,
        chain: BoundaryChain,
        *,
        simplified_chains: dict[
            BoundaryChain,
            BoundaryChain,
        ],
        fallback_chain_levels: dict[
            BoundaryChain,
            int,
        ],
        tolerance: float,
    ) -> BoundaryChain:
        canonical_chain = self._canonical_chain(
            chain,
        )

        simplified = simplified_chains.get(
            canonical_chain,
        )

        if simplified is None:
            fallback_level = fallback_chain_levels.get(
                canonical_chain,
                0,
            )

            simplified = self._simplifier.simplify_open_chain(
                canonical_chain,
                tolerance=self._fallback_tolerance(
                    tolerance,
                    fallback_level=fallback_level,
                ),
            )

            simplified_chains[canonical_chain] = simplified

        if chain == canonical_chain:
            return simplified

        return tuple(
            reversed(
                simplified,
            )
        )

    @classmethod
    def _canonical_ring(
        cls,
        ring: Ring,
    ) -> Ring:
        if not ring:
            return ring

        forward = cls._rotate_ring_to_minimum(
            ring,
        )
        reversed_ring = cls._rotate_ring_to_minimum(
            tuple(
                reversed(ring),
            )
        )

        return min(
            forward,
            reversed_ring,
        )

    @staticmethod
    def _rotate_ring_to_minimum(
        ring: Ring,
    ) -> Ring:
        minimum_point = min(
            ring,
        )
        candidates = tuple(
            ring[index:] + ring[:index]
            for index, point in enumerate(
                ring,
            )
            if point == minimum_point
        )

        return min(
            candidates,
        )

    @classmethod
    def _orient_ring_like(
        cls,
        ring: Ring,
        reference: Ring,
    ) -> Ring:
        if (
            cls._signed_area_twice(
                ring,
            )
            * cls._signed_area_twice(
                reference,
            )
            < 0
        ):
            ring = tuple(
                reversed(ring),
            )

        return cls._rotate_ring_to_minimum(
            ring,
        )

    @staticmethod
    def _signed_area_twice(
        ring: Ring,
    ) -> int:
        return sum(
            (
                ring[index][0] * ring[(index + 1) % len(ring)][1]
                - ring[(index + 1) % len(ring)][0] * ring[index][1]
            )
            for index in range(
                len(ring),
            )
        )

    @staticmethod
    def _canonical_chain(
        chain: BoundaryChain,
    ) -> BoundaryChain:
        reversed_chain = tuple(
            reversed(chain),
        )

        return min(
            chain,
            reversed_chain,
        )
