# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.color import ImageQuantizer
from pbn.color.color_distance import ColorDistance
from pbn.exceptions import QuantizationPaletteError
from pbn.models import (
    RGB,
    InputImage,
    Palette,
    PaletteColor,
    QuantizedImage,
)

from .quantization_executor_port import (
    QuantizationChunk,
    QuantizationChunkResult,
    QuantizationExecutorPort,
)


class ParallelImageQuantizer:
    """
    Orchestrates deterministic chunked image quantization.
    """

    def __init__(
        self,
        color_distance: ColorDistance,
        executor: QuantizationExecutorPort,
        worker_count: int,
        break_even_workload: int,
    ) -> None:
        if worker_count <= 0:
            raise ValueError(
                "worker_count must be greater than zero",
            )

        self._color_distance = color_distance
        self._executor = executor
        self._worker_count = worker_count
        self._break_even_workload = break_even_workload
        self._sequential_quantizer = ImageQuantizer(
            color_distance=color_distance,
        )

    def quantize(
        self,
        image: InputImage,
        palette: Palette,
    ) -> QuantizedImage:
        """
        Quantize an image using deterministic independent color chunks.
        """
        unique_colors = self._sequential_quantizer.collect_unique_colors(
            image,
        )

        effective_worker_count = min(
            self._worker_count,
            len(unique_colors),
        )

        workload = len(unique_colors) * len(
            palette.colors,
        )

        if effective_worker_count < 2 or workload < self._break_even_workload:
            return self._sequential_quantizer.quantize(
                image,
                palette,
            )

        chunks = self._build_chunks(
            unique_colors,
            effective_worker_count,
        )

        chunk_results = self._executor.quantize_chunks(
            chunks,
            palette,
            self._color_distance,
        )

        color_matches = self._combine_chunk_results(
            unique_colors,
            chunk_results,
            palette,
        )

        return self._sequential_quantizer.reconstruct_quantized_image(
            image,
            color_matches,
        )

    @staticmethod
    def _build_chunks(
        colors: tuple[RGB, ...],
        worker_count: int,
    ) -> tuple[QuantizationChunk, ...]:
        """
        Partition ordered colors into balanced contiguous chunks.

        Each chunk carries its colors as three bytes each, per ADR-0014.
        The order within a chunk and the order of the chunks are what
        lets the results come back as bare indices.
        """
        base_chunk_size, remainder = divmod(
            len(colors),
            worker_count,
        )

        chunks: list[QuantizationChunk] = []
        start = 0

        for chunk_index in range(worker_count):
            chunk_size = base_chunk_size + (1 if chunk_index < remainder else 0)

            end = start + chunk_size

            chunks.append(
                (
                    chunk_index,
                    bytes(
                        channel
                        for color in colors[start:end]
                        for channel in (
                            color.red,
                            color.green,
                            color.blue,
                        )
                    ),
                ),
            )

            start = end

        return tuple(chunks)

    @staticmethod
    def _combine_chunk_results(
        colors: tuple[RGB, ...],
        chunk_results: tuple[
            QuantizationChunkResult,
            ...,
        ],
        palette: Palette,
    ) -> tuple[
        tuple[RGB, PaletteColor],
        ...,
    ]:
        """
        Pair the colors that were sent with the palette colors chosen.

        The results carry indices rather than palette colors, per
        ADR-0014, and the colors they answer are the ones this object
        chunked and still holds. Sorting by chunk index restores the
        order the chunks were built in, which is the order of `colors`.
        """
        ordered_results = sorted(
            chunk_results,
            key=lambda result: result[0],
        )

        palette_indices = b"".join(indices for _, indices in ordered_results)

        if len(palette_indices) != len(colors):
            raise QuantizationPaletteError(
                f"Quantization returned {len(palette_indices)} results "
                f"for {len(colors)} colors.",
            )

        palette_colors = palette.colors

        return tuple(
            (
                color,
                palette_colors[index],
            )
            for color, index in zip(
                colors,
                palette_indices,
                strict=True,
            )
        )
