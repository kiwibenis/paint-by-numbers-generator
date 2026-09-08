# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.application.parallel_image_quantizer import (
    ParallelImageQuantizer,
)
from pbn.application.quantization_executor_port import (
    COLOR_BYTES,
    QuantizationChunk,
    QuantizationChunkResult,
)
from pbn.color import DeltaE76, ImageQuantizer
from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
)


def create_palette(
    color_count: int,
) -> Palette:
    colors = tuple(
        PaletteColor(
            number=index + 1,
            name=f"Color {index + 1}",
            rgb=RGB(
                red=index,
                green=index,
                blue=index,
            ),
            lab=Lab(
                l=0.0,
                a=0.0,
                b=0.0,
            ),
        )
        for index in range(
            color_count,
        )
    )

    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=colors,
    )


def create_image(
    unique_color_count: int,
) -> InputImage:
    colors = tuple(
        RGB(
            red=index & 0xFF,
            green=(index >> 8) & 0xFF,
            blue=(index >> 16) & 0xFF,
        )
        for index in range(
            unique_color_count,
        )
    )

    return InputImage.from_rows((colors,))


def test_parallel_quantizer_uses_sequential_path_below_break_even_workload() -> None:
    image = create_image(
        4,
    )
    palette = create_palette(
        3,
    )

    executor_called = False

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            nonlocal executor_called
            executor_called = True

            return ()

    color_distance = DeltaE76()

    quantizer = ParallelImageQuantizer(
        color_distance=color_distance,
        executor=FakeExecutor(),
        worker_count=2,
        break_even_workload=16,
    )

    result = quantizer.quantize(
        image,
        palette,
    )

    expected = ImageQuantizer(
        color_distance=color_distance,
    ).quantize(
        image,
        palette,
    )

    assert result == expected
    assert executor_called is False


def test_parallel_quantizer_uses_executor_at_break_even_workload() -> None:
    image = create_image(
        4,
    )
    palette = create_palette(
        4,
    )
    executor_called = False

    class FakeExecutor:
        def quantize_chunks(
            self,
            chunks: tuple[
                QuantizationChunk,
                ...,
            ],
            palette: Palette,
            color_distance: ColorDistance,
        ) -> tuple[
            QuantizationChunkResult,
            ...,
        ]:
            nonlocal executor_called
            executor_called = True

            return tuple(
                (
                    chunk_index,
                    bytes(
                        len(packed_colors) // COLOR_BYTES,
                    ),
                )
                for chunk_index, packed_colors in chunks
            )

    quantizer = ParallelImageQuantizer(
        color_distance=DeltaE76(),
        executor=FakeExecutor(),
        worker_count=2,
        break_even_workload=16,
    )

    quantizer.quantize(
        image,
        palette,
    )

    assert executor_called is True
