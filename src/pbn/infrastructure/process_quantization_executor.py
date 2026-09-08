# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from concurrent.futures import (
    FIRST_EXCEPTION,
    ProcessPoolExecutor,
    as_completed,
    wait,
)
from multiprocessing import get_context

from pbn.application.quantization_executor_port import (
    COLOR_BYTES,
    QuantizationChunk,
    QuantizationChunkResult,
    ensure_addressable_palette,
)
from pbn.color import ImageQuantizer
from pbn.color.color_distance import ColorDistance
from pbn.exceptions import InvariantViolationError
from pbn.models import RGB, Palette


def _quantize_chunk(
    chunk: QuantizationChunk,
    palette: Palette,
    color_distance: ColorDistance,
) -> QuantizationChunkResult:
    """
    Quantize one independent color chunk inside a worker process.

    Unpacks the colors and packs the answer back into palette indices,
    per ADR-0014. The compaction lives here rather than in the quantizer
    because it is a property of the transport, and the quantizer speaks
    the vocabulary of the domain.
    """
    chunk_index, packed_colors = chunk

    quantizer = ImageQuantizer(
        color_distance=color_distance,
    )

    matches = quantizer.quantize_colors(
        tuple(
            RGB(
                red=packed_colors[offset],
                green=packed_colors[offset + 1],
                blue=packed_colors[offset + 2],
            )
            for offset in range(
                0,
                len(packed_colors),
                COLOR_BYTES,
            )
        ),
        palette,
    )

    index_by_color = {
        color: index
        for index, color in enumerate(
            palette.colors,
        )
    }

    return (
        chunk_index,
        bytes(index_by_color[palette_color] for _, palette_color in matches),
    )


class ProcessQuantizationExecutor:
    """
    Executes independent quantization chunks in worker processes.
    """

    def quantize_chunks(
        self,
        chunks: tuple[QuantizationChunk, ...],
        palette: Palette,
        color_distance: ColorDistance,
    ) -> tuple[QuantizationChunkResult, ...]:
        """
        Quantize chunks using spawn-based worker processes.
        """
        ensure_addressable_palette(
            palette,
        )

        if not chunks:
            return ()

        context = get_context(
            "spawn",
        )

        with ProcessPoolExecutor(
            max_workers=len(chunks),
            mp_context=context,
        ) as executor:
            futures = tuple(
                executor.submit(
                    _quantize_chunk,
                    chunk,
                    palette,
                    color_distance,
                )
                for chunk in chunks
            )

            done, not_done = wait(
                futures,
                return_when=FIRST_EXCEPTION,
            )

            failed_future = next(
                (future for future in done if future.exception() is not None),
                None,
            )

            if failed_future is not None:
                for future in not_done:
                    future.cancel()

                exception = failed_future.exception()

                if exception is None:
                    raise InvariantViolationError(
                        "Parallel quantization failed " "without an exception.",
                    )

                raise exception

            return tuple(
                future.result()
                for future in as_completed(
                    futures,
                )
            )
