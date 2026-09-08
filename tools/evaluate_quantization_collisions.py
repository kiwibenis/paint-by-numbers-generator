# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Evaluate palette utilization and quantization collisions.

This developer tool measures where independent nearest-palette-color
quantization collapses distinct source colors onto the same palette color.

It also estimates perceptually distinct source-color groups, evaluates
spatially connected source-color components against the configured physical
paintability constraint, measures how cheaply collapsed local boundaries
could be rescued with alternative palette colors, groups meaningful collapsed
raster edges into spatial boundary components, evaluates collapsed source
contrast across configurable spatial offsets, detects center-surround
structures that disappear during quantization, and measures whether those
detections persist across multiple spatial scales.

It does not change production quantization behavior.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict, deque
from collections.abc import Callable
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from pathlib import Path
from struct import pack
from typing import Protocol

from pbn.application.generator_config_resolver import (
    GeneratorConfigResolver,
)
from pbn.color import (
    ImageQuantizer,
    RgbToLabConverter,
)
from pbn.color.color_distance import ColorDistance
from pbn.infrastructure.config_loader import load_config
from pbn.infrastructure.image_loader import load_image
from pbn.infrastructure.palette_loader import load_palette
from pbn.models import (
    RGB,
    ImageSize,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
)
from pbn.models.pixel_index import pack_pixels
from pbn.regions.circle_fit import RegionCircleFit
from tools.benchmark_region_complexity import (
    EVALUATION_CASES,
    PREVIEW_OUTPUT_DIRECTORY,
    REPOSITORY_ROOT,
    palette_path,
    resolve_color_distance,
)
from tools.developer_image_limits import (
    DEVELOPER_IMAGE_INPUT_LIMITS,
)

GridPoint = tuple[int, int]
Pixel = tuple[int, int]
GridSegment = tuple[GridPoint, GridPoint]


class RgbLabConverter(Protocol):
    """
    Convert RGB colors to CIELAB.
    """

    def convert(
        self,
        rgb: RGB,
    ) -> Lab:
        """
        Convert one RGB color to CIELAB.
        """
        ...


class PixelCircleFit(Protocol):
    """
    Evaluate whether a minimum circle fits into a pixel set.

    The pixels are packed indices, as `pbn.models.pixel_index` defines
    them. This protocol used to declare coordinate pairs and the tool
    passed them, while the only implementation reads every element as a
    packed integer. The call raised TypeError on the first component
    large enough to reach the coordinate arithmetic.
    """

    def fits_pixels(
        self,
        pixels: AbstractSet[int],
        diameter_px: int,
    ) -> bool:
        """
        Return whether the required circle fits inside the pixels.
        """
        ...


@dataclass(frozen=True, slots=True)
class PaletteCandidate:
    """
    One ranked palette candidate for a source color.
    """

    color: PaletteColor
    distance: float
    additional_distance: float


@dataclass(frozen=True, slots=True)
class PaletteUtilizationSummary:
    """
    Aggregate palette-utilization statistics.
    """

    palette_color_count: int
    used_palette_color_count: int
    utilization_fraction: float
    distinct_source_color_count: int
    pixel_count: int


@dataclass(frozen=True, slots=True)
class PaletteUsage:
    """
    Usage statistics for one quantized palette color.
    """

    color: PaletteColor
    source_color_count: int
    pixel_count: int
    pixel_fraction: float


@dataclass(frozen=True, slots=True)
class CollapsedBoundary:
    """
    A local source-color boundary removed by quantization.
    """

    first_source: RGB
    second_source: RGB
    palette_color: PaletteColor
    boundary_length_px: int
    source_pixel_count: int


@dataclass(frozen=True, slots=True)
class SourceColorEvaluation:
    """
    Quantization diagnostics for one distinct source RGB value.
    """

    source: RGB
    pixel_count: int
    candidates: tuple[PaletteCandidate, ...]


@dataclass(frozen=True, slots=True)
class LocalSourceComponent:
    """
    Spatially connected source pixels around one fixed color reference.
    """

    representative: RGB
    pixels: frozenset[tuple[int, int]]
    paintable: bool


@dataclass(frozen=True, slots=True)
class LocalSourceComponentSummary:
    """
    Aggregate statistics for local source-color components.
    """

    component_count: int
    paintable_component_count: int
    unpaintable_component_count: int
    paintable_pixel_count: int
    unpaintable_pixel_count: int


@dataclass(frozen=True, slots=True)
class UnpaintableComponentDiagnostic:
    """
    Diagnostic information for one unpaintable local component.
    """

    representative: RGB
    pixel_count: int

    min_x: int
    min_y: int
    max_x: int
    max_y: int

    neighbor_representative: RGB | None
    shared_boundary_px: int
    neighbor_distance: float | None


@dataclass(frozen=True, slots=True)
class QuantizationRescueDiagnostic:
    """
    Rescue-cost information for one collapsed source-color boundary.
    """

    collision: CollapsedBoundary
    source_distance: float
    first_alternative: PaletteCandidate | None
    second_alternative: PaletteCandidate | None
    minimum_rescue_cost: float | None


@dataclass(frozen=True, slots=True)
class QuantizationRescueSummary:
    """
    Aggregate rescue-cost statistics for collapsed boundaries.
    """

    collision_count: int
    low_source_distance_count: int
    meaningful_collision_count: int
    rescue_cost_le_1_count: int
    rescue_cost_le_2_count: int
    rescue_cost_le_5_count: int
    expensive_rescue_count: int
    unavailable_rescue_count: int

    collision_boundary_length_px: int
    low_source_distance_boundary_length_px: int
    meaningful_boundary_length_px: int
    rescue_cost_le_1_boundary_length_px: int
    rescue_cost_le_2_boundary_length_px: int
    rescue_cost_le_5_boundary_length_px: int
    expensive_rescue_boundary_length_px: int
    unavailable_rescue_boundary_length_px: int


@dataclass(frozen=True, slots=True)
class CollapsedBoundaryComponent:
    """
    Spatially connected meaningful collapsed raster-boundary edges.
    """

    edge_count: int

    min_x: int
    min_y: int
    max_x: int
    max_y: int

    source_distance_min: float
    source_distance_max: float
    source_distance_mean: float

    rescue_cost_min: float | None
    rescue_cost_mean: float | None
    unavailable_rescue_edge_count: int

    dominant_palette_color: PaletteColor

    incident_pixels: frozenset[Pixel]


@dataclass(frozen=True, slots=True)
class OffsetCollapsedPair:
    """
    Two spatially separated source pixels collapsed to one palette color.
    """

    first_pixel: Pixel
    second_pixel: Pixel

    first_source: RGB
    second_source: RGB

    palette_color: PaletteColor
    offset_px: int
    source_distance: float


@dataclass(frozen=True, slots=True)
class OffsetCollapsedSummary:
    """
    Aggregate source-contrast statistics for one spatial offset.
    """

    offset_px: int
    pair_count: int
    source_distance_min: float | None
    source_distance_max: float | None
    source_distance_mean: float | None


@dataclass(frozen=True, slots=True)
class CenterSurroundCandidate:
    """
    One possible thin source structure lost during quantization.

    The two background pixels lie on opposite sides of the center pixel.
    The backgrounds are perceptually similar, while the center differs
    perceptually from both backgrounds. All three pixels nevertheless map
    to the same palette color.
    """

    center_pixel: Pixel
    first_background_pixel: Pixel
    second_background_pixel: Pixel

    orientation: str
    offset_px: int

    center_source: RGB
    first_background_source: RGB
    second_background_source: RGB

    palette_color: PaletteColor

    background_distance: float
    first_center_distance: float
    second_center_distance: float


@dataclass(frozen=True, slots=True)
class CenterSurroundSummary:
    """
    Aggregate center-surround statistics for one spatial offset.
    """

    offset_px: int
    candidate_count: int
    unique_center_count: int
    horizontal_count: int
    vertical_count: int


@dataclass(frozen=True, slots=True)
class CenterSurroundPersistence:
    """
    One center-surround detection supported by multiple spatial offsets.
    """

    center_pixel: Pixel
    supported_offsets: tuple[int, ...]
    candidate_count: int
    horizontal_count: int
    vertical_count: int


@dataclass(frozen=True, slots=True)
class CenterSurroundPersistenceSummary:
    """
    Aggregate multiscale center-surround persistence statistics.
    """

    minimum_offset_support: int
    center_count: int
    support_histogram: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class _SpatialCollapsedBoundaryEdge:
    """
    One concrete collapsed raster edge in image space.
    """

    segment: GridSegment
    incident_pixels: frozenset[Pixel]
    diagnostic: QuantizationRescueDiagnostic


def rank_palette_candidates(
    *,
    source: Lab,
    palette: Palette,
    color_distance: ColorDistance,
    limit: int,
) -> tuple[PaletteCandidate, ...]:
    """
    Rank palette colors by configured color distance.

    Equal-distance candidates preserve palette order, matching the
    deterministic tie-breaking semantics of nearest-color quantization.
    """
    if limit <= 0:
        raise ValueError(
            "limit must be greater than zero",
        )

    if not palette.colors:
        raise ValueError(
            "Palette contains no colors.",
        )

    ranked = sorted(
        (
            (
                color_distance.distance(
                    source,
                    color.lab,
                ),
                index,
                color,
            )
            for index, color in enumerate(
                palette.colors,
            )
        ),
        key=lambda item: (
            item[0],
            item[1],
        ),
    )

    nearest_distance = ranked[0][0]

    return tuple(
        PaletteCandidate(
            color=color,
            distance=distance,
            additional_distance=(distance - nearest_distance),
        )
        for distance, _, color in ranked[:limit]
    )


def cluster_source_colors(
    *,
    colors: tuple[RGB, ...],
    converter: RgbLabConverter,
    color_distance: ColorDistance,
    maximum_distance: float,
) -> tuple[tuple[RGB, ...], ...]:
    """
    Group source colors around fixed first-seen representatives.
    """
    if maximum_distance < 0.0:
        raise ValueError(
            "maximum_distance must not be negative",
        )

    if not colors:
        return ()

    labs = {
        color: converter.convert(
            color,
        )
        for color in colors
    }

    representatives: list[
        tuple[
            RGB,
            Lab,
        ]
    ] = []

    clusters: list[list[RGB]] = []

    for color in colors:
        color_lab = labs[color]

        matching_cluster_index: int | None = None

        for index, (
            _representative,
            representative_lab,
        ) in enumerate(
            representatives,
        ):
            distance = color_distance.distance(
                color_lab,
                representative_lab,
            )

            if distance <= maximum_distance:
                matching_cluster_index = index
                break

        if matching_cluster_index is None:
            representatives.append(
                (
                    color,
                    color_lab,
                ),
            )
            clusters.append(
                [
                    color,
                ],
            )
            continue

        clusters[matching_cluster_index].append(
            color,
        )

    return tuple(
        tuple(
            cluster,
        )
        for cluster in clusters
    )


def build_local_source_components(
    *,
    image: InputImage,
    converter: RgbLabConverter,
    color_distance: ColorDistance,
    maximum_distance: float,
    minimum_circle_diameter_px: int,
    circle_fit: PixelCircleFit,
) -> tuple[LocalSourceComponent, ...]:
    """
    Build four-connected perceptual source-color components.
    """
    if maximum_distance < 0.0:
        raise ValueError(
            "maximum_distance must not be negative",
        )

    if image.width <= 0 or image.height <= 0:
        return ()

    lab_cache: dict[RGB, Lab] = {}

    def lab_for(
        color: RGB,
    ) -> Lab:
        cached = lab_cache.get(
            color,
        )

        if cached is not None:
            return cached

        converted = converter.convert(
            color,
        )
        lab_cache[color] = converted

        return converted

    visited: set[Pixel] = set()

    components: list[LocalSourceComponent] = []

    for start_y in range(
        image.height,
    ):
        for start_x in range(
            image.width,
        ):
            start = (
                start_x,
                start_y,
            )

            if start in visited:
                continue

            representative = image.rgb_at(
                start_x,
                start_y,
            )
            representative_lab = lab_for(
                representative,
            )

            queue: deque[Pixel] = deque(
                (start,),
            )

            visited.add(
                start,
            )

            component_pixels: set[Pixel] = {
                start,
            }

            while queue:
                x, y = queue.popleft()

                for neighbor_x, neighbor_y in (
                    (
                        x - 1,
                        y,
                    ),
                    (
                        x + 1,
                        y,
                    ),
                    (
                        x,
                        y - 1,
                    ),
                    (
                        x,
                        y + 1,
                    ),
                ):
                    if (
                        neighbor_x < 0
                        or neighbor_x >= image.width
                        or neighbor_y < 0
                        or neighbor_y >= image.height
                    ):
                        continue

                    neighbor = (
                        neighbor_x,
                        neighbor_y,
                    )

                    if neighbor in visited:
                        continue

                    neighbor_color = image.rgb_at(
                        neighbor_x,
                        neighbor_y,
                    )

                    neighbor_distance = color_distance.distance(
                        representative_lab,
                        lab_for(
                            neighbor_color,
                        ),
                    )

                    if neighbor_distance > maximum_distance:
                        continue

                    visited.add(
                        neighbor,
                    )
                    component_pixels.add(
                        neighbor,
                    )
                    queue.append(
                        neighbor,
                    )

            frozen_pixels = frozenset(
                component_pixels,
            )

            components.append(
                LocalSourceComponent(
                    representative=representative,
                    pixels=frozen_pixels,
                    paintable=(
                        circle_fit.fits_pixels(
                            # The component is kept as coordinates,
                            # which is what the report prints. Only the
                            # circle test takes packed indices.
                            pack_pixels(
                                frozen_pixels,
                            ),
                            minimum_circle_diameter_px,
                        )
                    ),
                ),
            )

    return tuple(
        components,
    )


def summarize_local_source_components(
    *,
    components: tuple[
        LocalSourceComponent,
        ...,
    ],
) -> LocalSourceComponentSummary:
    """
    Summarize local source-color component paintability.
    """
    paintable_components = tuple(
        component for component in components if component.paintable
    )

    unpaintable_components = tuple(
        component for component in components if not component.paintable
    )

    return LocalSourceComponentSummary(
        component_count=len(
            components,
        ),
        paintable_component_count=len(
            paintable_components,
        ),
        unpaintable_component_count=len(
            unpaintable_components,
        ),
        paintable_pixel_count=sum(
            len(
                component.pixels,
            )
            for component in paintable_components
        ),
        unpaintable_pixel_count=sum(
            len(
                component.pixels,
            )
            for component in unpaintable_components
        ),
    )


def rank_unpaintable_components(
    *,
    image: InputImage,
    components: tuple[
        LocalSourceComponent,
        ...,
    ],
    converter: RgbLabConverter,
    color_distance: ColorDistance,
) -> tuple[UnpaintableComponentDiagnostic, ...]:
    """
    Rank unpaintable components by affected pixel count.
    """
    if not components:
        return ()

    owner_by_pixel = [
        [
            -1
            for _ in range(
                image.width,
            )
        ]
        for _ in range(
            image.height,
        )
    ]

    for component_index, component in enumerate(
        components,
    ):
        for x, y in component.pixels:
            owner_by_pixel[y][x] = component_index

    lab_cache: dict[RGB, Lab] = {}

    def lab_for(
        color: RGB,
    ) -> Lab:
        cached = lab_cache.get(
            color,
        )

        if cached is not None:
            return cached

        converted = converter.convert(
            color,
        )

        lab_cache[color] = converted

        return converted

    diagnostics: list[UnpaintableComponentDiagnostic] = []

    for component_index, component in enumerate(
        components,
    ):
        if component.paintable:
            continue

        min_x = min(x for x, _ in component.pixels)
        min_y = min(y for _, y in component.pixels)
        max_x = max(x for x, _ in component.pixels)
        max_y = max(y for _, y in component.pixels)

        neighboring_boundaries: Counter[int] = Counter()

        for x, y in component.pixels:
            for neighbor_x, neighbor_y in (
                (
                    x - 1,
                    y,
                ),
                (
                    x + 1,
                    y,
                ),
                (
                    x,
                    y - 1,
                ),
                (
                    x,
                    y + 1,
                ),
            ):
                if (
                    neighbor_x < 0
                    or neighbor_x >= image.width
                    or neighbor_y < 0
                    or neighbor_y >= image.height
                ):
                    continue

                neighbor_component_index = owner_by_pixel[neighbor_y][neighbor_x]

                if (
                    neighbor_component_index < 0
                    or neighbor_component_index == component_index
                ):
                    continue

                neighboring_boundaries[neighbor_component_index] += 1

        neighbor_representative: RGB | None = None
        shared_boundary_px = 0
        neighbor_distance: float | None = None

        if neighboring_boundaries:
            representative_lab = lab_for(
                component.representative,
            )

            neighbor_candidates = tuple(
                (
                    -boundary_length,
                    color_distance.distance(
                        representative_lab,
                        lab_for(
                            components[neighbor_component_index].representative,
                        ),
                    ),
                    components[neighbor_component_index].representative.as_tuple(),
                    neighbor_component_index,
                    boundary_length,
                )
                for (
                    neighbor_component_index,
                    boundary_length,
                ) in neighboring_boundaries.items()
            )

            (
                _negative_boundary_length,
                neighbor_distance,
                _neighbor_rgb,
                selected_neighbor_index,
                shared_boundary_px,
            ) = min(
                neighbor_candidates,
            )

            neighbor_representative = components[selected_neighbor_index].representative

        diagnostics.append(
            UnpaintableComponentDiagnostic(
                representative=component.representative,
                pixel_count=len(
                    component.pixels,
                ),
                min_x=min_x,
                min_y=min_y,
                max_x=max_x,
                max_y=max_y,
                neighbor_representative=(neighbor_representative),
                shared_boundary_px=(shared_boundary_px),
                neighbor_distance=(neighbor_distance),
            ),
        )

    return tuple(
        sorted(
            diagnostics,
            key=lambda diagnostic: (
                -diagnostic.pixel_count,
                diagnostic.min_y,
                diagnostic.min_x,
                diagnostic.representative.as_tuple(),
            ),
        ),
    )


def build_unpaintable_component_preview_bmp(
    *,
    image: InputImage,
    components: tuple[
        LocalSourceComponent,
        ...,
    ],
) -> bytes:
    """
    Render unpaintable components in red over the original image.
    """
    unpaintable_pixels = {
        pixel
        for component in components
        if not component.paintable
        for pixel in component.pixels
    }

    return _build_red_overlay_bmp(
        image=image,
        highlighted_pixels=frozenset(
            unpaintable_pixels,
        ),
    )


def unpaintable_component_preview_path(
    *,
    output_directory: Path,
    case: str,
) -> Path:
    """
    Return the deterministic preview path for one evaluation case.
    """
    return output_directory / ("quantization-local-unpaintable-" f"{case}.bmp")


def write_unpaintable_component_preview(
    *,
    output_path: Path,
    image: InputImage,
    components: tuple[
        LocalSourceComponent,
        ...,
    ],
) -> None:
    """
    Write the unpaintable-component diagnostic preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_unpaintable_component_preview_bmp(
            image=image,
            components=components,
        ),
    )


def summarize_palette_utilization(
    *,
    image: InputImage,
    palette: Palette,
    color_matches: dict[RGB, PaletteColor],
) -> PaletteUtilizationSummary:
    """
    Summarize palette utilization for one input image.
    """
    source_pixel_counts = _source_pixel_counts(
        image,
    )

    used_palette_colors = {color_matches[source] for source in source_pixel_counts}

    palette_color_count = len(
        palette.colors,
    )

    utilization_fraction = (
        len(used_palette_colors) / palette_color_count if palette_color_count else 0.0
    )

    return PaletteUtilizationSummary(
        palette_color_count=palette_color_count,
        used_palette_color_count=len(
            used_palette_colors,
        ),
        utilization_fraction=utilization_fraction,
        distinct_source_color_count=len(
            source_pixel_counts,
        ),
        pixel_count=(image.width * image.height),
    )


def build_palette_usage(
    *,
    image: InputImage,
    color_matches: dict[RGB, PaletteColor],
) -> tuple[PaletteUsage, ...]:
    """
    Build deterministic palette-color usage diagnostics.
    """
    source_pixel_counts = _source_pixel_counts(
        image,
    )

    source_counts_by_palette: Counter[PaletteColor] = Counter()

    pixel_counts_by_palette: Counter[PaletteColor] = Counter()

    for source, pixel_count in source_pixel_counts.items():
        palette_color = color_matches[source]

        source_counts_by_palette[palette_color] += 1

        pixel_counts_by_palette[palette_color] += pixel_count

    total_pixels = image.width * image.height

    usage = tuple(
        PaletteUsage(
            color=color,
            source_color_count=(source_counts_by_palette[color]),
            pixel_count=(pixel_counts_by_palette[color]),
            pixel_fraction=(
                pixel_counts_by_palette[color] / total_pixels if total_pixels else 0.0
            ),
        )
        for color in pixel_counts_by_palette
    )

    return tuple(
        sorted(
            usage,
            key=lambda item: (
                -item.pixel_count,
                -item.source_color_count,
                item.color.number,
            ),
        ),
    )


def build_source_color_evaluations(
    *,
    image: InputImage,
    palette: Palette,
    color_distance: ColorDistance,
    candidate_limit: int,
) -> tuple[SourceColorEvaluation, ...]:
    """
    Evaluate nearest palette candidates for all source RGB values.
    """
    converter = RgbToLabConverter()
    source_pixel_counts = _source_pixel_counts(
        image,
    )

    evaluations = tuple(
        SourceColorEvaluation(
            source=source,
            pixel_count=pixel_count,
            candidates=rank_palette_candidates(
                source=converter.convert(
                    source,
                ),
                palette=palette,
                color_distance=color_distance,
                limit=candidate_limit,
            ),
        )
        for source, pixel_count in source_pixel_counts.items()
    )

    return tuple(
        sorted(
            evaluations,
            key=lambda item: (
                -item.pixel_count,
                item.source.as_tuple(),
            ),
        ),
    )


def find_collapsed_boundaries(
    *,
    image: InputImage,
    color_matches: dict[RGB, PaletteColor],
) -> tuple[CollapsedBoundary, ...]:
    """
    Find four-connected source-color boundaries lost by quantization.
    """
    source_pixel_counts = _source_pixel_counts(
        image,
    )

    boundary_lengths: Counter[
        tuple[
            RGB,
            RGB,
            PaletteColor,
        ]
    ] = Counter()

    for y, row in enumerate(
        image.rows(),
    ):
        for x, source in enumerate(
            row,
        ):
            if x + 1 < image.width:
                _record_collapsed_boundary(
                    first=source,
                    second=row[x + 1],
                    color_matches=color_matches,
                    boundary_lengths=boundary_lengths,
                )

            if y + 1 < image.height:
                _record_collapsed_boundary(
                    first=source,
                    second=image.rgb_at(
                        x,
                        y + 1,
                    ),
                    color_matches=color_matches,
                    boundary_lengths=boundary_lengths,
                )

    collisions = tuple(
        CollapsedBoundary(
            first_source=first,
            second_source=second,
            palette_color=palette_color,
            boundary_length_px=boundary_length,
            source_pixel_count=(
                source_pixel_counts[first] + source_pixel_counts[second]
            ),
        )
        for (
            first,
            second,
            palette_color,
        ), boundary_length in boundary_lengths.items()
    )

    return tuple(
        sorted(
            collisions,
            key=lambda collision: (
                -collision.boundary_length_px,
                -collision.source_pixel_count,
                collision.palette_color.number,
                collision.first_source.as_tuple(),
                collision.second_source.as_tuple(),
            ),
        ),
    )


def build_quantization_rescue_diagnostics(
    *,
    collisions: tuple[CollapsedBoundary, ...],
    evaluations_by_source: dict[
        RGB,
        SourceColorEvaluation,
    ],
    converter: RgbLabConverter,
    color_distance: ColorDistance,
) -> tuple[QuantizationRescueDiagnostic, ...]:
    """
    Measure alternative-palette rescue costs for collapsed boundaries.
    """
    lab_cache: dict[RGB, Lab] = {}

    def lab_for(
        color: RGB,
    ) -> Lab:
        cached = lab_cache.get(
            color,
        )

        if cached is not None:
            return cached

        converted = converter.convert(
            color,
        )
        lab_cache[color] = converted

        return converted

    diagnostics: list[QuantizationRescueDiagnostic] = []

    for collision in collisions:
        first_evaluation = evaluations_by_source[collision.first_source]
        second_evaluation = evaluations_by_source[collision.second_source]

        first_alternative = _best_alternative_candidate(
            candidates=first_evaluation.candidates,
            current_color=collision.palette_color,
        )
        second_alternative = _best_alternative_candidate(
            candidates=second_evaluation.candidates,
            current_color=collision.palette_color,
        )

        rescue_costs = tuple(
            candidate.additional_distance
            for candidate in (
                first_alternative,
                second_alternative,
            )
            if candidate is not None
        )

        minimum_rescue_cost = (
            min(
                rescue_costs,
            )
            if rescue_costs
            else None
        )

        diagnostics.append(
            QuantizationRescueDiagnostic(
                collision=collision,
                source_distance=(
                    color_distance.distance(
                        lab_for(
                            collision.first_source,
                        ),
                        lab_for(
                            collision.second_source,
                        ),
                    )
                ),
                first_alternative=first_alternative,
                second_alternative=second_alternative,
                minimum_rescue_cost=minimum_rescue_cost,
            ),
        )

    return tuple(
        diagnostics,
    )


def rank_quantization_rescue_diagnostics(
    *,
    diagnostics: tuple[
        QuantizationRescueDiagnostic,
        ...,
    ],
    source_distance_threshold: float,
) -> tuple[QuantizationRescueDiagnostic, ...]:
    """
    Rank meaningful collapsed boundaries by rescue cost.
    """
    if source_distance_threshold < 0.0:
        raise ValueError(
            "source_distance_threshold must not be negative",
        )

    meaningful = tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.source_distance > source_distance_threshold
    )

    return tuple(
        sorted(
            meaningful,
            key=lambda diagnostic: (
                (
                    diagnostic.minimum_rescue_cost
                    if diagnostic.minimum_rescue_cost is not None
                    else float("inf")
                ),
                -diagnostic.collision.boundary_length_px,
                -diagnostic.source_distance,
                -diagnostic.collision.source_pixel_count,
                diagnostic.collision.palette_color.number,
                diagnostic.collision.first_source.as_tuple(),
                diagnostic.collision.second_source.as_tuple(),
            ),
        ),
    )


def rank_quantization_rescue_diagnostics_by_boundary_impact(
    *,
    diagnostics: tuple[
        QuantizationRescueDiagnostic,
        ...,
    ],
    source_distance_threshold: float,
) -> tuple[QuantizationRescueDiagnostic, ...]:
    """
    Rank meaningful collapsed boundaries by affected boundary length.
    """
    if source_distance_threshold < 0.0:
        raise ValueError(
            "source_distance_threshold must not be negative",
        )

    meaningful = tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.source_distance > source_distance_threshold
    )

    return tuple(
        sorted(
            meaningful,
            key=lambda diagnostic: (
                -diagnostic.collision.boundary_length_px,
                (
                    diagnostic.minimum_rescue_cost
                    if diagnostic.minimum_rescue_cost is not None
                    else float("inf")
                ),
                -diagnostic.source_distance,
                -diagnostic.collision.source_pixel_count,
                diagnostic.collision.palette_color.number,
                diagnostic.collision.first_source.as_tuple(),
                diagnostic.collision.second_source.as_tuple(),
            ),
        ),
    )


def summarize_quantization_rescue_diagnostics(
    *,
    diagnostics: tuple[
        QuantizationRescueDiagnostic,
        ...,
    ],
    source_distance_threshold: float,
) -> QuantizationRescueSummary:
    """
    Summarize rescue availability for meaningful collapsed boundaries.
    """
    if source_distance_threshold < 0.0:
        raise ValueError(
            "source_distance_threshold must not be negative",
        )

    low_source_distance = tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.source_distance <= source_distance_threshold
    )

    meaningful = tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.source_distance > source_distance_threshold
    )

    available = tuple(
        diagnostic
        for diagnostic in meaningful
        if diagnostic.minimum_rescue_cost is not None
    )

    rescue_cost_le_1 = tuple(
        diagnostic
        for diagnostic in available
        if (
            diagnostic.minimum_rescue_cost is not None
            and diagnostic.minimum_rescue_cost <= 1.0
        )
    )

    rescue_cost_le_2 = tuple(
        diagnostic
        for diagnostic in available
        if (
            diagnostic.minimum_rescue_cost is not None
            and diagnostic.minimum_rescue_cost <= 2.0
        )
    )

    rescue_cost_le_5 = tuple(
        diagnostic
        for diagnostic in available
        if (
            diagnostic.minimum_rescue_cost is not None
            and diagnostic.minimum_rescue_cost <= 5.0
        )
    )

    expensive = tuple(
        diagnostic
        for diagnostic in available
        if (
            diagnostic.minimum_rescue_cost is not None
            and diagnostic.minimum_rescue_cost > 5.0
        )
    )

    unavailable = tuple(
        diagnostic
        for diagnostic in meaningful
        if diagnostic.minimum_rescue_cost is None
    )

    return QuantizationRescueSummary(
        collision_count=len(
            diagnostics,
        ),
        low_source_distance_count=len(
            low_source_distance,
        ),
        meaningful_collision_count=len(
            meaningful,
        ),
        rescue_cost_le_1_count=len(
            rescue_cost_le_1,
        ),
        rescue_cost_le_2_count=len(
            rescue_cost_le_2,
        ),
        rescue_cost_le_5_count=len(
            rescue_cost_le_5,
        ),
        expensive_rescue_count=len(
            expensive,
        ),
        unavailable_rescue_count=len(
            unavailable,
        ),
        collision_boundary_length_px=_sum_boundary_lengths(
            diagnostics,
        ),
        low_source_distance_boundary_length_px=(
            _sum_boundary_lengths(
                low_source_distance,
            )
        ),
        meaningful_boundary_length_px=_sum_boundary_lengths(
            meaningful,
        ),
        rescue_cost_le_1_boundary_length_px=(
            _sum_boundary_lengths(
                rescue_cost_le_1,
            )
        ),
        rescue_cost_le_2_boundary_length_px=(
            _sum_boundary_lengths(
                rescue_cost_le_2,
            )
        ),
        rescue_cost_le_5_boundary_length_px=(
            _sum_boundary_lengths(
                rescue_cost_le_5,
            )
        ),
        expensive_rescue_boundary_length_px=(
            _sum_boundary_lengths(
                expensive,
            )
        ),
        unavailable_rescue_boundary_length_px=(
            _sum_boundary_lengths(
                unavailable,
            )
        ),
    )


def find_offset_collapsed_pairs(
    *,
    image: InputImage,
    color_matches: dict[RGB, PaletteColor],
    converter: RgbLabConverter,
    color_distance: ColorDistance,
    offset_px: int,
    source_distance_threshold: float,
) -> tuple[OffsetCollapsedPair, ...]:
    """
    Find spatially separated source pixels collapsed to one palette color.
    """
    if offset_px <= 0:
        raise ValueError(
            "offset_px must be greater than zero",
        )

    if source_distance_threshold < 0.0:
        raise ValueError(
            "source_distance_threshold must not be negative",
        )

    lab_cache: dict[RGB, Lab] = {}

    def lab_for(
        color: RGB,
    ) -> Lab:
        cached = lab_cache.get(
            color,
        )

        if cached is not None:
            return cached

        converted = converter.convert(
            color,
        )

        lab_cache[color] = converted

        return converted

    pairs: list[OffsetCollapsedPair] = []

    for y, row in enumerate(
        image.rows(),
    ):
        for x, first_source in enumerate(
            row,
        ):
            horizontal_x = x + offset_px

            if horizontal_x < image.width:
                second_source = row[horizontal_x]

                pair = _build_offset_collapsed_pair(
                    first_pixel=(
                        x,
                        y,
                    ),
                    second_pixel=(
                        horizontal_x,
                        y,
                    ),
                    first_source=first_source,
                    second_source=second_source,
                    offset_px=offset_px,
                    source_distance_threshold=(source_distance_threshold),
                    color_matches=color_matches,
                    lab_for=lab_for,
                    color_distance=color_distance,
                )

                if pair is not None:
                    pairs.append(
                        pair,
                    )

            vertical_y = y + offset_px

            if vertical_y < image.height:
                second_source = image.rgb_at(
                    x,
                    vertical_y,
                )

                pair = _build_offset_collapsed_pair(
                    first_pixel=(
                        x,
                        y,
                    ),
                    second_pixel=(
                        x,
                        vertical_y,
                    ),
                    first_source=first_source,
                    second_source=second_source,
                    offset_px=offset_px,
                    source_distance_threshold=(source_distance_threshold),
                    color_matches=color_matches,
                    lab_for=lab_for,
                    color_distance=color_distance,
                )

                if pair is not None:
                    pairs.append(
                        pair,
                    )

    return tuple(
        pairs,
    )


def summarize_offset_collapsed_pairs(
    *,
    offset_px: int,
    pairs: tuple[
        OffsetCollapsedPair,
        ...,
    ],
) -> OffsetCollapsedSummary:
    """
    Summarize collapsed source contrast for one spatial offset.
    """
    if offset_px <= 0:
        raise ValueError(
            "offset_px must be greater than zero",
        )

    if not pairs:
        return OffsetCollapsedSummary(
            offset_px=offset_px,
            pair_count=0,
            source_distance_min=None,
            source_distance_max=None,
            source_distance_mean=None,
        )

    source_distances = tuple(pair.source_distance for pair in pairs)

    return OffsetCollapsedSummary(
        offset_px=offset_px,
        pair_count=len(
            pairs,
        ),
        source_distance_min=min(
            source_distances,
        ),
        source_distance_max=max(
            source_distances,
        ),
        source_distance_mean=(
            sum(
                source_distances,
            )
            / len(
                source_distances,
            )
        ),
    )


def format_offset_collapsed_summary(
    summary: OffsetCollapsedSummary,
) -> str:
    """
    Format one spatial-offset collision summary.
    """
    return (
        "offset_collisions="
        f"offset_px={summary.offset_px}, "
        f"pairs={summary.pair_count}, "
        "source_delta_e_min="
        f"{_format_optional_float(summary.source_distance_min)}, "
        "source_delta_e_max="
        f"{_format_optional_float(summary.source_distance_max)}, "
        "source_delta_e_mean="
        f"{_format_optional_float(summary.source_distance_mean)}"
    )


def build_offset_collapsed_pair_preview_bmp(
    *,
    image: InputImage,
    pairs: tuple[
        OffsetCollapsedPair,
        ...,
    ],
) -> bytes:
    """
    Render the endpoints of collapsed offset pairs in red.
    """
    highlighted_pixels = frozenset(
        pixel
        for pair in pairs
        for pixel in (
            pair.first_pixel,
            pair.second_pixel,
        )
    )

    return _build_red_overlay_bmp(
        image=image,
        highlighted_pixels=highlighted_pixels,
    )


def offset_collapsed_pair_preview_path(
    *,
    output_directory: Path,
    case: str,
    offset_px: int,
) -> Path:
    """
    Return the deterministic preview path for one spatial offset.
    """
    return output_directory / (
        "quantization-offset-collisions-" f"{case}-{offset_px}px.bmp"
    )


def write_offset_collapsed_pair_preview(
    *,
    output_path: Path,
    image: InputImage,
    pairs: tuple[
        OffsetCollapsedPair,
        ...,
    ],
) -> None:
    """
    Write one spatial-offset collision preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_offset_collapsed_pair_preview_bmp(
            image=image,
            pairs=pairs,
        ),
    )


def find_center_surround_candidates(
    *,
    image: InputImage,
    color_matches: dict[RGB, PaletteColor],
    converter: RgbLabConverter,
    color_distance: ColorDistance,
    offset_px: int,
    background_distance_threshold: float,
    center_distance_threshold: float,
) -> tuple[CenterSurroundCandidate, ...]:
    """
    Find possible thin structures removed by palette quantization.

    For each center pixel, horizontal and vertical samples are taken at the
    configured offset on opposite sides of the center.

    A sample is accepted when:

    - both background colors are within the background threshold;
    - the center differs from both backgrounds by more than the center
      threshold;
    - both backgrounds and the center map to the same palette color.

    The diagnostic is intentionally local and does not imply that a detected
    center should be preserved by production quantization.
    """
    if offset_px <= 0:
        raise ValueError(
            "offset_px must be greater than zero",
        )

    if background_distance_threshold < 0.0:
        raise ValueError(
            "background_distance_threshold must not be negative",
        )

    if center_distance_threshold < 0.0:
        raise ValueError(
            "center_distance_threshold must not be negative",
        )

    lab_cache: dict[RGB, Lab] = {}

    def lab_for(
        color: RGB,
    ) -> Lab:
        cached = lab_cache.get(
            color,
        )

        if cached is not None:
            return cached

        converted = converter.convert(
            color,
        )

        lab_cache[color] = converted

        return converted

    candidates: list[CenterSurroundCandidate] = []

    for y, row in enumerate(
        image.rows(),
    ):
        for x, center_source in enumerate(
            row,
        ):
            if x - offset_px >= 0 and x + offset_px < image.width:
                first_background_source = row[x - offset_px]
                second_background_source = row[x + offset_px]

                candidate = _build_center_surround_candidate(
                    center_pixel=(
                        x,
                        y,
                    ),
                    first_background_pixel=(
                        x - offset_px,
                        y,
                    ),
                    second_background_pixel=(
                        x + offset_px,
                        y,
                    ),
                    orientation="horizontal",
                    offset_px=offset_px,
                    center_source=center_source,
                    first_background_source=(first_background_source),
                    second_background_source=(second_background_source),
                    color_matches=color_matches,
                    lab_for=lab_for,
                    color_distance=color_distance,
                    background_distance_threshold=(background_distance_threshold),
                    center_distance_threshold=(center_distance_threshold),
                )

                if candidate is not None:
                    candidates.append(
                        candidate,
                    )

            if y - offset_px >= 0 and y + offset_px < image.height:
                first_background_source = image.rgb_at(
                    x,
                    y - offset_px,
                )
                second_background_source = image.rgb_at(
                    x,
                    y + offset_px,
                )

                candidate = _build_center_surround_candidate(
                    center_pixel=(
                        x,
                        y,
                    ),
                    first_background_pixel=(
                        x,
                        y - offset_px,
                    ),
                    second_background_pixel=(
                        x,
                        y + offset_px,
                    ),
                    orientation="vertical",
                    offset_px=offset_px,
                    center_source=center_source,
                    first_background_source=(first_background_source),
                    second_background_source=(second_background_source),
                    color_matches=color_matches,
                    lab_for=lab_for,
                    color_distance=color_distance,
                    background_distance_threshold=(background_distance_threshold),
                    center_distance_threshold=(center_distance_threshold),
                )

                if candidate is not None:
                    candidates.append(
                        candidate,
                    )

    return tuple(
        candidates,
    )


def summarize_center_surround_candidates(
    *,
    offset_px: int,
    candidates: tuple[
        CenterSurroundCandidate,
        ...,
    ],
) -> CenterSurroundSummary:
    """
    Summarize center-surround candidates for one spatial offset.
    """
    if offset_px <= 0:
        raise ValueError(
            "offset_px must be greater than zero",
        )

    return CenterSurroundSummary(
        offset_px=offset_px,
        candidate_count=len(
            candidates,
        ),
        unique_center_count=len(
            {candidate.center_pixel for candidate in candidates},
        ),
        horizontal_count=sum(
            1 for candidate in candidates if candidate.orientation == "horizontal"
        ),
        vertical_count=sum(
            1 for candidate in candidates if candidate.orientation == "vertical"
        ),
    )


def format_center_surround_summary(
    summary: CenterSurroundSummary,
) -> str:
    """
    Format one center-surround diagnostic summary.
    """
    return (
        "center_surround="
        f"offset_px={summary.offset_px}, "
        f"candidates={summary.candidate_count}, "
        f"unique_centers={summary.unique_center_count}, "
        f"horizontal={summary.horizontal_count}, "
        f"vertical={summary.vertical_count}"
    )


def build_center_surround_preview_bmp(
    *,
    image: InputImage,
    candidates: tuple[
        CenterSurroundCandidate,
        ...,
    ],
) -> bytes:
    """
    Render center pixels of center-surround candidates in red.
    """
    highlighted_pixels = frozenset(candidate.center_pixel for candidate in candidates)

    return _build_red_overlay_bmp(
        image=image,
        highlighted_pixels=highlighted_pixels,
    )


def center_surround_preview_path(
    *,
    output_directory: Path,
    case: str,
    offset_px: int,
) -> Path:
    """
    Return the deterministic preview path for one center-surround offset.
    """
    return output_directory / (
        "quantization-center-surround-" f"{case}-{offset_px}px.bmp"
    )


def write_center_surround_preview(
    *,
    output_path: Path,
    image: InputImage,
    candidates: tuple[
        CenterSurroundCandidate,
        ...,
    ],
) -> None:
    """
    Write one center-surround diagnostic preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_center_surround_preview_bmp(
            image=image,
            candidates=candidates,
        ),
    )


def build_center_surround_persistence(
    *,
    candidates: tuple[
        CenterSurroundCandidate,
        ...,
    ],
    minimum_offset_support: int,
) -> tuple[CenterSurroundPersistence, ...]:
    """
    Build multiscale center-surround detections.

    A center is retained only when it is detected at the requested minimum
    number of distinct spatial offsets.

    Horizontal and vertical detections at the same offset contribute multiple
    candidate observations but only one offset of support.
    """
    if minimum_offset_support <= 0:
        raise ValueError(
            "minimum_offset_support must be greater than zero",
        )

    candidates_by_center: dict[
        Pixel,
        list[CenterSurroundCandidate],
    ] = defaultdict(
        list,
    )

    for candidate in candidates:
        candidates_by_center[candidate.center_pixel].append(
            candidate,
        )

    persistent: list[CenterSurroundPersistence] = []

    for center_pixel, center_candidates in candidates_by_center.items():
        supported_offsets = tuple(
            sorted(
                {candidate.offset_px for candidate in center_candidates},
            ),
        )

        if (
            len(
                supported_offsets,
            )
            < minimum_offset_support
        ):
            continue

        persistent.append(
            CenterSurroundPersistence(
                center_pixel=center_pixel,
                supported_offsets=supported_offsets,
                candidate_count=len(
                    center_candidates,
                ),
                horizontal_count=sum(
                    1
                    for candidate in center_candidates
                    if candidate.orientation == "horizontal"
                ),
                vertical_count=sum(
                    1
                    for candidate in center_candidates
                    if candidate.orientation == "vertical"
                ),
            ),
        )

    return tuple(
        sorted(
            persistent,
            key=lambda item: (
                item.center_pixel[1],
                item.center_pixel[0],
            ),
        ),
    )


def summarize_center_surround_persistence(
    *,
    persistence: tuple[
        CenterSurroundPersistence,
        ...,
    ],
    minimum_offset_support: int,
) -> CenterSurroundPersistenceSummary:
    """
    Summarize multiscale center-surround persistence.
    """
    if minimum_offset_support <= 0:
        raise ValueError(
            "minimum_offset_support must be greater than zero",
        )

    support_counts: Counter[int] = Counter(
        len(
            item.supported_offsets,
        )
        for item in persistence
    )

    return CenterSurroundPersistenceSummary(
        minimum_offset_support=minimum_offset_support,
        center_count=len(
            persistence,
        ),
        support_histogram=tuple(
            sorted(
                support_counts.items(),
            ),
        ),
    )


def format_center_surround_persistence_summary(
    summary: CenterSurroundPersistenceSummary,
) -> str:
    """
    Format multiscale center-surround persistence statistics.
    """
    histogram = "|".join(
        f"{support}:{count}" for support, count in summary.support_histogram
    )

    return (
        "center_surround_persistence="
        "minimum_offset_support="
        f"{summary.minimum_offset_support}, "
        f"centers={summary.center_count}, "
        f"support_histogram={histogram}"
    )


def build_center_surround_persistence_preview_bmp(
    *,
    image: InputImage,
    persistence: tuple[
        CenterSurroundPersistence,
        ...,
    ],
) -> bytes:
    """
    Render persistent center-surround centers in red.
    """
    highlighted_pixels = frozenset(item.center_pixel for item in persistence)

    return _build_red_overlay_bmp(
        image=image,
        highlighted_pixels=highlighted_pixels,
    )


def center_surround_persistence_preview_path(
    *,
    output_directory: Path,
    case: str,
) -> Path:
    """
    Return the deterministic multiscale persistence preview path.
    """
    return output_directory / ("quantization-center-surround-persistent-" f"{case}.bmp")


def write_center_surround_persistence_preview(
    *,
    output_path: Path,
    image: InputImage,
    persistence: tuple[
        CenterSurroundPersistence,
        ...,
    ],
) -> None:
    """
    Write the multiscale center-surround persistence preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_center_surround_persistence_preview_bmp(
            image=image,
            persistence=persistence,
        ),
    )


def build_collapsed_boundary_components(
    *,
    image: InputImage,
    color_matches: dict[RGB, PaletteColor],
    rescue_diagnostics: tuple[
        QuantizationRescueDiagnostic,
        ...,
    ],
    source_distance_threshold: float,
) -> tuple[CollapsedBoundaryComponent, ...]:
    """
    Group meaningful collapsed raster edges into spatial components.
    """
    if source_distance_threshold < 0.0:
        raise ValueError(
            "source_distance_threshold must not be negative",
        )

    meaningful_by_key = {
        (
            diagnostic.collision.first_source,
            diagnostic.collision.second_source,
            diagnostic.collision.palette_color,
        ): diagnostic
        for diagnostic in rescue_diagnostics
        if diagnostic.source_distance > source_distance_threshold
    }

    spatial_edges: list[_SpatialCollapsedBoundaryEdge] = []

    for y, row in enumerate(
        image.rows(),
    ):
        for x, source in enumerate(
            row,
        ):
            if x + 1 < image.width:
                right = row[x + 1]

                edge = _build_spatial_collapsed_boundary_edge(
                    first=source,
                    second=right,
                    first_pixel=(
                        x,
                        y,
                    ),
                    second_pixel=(
                        x + 1,
                        y,
                    ),
                    segment=(
                        (
                            x + 1,
                            y,
                        ),
                        (
                            x + 1,
                            y + 1,
                        ),
                    ),
                    color_matches=color_matches,
                    meaningful_by_key=meaningful_by_key,
                )

                if edge is not None:
                    spatial_edges.append(
                        edge,
                    )

            if y + 1 < image.height:
                below = image.rgb_at(
                    x,
                    y + 1,
                )

                edge = _build_spatial_collapsed_boundary_edge(
                    first=source,
                    second=below,
                    first_pixel=(
                        x,
                        y,
                    ),
                    second_pixel=(
                        x,
                        y + 1,
                    ),
                    segment=(
                        (
                            x,
                            y + 1,
                        ),
                        (
                            x + 1,
                            y + 1,
                        ),
                    ),
                    color_matches=color_matches,
                    meaningful_by_key=meaningful_by_key,
                )

                if edge is not None:
                    spatial_edges.append(
                        edge,
                    )

    if not spatial_edges:
        return ()

    edge_indices_by_grid_point: dict[
        GridPoint,
        list[int],
    ] = defaultdict(
        list,
    )

    for edge_index, edge in enumerate(
        spatial_edges,
    ):
        first_point, second_point = edge.segment

        edge_indices_by_grid_point[first_point].append(
            edge_index,
        )
        edge_indices_by_grid_point[second_point].append(
            edge_index,
        )

    visited: set[int] = set()

    components: list[CollapsedBoundaryComponent] = []

    for start_index in range(
        len(
            spatial_edges,
        ),
    ):
        if start_index in visited:
            continue

        queue: deque[int] = deque(
            (start_index,),
        )

        visited.add(
            start_index,
        )

        component_edges: list[_SpatialCollapsedBoundaryEdge] = []

        while queue:
            edge_index = queue.popleft()

            edge = spatial_edges[edge_index]

            component_edges.append(
                edge,
            )

            for grid_point in edge.segment:
                for neighbor_index in edge_indices_by_grid_point[grid_point]:
                    if neighbor_index in visited:
                        continue

                    visited.add(
                        neighbor_index,
                    )
                    queue.append(
                        neighbor_index,
                    )

        components.append(
            _build_collapsed_boundary_component(
                tuple(
                    component_edges,
                ),
            ),
        )

    return tuple(
        components,
    )


def rank_collapsed_boundary_components(
    components: tuple[
        CollapsedBoundaryComponent,
        ...,
    ],
) -> tuple[CollapsedBoundaryComponent, ...]:
    """
    Rank spatial collapsed-boundary components by affected edge count.
    """
    return tuple(
        sorted(
            components,
            key=lambda component: (
                -component.edge_count,
                (
                    component.rescue_cost_mean
                    if component.rescue_cost_mean is not None
                    else float("inf")
                ),
                -component.source_distance_mean,
                component.min_y,
                component.min_x,
                component.max_y,
                component.max_x,
                component.dominant_palette_color.number,
            ),
        ),
    )


def build_collapsed_boundary_component_preview_bmp(
    *,
    image: InputImage,
    components: tuple[
        CollapsedBoundaryComponent,
        ...,
    ],
) -> bytes:
    """
    Render pixels incident to meaningful collapsed boundaries in red.
    """
    highlighted_pixels = frozenset(
        pixel for component in components for pixel in component.incident_pixels
    )

    return _build_red_overlay_bmp(
        image=image,
        highlighted_pixels=highlighted_pixels,
    )


def collapsed_boundary_component_preview_path(
    *,
    output_directory: Path,
    case: str,
) -> Path:
    """
    Return the deterministic collapsed-boundary preview path.
    """
    return output_directory / (
        "quantization-collapsed-boundary-components-" f"{case}.bmp"
    )


def write_collapsed_boundary_component_preview(
    *,
    output_path: Path,
    image: InputImage,
    components: tuple[
        CollapsedBoundaryComponent,
        ...,
    ],
) -> None:
    """
    Write the collapsed-boundary-component diagnostic preview.
    """
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_collapsed_boundary_component_preview_bmp(
            image=image,
            components=components,
        ),
    )


def format_summary(
    *,
    case: str,
    summary: PaletteUtilizationSummary,
    collision_count: int,
    collapsed_boundary_length_px: int,
) -> str:
    """
    Format one case-level quantization summary.
    """
    return (
        f"{case}: "
        f"palette_colors={summary.palette_color_count}, "
        "used_palette_colors="
        f"{summary.used_palette_color_count}, "
        "palette_utilization="
        f"{summary.utilization_fraction:.2%}, "
        "distinct_source_colors="
        f"{summary.distinct_source_color_count}, "
        f"pixels={summary.pixel_count}, "
        f"collapsed_color_pairs={collision_count}, "
        "collapsed_boundary_length_px="
        f"{collapsed_boundary_length_px}"
    )


def format_local_component_summary(
    *,
    maximum_distance: float,
    minimum_circle_diameter_px: int,
    summary: LocalSourceComponentSummary,
) -> str:
    """
    Format one spatial source-component summary.
    """
    total_pixels = summary.paintable_pixel_count + summary.unpaintable_pixel_count

    unpaintable_pixel_fraction = (
        summary.unpaintable_pixel_count / total_pixels if total_pixels else 0.0
    )

    return (
        "local_components="
        f"maximum_delta_e={maximum_distance:.3f}, "
        "minimum_circle_diameter_px="
        f"{minimum_circle_diameter_px}, "
        f"count={summary.component_count}, "
        "paintable="
        f"{summary.paintable_component_count}, "
        "unpaintable="
        f"{summary.unpaintable_component_count}, "
        "paintable_pixels="
        f"{summary.paintable_pixel_count}, "
        "unpaintable_pixels="
        f"{summary.unpaintable_pixel_count}, "
        "unpaintable_pixel_fraction="
        f"{unpaintable_pixel_fraction:.6f}"
    )


def format_unpaintable_component_diagnostic(
    diagnostic: UnpaintableComponentDiagnostic,
) -> str:
    """
    Format one unpaintable-component diagnostic.
    """
    if diagnostic.neighbor_representative is None:
        neighbor = "none"
    else:
        neighbor = str(
            diagnostic.neighbor_representative.as_tuple(),
        )

    if diagnostic.neighbor_distance is None:
        neighbor_distance = "none"
    else:
        neighbor_distance = f"{diagnostic.neighbor_distance:.6f}"

    return (
        "unpaintable_component="
        f"rgb={diagnostic.representative.as_tuple()}, "
        f"pixels={diagnostic.pixel_count}, "
        "bbox="
        f"({diagnostic.min_x},"
        f"{diagnostic.min_y})-"
        f"({diagnostic.max_x},"
        f"{diagnostic.max_y}), "
        f"neighbor_rgb={neighbor}, "
        "shared_boundary_px="
        f"{diagnostic.shared_boundary_px}, "
        "neighbor_delta_e="
        f"{neighbor_distance}"
    )


def format_quantization_rescue_summary(
    *,
    source_distance_threshold: float,
    summary: QuantizationRescueSummary,
) -> str:
    """
    Format aggregate rescue-cost statistics.
    """
    return (
        "rescue_summary="
        "source_delta_e_threshold="
        f"{source_distance_threshold:.3f}, "
        f"collisions={summary.collision_count}, "
        "low_source_delta_e="
        f"{summary.low_source_distance_count}, "
        "meaningful_collisions="
        f"{summary.meaningful_collision_count}, "
        "rescue_cost_le_1="
        f"{summary.rescue_cost_le_1_count}, "
        "rescue_cost_le_2="
        f"{summary.rescue_cost_le_2_count}, "
        "rescue_cost_le_5="
        f"{summary.rescue_cost_le_5_count}, "
        "expensive_rescue="
        f"{summary.expensive_rescue_count}, "
        "unavailable_rescue="
        f"{summary.unavailable_rescue_count}, "
        "boundary_px="
        f"{summary.collision_boundary_length_px}, "
        "low_source_delta_e_boundary_px="
        f"{summary.low_source_distance_boundary_length_px}, "
        "meaningful_boundary_px="
        f"{summary.meaningful_boundary_length_px}, "
        "rescue_cost_le_1_boundary_px="
        f"{summary.rescue_cost_le_1_boundary_length_px}, "
        "rescue_cost_le_2_boundary_px="
        f"{summary.rescue_cost_le_2_boundary_length_px}, "
        "rescue_cost_le_5_boundary_px="
        f"{summary.rescue_cost_le_5_boundary_length_px}, "
        "expensive_rescue_boundary_px="
        f"{summary.expensive_rescue_boundary_length_px}, "
        "unavailable_rescue_boundary_px="
        f"{summary.unavailable_rescue_boundary_length_px}"
    )


def format_quantization_rescue_diagnostic(
    diagnostic: QuantizationRescueDiagnostic,
    *,
    label: str = "rescue",
) -> str:
    """
    Format one collapsed-boundary rescue diagnostic.
    """
    return (
        f"{label}="
        "first_rgb="
        f"{diagnostic.collision.first_source.as_tuple()}, "
        "second_rgb="
        f"{diagnostic.collision.second_source.as_tuple()}, "
        "source_delta_e="
        f"{diagnostic.source_distance:.6f}, "
        "palette_number="
        f"{diagnostic.collision.palette_color.number}, "
        "palette_name="
        f"{diagnostic.collision.palette_color.name}, "
        "boundary_length_px="
        f"{diagnostic.collision.boundary_length_px}, "
        "source_pixel_count="
        f"{diagnostic.collision.source_pixel_count}, "
        "first_alternative="
        f"{_format_optional_candidate(diagnostic.first_alternative)}, "
        "second_alternative="
        f"{_format_optional_candidate(diagnostic.second_alternative)}, "
        "minimum_rescue_cost="
        f"{_format_optional_float(diagnostic.minimum_rescue_cost)}"
    )


def format_collapsed_boundary_component(
    component: CollapsedBoundaryComponent,
) -> str:
    """
    Format one spatial collapsed-boundary component.
    """
    return (
        "boundary_component="
        f"edges={component.edge_count}, "
        "bbox="
        f"({component.min_x},"
        f"{component.min_y})-"
        f"({component.max_x},"
        f"{component.max_y}), "
        "source_delta_e_min="
        f"{component.source_distance_min:.6f}, "
        "source_delta_e_max="
        f"{component.source_distance_max:.6f}, "
        "source_delta_e_mean="
        f"{component.source_distance_mean:.6f}, "
        "rescue_cost_min="
        f"{_format_optional_float(component.rescue_cost_min)}, "
        "rescue_cost_mean="
        f"{_format_optional_float(component.rescue_cost_mean)}, "
        "unavailable_rescue_edges="
        f"{component.unavailable_rescue_edge_count}, "
        "palette_number="
        f"{component.dominant_palette_color.number}, "
        "palette_name="
        f"{component.dominant_palette_color.name}"
    )


def format_palette_usage(
    usage: PaletteUsage,
) -> str:
    """
    Format one palette usage record.
    """
    return (
        "palette_usage="
        f"number={usage.color.number}, "
        f"name={usage.color.name}, "
        "source_colors="
        f"{usage.source_color_count}, "
        f"pixels={usage.pixel_count}, "
        f"pixel_fraction={usage.pixel_fraction:.6f}"
    )


def format_collision(
    *,
    collision: CollapsedBoundary,
    evaluations_by_source: dict[
        RGB,
        SourceColorEvaluation,
    ],
) -> str:
    """
    Format one collapsed-boundary diagnostic.
    """
    first = evaluations_by_source[collision.first_source]
    second = evaluations_by_source[collision.second_source]

    return (
        "collision="
        f"first_rgb={collision.first_source.as_tuple()}, "
        f"second_rgb={collision.second_source.as_tuple()}, "
        "palette_number="
        f"{collision.palette_color.number}, "
        "palette_name="
        f"{collision.palette_color.name}, "
        "boundary_length_px="
        f"{collision.boundary_length_px}, "
        "source_pixel_count="
        f"{collision.source_pixel_count}, "
        "first_candidates="
        f"{_format_candidates(first.candidates)}, "
        "second_candidates="
        f"{_format_candidates(second.candidates)}"
    )


def _build_center_surround_candidate(
    *,
    center_pixel: Pixel,
    first_background_pixel: Pixel,
    second_background_pixel: Pixel,
    orientation: str,
    offset_px: int,
    center_source: RGB,
    first_background_source: RGB,
    second_background_source: RGB,
    color_matches: dict[RGB, PaletteColor],
    lab_for: Callable[[RGB], Lab],
    color_distance: ColorDistance,
    background_distance_threshold: float,
    center_distance_threshold: float,
) -> CenterSurroundCandidate | None:
    center_palette_color = color_matches[center_source]

    first_background_palette_color = color_matches[first_background_source]

    second_background_palette_color = color_matches[second_background_source]

    if not (
        center_palette_color
        == first_background_palette_color
        == second_background_palette_color
    ):
        return None

    first_background_lab = lab_for(
        first_background_source,
    )

    second_background_lab = lab_for(
        second_background_source,
    )

    center_lab = lab_for(
        center_source,
    )

    background_distance = color_distance.distance(
        first_background_lab,
        second_background_lab,
    )

    if background_distance > background_distance_threshold:
        return None

    first_center_distance = color_distance.distance(
        first_background_lab,
        center_lab,
    )

    if first_center_distance <= center_distance_threshold:
        return None

    second_center_distance = color_distance.distance(
        second_background_lab,
        center_lab,
    )

    if second_center_distance <= center_distance_threshold:
        return None

    return CenterSurroundCandidate(
        center_pixel=center_pixel,
        first_background_pixel=first_background_pixel,
        second_background_pixel=second_background_pixel,
        orientation=orientation,
        offset_px=offset_px,
        center_source=center_source,
        first_background_source=first_background_source,
        second_background_source=second_background_source,
        palette_color=center_palette_color,
        background_distance=background_distance,
        first_center_distance=first_center_distance,
        second_center_distance=second_center_distance,
    )


def _build_offset_collapsed_pair(
    *,
    first_pixel: Pixel,
    second_pixel: Pixel,
    first_source: RGB,
    second_source: RGB,
    offset_px: int,
    source_distance_threshold: float,
    color_matches: dict[RGB, PaletteColor],
    lab_for: Callable[[RGB], Lab],
    color_distance: ColorDistance,
) -> OffsetCollapsedPair | None:
    first_palette_color = color_matches[first_source]
    second_palette_color = color_matches[second_source]

    if first_palette_color != second_palette_color:
        return None

    source_distance = color_distance.distance(
        lab_for(
            first_source,
        ),
        lab_for(
            second_source,
        ),
    )

    if source_distance <= source_distance_threshold:
        return None

    return OffsetCollapsedPair(
        first_pixel=first_pixel,
        second_pixel=second_pixel,
        first_source=first_source,
        second_source=second_source,
        palette_color=first_palette_color,
        offset_px=offset_px,
        source_distance=source_distance,
    )


def _build_spatial_collapsed_boundary_edge(
    *,
    first: RGB,
    second: RGB,
    first_pixel: Pixel,
    second_pixel: Pixel,
    segment: GridSegment,
    color_matches: dict[
        RGB,
        PaletteColor,
    ],
    meaningful_by_key: dict[
        tuple[
            RGB,
            RGB,
            PaletteColor,
        ],
        QuantizationRescueDiagnostic,
    ],
) -> _SpatialCollapsedBoundaryEdge | None:
    if first == second:
        return None

    first_palette_color = color_matches[first]
    second_palette_color = color_matches[second]

    if first_palette_color != second_palette_color:
        return None

    canonical_first, canonical_second = _canonical_source_pair(
        first,
        second,
    )

    diagnostic = meaningful_by_key.get(
        (
            canonical_first,
            canonical_second,
            first_palette_color,
        ),
    )

    if diagnostic is None:
        return None

    return _SpatialCollapsedBoundaryEdge(
        segment=segment,
        incident_pixels=frozenset(
            (
                first_pixel,
                second_pixel,
            ),
        ),
        diagnostic=diagnostic,
    )


def _build_collapsed_boundary_component(
    edges: tuple[
        _SpatialCollapsedBoundaryEdge,
        ...,
    ],
) -> CollapsedBoundaryComponent:
    incident_pixels = frozenset(
        pixel for edge in edges for pixel in edge.incident_pixels
    )

    source_distances = tuple(edge.diagnostic.source_distance for edge in edges)

    rescue_costs = tuple(
        edge.diagnostic.minimum_rescue_cost
        for edge in edges
        if edge.diagnostic.minimum_rescue_cost is not None
    )

    palette_counts: Counter[PaletteColor] = Counter(
        edge.diagnostic.collision.palette_color for edge in edges
    )

    dominant_palette_color = min(
        palette_counts,
        key=lambda color: (
            -palette_counts[color],
            color.number,
        ),
    )

    return CollapsedBoundaryComponent(
        edge_count=len(
            edges,
        ),
        min_x=min(x for x, _ in incident_pixels),
        min_y=min(y for _, y in incident_pixels),
        max_x=max(x for x, _ in incident_pixels),
        max_y=max(y for _, y in incident_pixels),
        source_distance_min=min(
            source_distances,
        ),
        source_distance_max=max(
            source_distances,
        ),
        source_distance_mean=(
            sum(
                source_distances,
            )
            / len(
                source_distances,
            )
        ),
        rescue_cost_min=(
            min(
                rescue_costs,
            )
            if rescue_costs
            else None
        ),
        rescue_cost_mean=(
            sum(
                rescue_costs,
            )
            / len(
                rescue_costs,
            )
            if rescue_costs
            else None
        ),
        unavailable_rescue_edge_count=sum(
            1 for edge in edges if edge.diagnostic.minimum_rescue_cost is None
        ),
        dominant_palette_color=dominant_palette_color,
        incident_pixels=incident_pixels,
    )


def _best_alternative_candidate(
    *,
    candidates: tuple[
        PaletteCandidate,
        ...,
    ],
    current_color: PaletteColor,
) -> PaletteCandidate | None:
    return next(
        (candidate for candidate in candidates if candidate.color != current_color),
        None,
    )


def _sum_boundary_lengths(
    diagnostics: tuple[
        QuantizationRescueDiagnostic,
        ...,
    ],
) -> int:
    return sum(diagnostic.collision.boundary_length_px for diagnostic in diagnostics)


def _build_red_overlay_bmp(
    *,
    image: InputImage,
    highlighted_pixels: frozenset[Pixel],
) -> bytes:
    width = image.width
    height = image.height

    bytes_per_pixel = 3
    unpadded_row_size = width * bytes_per_pixel
    row_size = (unpadded_row_size + 3) & ~3
    pixel_data_size = row_size * height

    pixel_data = bytearray(
        pixel_data_size,
    )

    for y, row in enumerate(
        image.rows(),
    ):
        for x, color in enumerate(
            row,
        ):
            offset = y * row_size + x * bytes_per_pixel

            if (
                x,
                y,
            ) in highlighted_pixels:
                red = 255
                green = 0
                blue = 0
            else:
                red = color.red
                green = color.green
                blue = color.blue

            pixel_data[offset] = blue
            pixel_data[offset + 1] = green
            pixel_data[offset + 2] = red

    pixel_offset = 54
    file_size = pixel_offset + pixel_data_size

    file_header = b"BM" + pack(
        "<IHHI",
        file_size,
        0,
        0,
        pixel_offset,
    )

    information_header = pack(
        "<IiiHHIIiiII",
        40,
        width,
        -height,
        1,
        24,
        0,
        pixel_data_size,
        2835,
        2835,
        0,
        0,
    )

    return (
        file_header
        + information_header
        + bytes(
            pixel_data,
        )
    )


def _format_optional_candidate(
    candidate: PaletteCandidate | None,
) -> str:
    if candidate is None:
        return "none"

    return (
        f"{candidate.color.number}:"
        f"{candidate.color.name}:"
        f"distance={candidate.distance:.6f}:"
        "additional="
        f"{candidate.additional_distance:.6f}"
    )


def _format_optional_float(
    value: float | None,
) -> str:
    if value is None:
        return "none"

    return f"{value:.6f}"


def _format_candidates(
    candidates: tuple[
        PaletteCandidate,
        ...,
    ],
) -> str:
    return "|".join(
        (
            f"{candidate.color.number}:"
            f"{candidate.color.name}:"
            f"distance={candidate.distance:.6f}:"
            "additional="
            f"{candidate.additional_distance:.6f}"
        )
        for candidate in candidates
    )


def _source_pixel_counts(
    image: InputImage,
) -> Counter[RGB]:
    return Counter(pixel for row in image.rows() for pixel in row)


def _canonical_source_pair(
    first: RGB,
    second: RGB,
) -> tuple[RGB, RGB]:
    if first.as_tuple() <= second.as_tuple():
        return (
            first,
            second,
        )

    return (
        second,
        first,
    )


def _record_collapsed_boundary(
    *,
    first: RGB,
    second: RGB,
    color_matches: dict[
        RGB,
        PaletteColor,
    ],
    boundary_lengths: Counter[
        tuple[
            RGB,
            RGB,
            PaletteColor,
        ]
    ],
) -> None:
    if first == second:
        return

    first_palette_color = color_matches[first]
    second_palette_color = color_matches[second]

    if first_palette_color != second_palette_color:
        return

    canonical_first, canonical_second = _canonical_source_pair(
        first,
        second,
    )

    boundary_lengths[
        (
            canonical_first,
            canonical_second,
            first_palette_color,
        )
    ] += 1


def build_parser() -> ArgumentParser:
    """
    Build the quantization-collision evaluation parser.
    """
    parser = ArgumentParser(
        description=(
            "Evaluate palette utilization, perceptual source-color groups, "
            "local paintability, collapsed boundaries, spatial boundary "
            "components, spatial offset collisions, center-surround "
            "structures, multiscale persistence and alternative-palette "
            "rescue costs."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=(REPOSITORY_ROOT / "config" / "example.toml"),
    )

    parser.add_argument(
        "--cases",
        nargs="+",
        choices=EVALUATION_CASES,
        default=EVALUATION_CASES,
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
        default=None,
    )

    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--palette-usage-limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--collision-limit",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--cluster-thresholds",
        nargs="+",
        type=float,
        default=(
            1.0,
            2.0,
        ),
    )

    parser.add_argument(
        "--local-component-threshold",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--unpaintable-component-limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--preview-output-directory",
        type=Path,
        default=PREVIEW_OUTPUT_DIRECTORY,
    )

    parser.add_argument(
        "--rescue-source-distance-threshold",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--rescue-limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--boundary-component-limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--offset-distances",
        nargs="+",
        type=int,
        default=(
            2,
            4,
            8,
        ),
    )

    parser.add_argument(
        "--center-surround-offsets",
        nargs="+",
        type=int,
        default=(
            2,
            4,
            8,
        ),
    )

    parser.add_argument(
        "--center-surround-background-threshold",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--center-surround-center-threshold",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--center-surround-min-offset-support",
        type=int,
        default=2,
    )

    return parser


def main() -> None:
    """
    Run quantization-collision diagnostics.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.candidate_limit <= 0:
        parser.error(
            "--candidate-limit must be greater than zero",
        )

    if args.palette_usage_limit <= 0:
        parser.error(
            "--palette-usage-limit must be greater than zero",
        )

    if args.collision_limit <= 0:
        parser.error(
            "--collision-limit must be greater than zero",
        )

    if args.unpaintable_component_limit <= 0:
        parser.error(
            "--unpaintable-component-limit must be greater than zero",
        )

    if args.rescue_limit <= 0:
        parser.error(
            "--rescue-limit must be greater than zero",
        )

    if args.boundary_component_limit <= 0:
        parser.error(
            "--boundary-component-limit must be greater than zero",
        )

    if any(threshold < 0.0 for threshold in args.cluster_thresholds):
        parser.error(
            "--cluster-thresholds must not contain negative values",
        )

    if args.local_component_threshold < 0.0:
        parser.error(
            "--local-component-threshold must not be negative",
        )

    if args.rescue_source_distance_threshold < 0.0:
        parser.error(
            "--rescue-source-distance-threshold must not be negative",
        )

    if any(offset <= 0 for offset in args.offset_distances):
        parser.error(
            "--offset-distances must contain only positive values",
        )

    if any(offset <= 0 for offset in args.center_surround_offsets):
        parser.error(
            "--center-surround-offsets must contain only positive values",
        )

    if args.center_surround_background_threshold < 0.0:
        parser.error(
            "--center-surround-background-threshold must not be negative",
        )

    if args.center_surround_center_threshold < 0.0:
        parser.error(
            "--center-surround-center-threshold must not be negative",
        )

    if args.center_surround_min_offset_support <= 0:
        parser.error(
            "--center-surround-min-offset-support must be greater than zero",
        )

    config = load_config(
        args.config,
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
            palette_version=selected_palette_version,
        ),
    )

    color_distance = resolve_color_distance(
        selected_color_distance,
    )

    quantizer = ImageQuantizer(
        color_distance=color_distance,
    )

    converter = RgbToLabConverter()
    circle_fit = RegionCircleFit()
    config_resolver = GeneratorConfigResolver()

    print(
        (
            f"palette={selected_palette}, "
            "palette_version="
            f"{selected_palette_version}, "
            "color_distance="
            f"{selected_color_distance}, "
            "minimum_region_size_mm="
            f"{config.minimum_region_size_mm}, "
            "candidate_limit="
            f"{args.candidate_limit}, "
            "cluster_thresholds="
            f"{tuple(args.cluster_thresholds)}, "
            "local_component_threshold="
            f"{args.local_component_threshold}, "
            "rescue_source_distance_threshold="
            f"{args.rescue_source_distance_threshold}, "
            "offset_distances="
            f"{tuple(args.offset_distances)}, "
            "center_surround_offsets="
            f"{tuple(args.center_surround_offsets)}, "
            "center_surround_background_threshold="
            f"{args.center_surround_background_threshold}, "
            "center_surround_center_threshold="
            f"{args.center_surround_center_threshold}, "
            "center_surround_min_offset_support="
            f"{args.center_surround_min_offset_support}"
        ),
    )

    for case in args.cases:
        image_path = REPOSITORY_ROOT / "examples" / "input" / f"{case}.png"

        image = load_image(
            image_path,
            DEVELOPER_IMAGE_INPUT_LIMITS,
        )

        image_size = ImageSize(
            width=image.width,
            height=image.height,
        )

        minimum_circle_diameter_px = config_resolver.calculate_minimum_circle_diameter(
            config=config,
            image_size=image_size,
        )

        unique_colors = quantizer.collect_unique_colors(
            image,
        )

        color_matches_tuple = quantizer.quantize_colors(
            unique_colors,
            palette,
        )

        color_matches = dict(
            color_matches_tuple,
        )

        summary = summarize_palette_utilization(
            image=image,
            palette=palette,
            color_matches=color_matches,
        )

        usage = build_palette_usage(
            image=image,
            color_matches=color_matches,
        )

        evaluations = build_source_color_evaluations(
            image=image,
            palette=palette,
            color_distance=color_distance,
            candidate_limit=args.candidate_limit,
        )

        evaluations_by_source = {
            evaluation.source: evaluation for evaluation in evaluations
        }

        collisions = find_collapsed_boundaries(
            image=image,
            color_matches=color_matches,
        )

        collapsed_boundary_length_px = sum(
            collision.boundary_length_px for collision in collisions
        )

        rescue_diagnostics = build_quantization_rescue_diagnostics(
            collisions=collisions,
            evaluations_by_source=evaluations_by_source,
            converter=converter,
            color_distance=color_distance,
        )

        rescue_summary = summarize_quantization_rescue_diagnostics(
            diagnostics=rescue_diagnostics,
            source_distance_threshold=(args.rescue_source_distance_threshold),
        )

        ranked_rescue_diagnostics = rank_quantization_rescue_diagnostics(
            diagnostics=rescue_diagnostics,
            source_distance_threshold=(args.rescue_source_distance_threshold),
        )

        boundary_impact_diagnostics = (
            rank_quantization_rescue_diagnostics_by_boundary_impact(
                diagnostics=rescue_diagnostics,
                source_distance_threshold=(args.rescue_source_distance_threshold),
            )
        )

        boundary_components = build_collapsed_boundary_components(
            image=image,
            color_matches=color_matches,
            rescue_diagnostics=rescue_diagnostics,
            source_distance_threshold=(args.rescue_source_distance_threshold),
        )

        ranked_boundary_components = rank_collapsed_boundary_components(
            boundary_components,
        )

        print(
            format_summary(
                case=case,
                summary=summary,
                collision_count=len(
                    collisions,
                ),
                collapsed_boundary_length_px=(collapsed_boundary_length_px),
            ),
        )

        print(
            "  "
            + format_quantization_rescue_summary(
                source_distance_threshold=(args.rescue_source_distance_threshold),
                summary=rescue_summary,
            ),
        )

        print(
            "  "
            "boundary_components="
            f"count={len(boundary_components)}, "
            "edges="
            f"{sum(component.edge_count for component in boundary_components)}",
        )

        for offset_px in args.offset_distances:
            offset_pairs = find_offset_collapsed_pairs(
                image=image,
                color_matches=color_matches,
                converter=converter,
                color_distance=color_distance,
                offset_px=offset_px,
                source_distance_threshold=(args.rescue_source_distance_threshold),
            )

            offset_summary = summarize_offset_collapsed_pairs(
                offset_px=offset_px,
                pairs=offset_pairs,
            )

            print(
                "  "
                + format_offset_collapsed_summary(
                    offset_summary,
                ),
            )

            offset_preview_output_path = offset_collapsed_pair_preview_path(
                output_directory=(args.preview_output_directory),
                case=case,
                offset_px=offset_px,
            )

            write_offset_collapsed_pair_preview(
                output_path=offset_preview_output_path,
                image=image,
                pairs=offset_pairs,
            )

            print(
                "  "
                "offset_collision_preview="
                f"offset_px={offset_px}, "
                f"path={offset_preview_output_path}",
            )

        all_center_surround_candidates: list[CenterSurroundCandidate] = []

        for offset_px in args.center_surround_offsets:
            center_surround_candidates = find_center_surround_candidates(
                image=image,
                color_matches=color_matches,
                converter=converter,
                color_distance=color_distance,
                offset_px=offset_px,
                background_distance_threshold=(
                    args.center_surround_background_threshold
                ),
                center_distance_threshold=(args.center_surround_center_threshold),
            )

            all_center_surround_candidates.extend(
                center_surround_candidates,
            )

            center_surround_summary = summarize_center_surround_candidates(
                offset_px=offset_px,
                candidates=center_surround_candidates,
            )

            print(
                "  "
                + format_center_surround_summary(
                    center_surround_summary,
                ),
            )

            center_surround_output_path = center_surround_preview_path(
                output_directory=(args.preview_output_directory),
                case=case,
                offset_px=offset_px,
            )

            write_center_surround_preview(
                output_path=center_surround_output_path,
                image=image,
                candidates=center_surround_candidates,
            )

            print(
                "  "
                "center_surround_preview="
                f"offset_px={offset_px}, "
                f"path={center_surround_output_path}",
            )

        center_surround_persistence = build_center_surround_persistence(
            candidates=tuple(
                all_center_surround_candidates,
            ),
            minimum_offset_support=(args.center_surround_min_offset_support),
        )

        center_surround_persistence_summary = summarize_center_surround_persistence(
            persistence=center_surround_persistence,
            minimum_offset_support=(args.center_surround_min_offset_support),
        )

        print(
            "  "
            + format_center_surround_persistence_summary(
                center_surround_persistence_summary,
            ),
        )

        center_surround_persistence_output_path = (
            center_surround_persistence_preview_path(
                output_directory=(args.preview_output_directory),
                case=case,
            )
        )

        write_center_surround_persistence_preview(
            output_path=(center_surround_persistence_output_path),
            image=image,
            persistence=center_surround_persistence,
        )

        print(
            "  "
            "center_surround_persistence_preview="
            f"{center_surround_persistence_output_path}",
        )

        for rescue_diagnostic in ranked_rescue_diagnostics[: args.rescue_limit]:
            print(
                "  "
                + format_quantization_rescue_diagnostic(
                    rescue_diagnostic,
                ),
            )

        for rescue_diagnostic in boundary_impact_diagnostics[: args.rescue_limit]:
            print(
                "  "
                + format_quantization_rescue_diagnostic(
                    rescue_diagnostic,
                    label="rescue_impact",
                ),
            )

        for component in ranked_boundary_components[: args.boundary_component_limit]:
            print(
                "  "
                + format_collapsed_boundary_component(
                    component,
                ),
            )

        boundary_preview_output_path = collapsed_boundary_component_preview_path(
            output_directory=(args.preview_output_directory),
            case=case,
        )

        write_collapsed_boundary_component_preview(
            output_path=boundary_preview_output_path,
            image=image,
            components=boundary_components,
        )

        print(
            "  " "boundary_component_preview=" f"{boundary_preview_output_path}",
        )

        for threshold in args.cluster_thresholds:
            clusters = cluster_source_colors(
                colors=unique_colors,
                converter=converter,
                color_distance=color_distance,
                maximum_distance=threshold,
            )

            print(
                "  "
                "source_clusters="
                f"maximum_delta_e={threshold:.3f}, "
                f"count={len(clusters)}"
            )

        local_components = build_local_source_components(
            image=image,
            converter=converter,
            color_distance=color_distance,
            maximum_distance=(args.local_component_threshold),
            minimum_circle_diameter_px=(minimum_circle_diameter_px),
            circle_fit=circle_fit,
        )

        local_component_summary = summarize_local_source_components(
            components=local_components,
        )

        print(
            "  "
            + format_local_component_summary(
                maximum_distance=(args.local_component_threshold),
                minimum_circle_diameter_px=(minimum_circle_diameter_px),
                summary=local_component_summary,
            ),
        )

        unpaintable_diagnostics = rank_unpaintable_components(
            image=image,
            components=local_components,
            converter=converter,
            color_distance=color_distance,
        )

        for diagnostic in unpaintable_diagnostics[: args.unpaintable_component_limit]:
            print(
                "  "
                + format_unpaintable_component_diagnostic(
                    diagnostic,
                ),
            )

        preview_output_path = unpaintable_component_preview_path(
            output_directory=args.preview_output_directory,
            case=case,
        )

        write_unpaintable_component_preview(
            output_path=preview_output_path,
            image=image,
            components=local_components,
        )

        print(
            "  " "unpaintable_preview=" f"{preview_output_path}",
        )

        for item in usage[: args.palette_usage_limit]:
            print(
                "  "
                + format_palette_usage(
                    item,
                ),
            )

        for collision in collisions[: args.collision_limit]:
            print(
                "  "
                + format_collision(
                    collision=collision,
                    evaluations_by_source=(evaluations_by_source),
                ),
            )


if __name__ == "__main__":
    main()
