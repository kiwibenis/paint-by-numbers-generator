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
from pbn.color import DeltaE76, DeltaE2000, ImageQuantizer
from pbn.color.color_distance import ColorDistance
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
    QuantizedImage,
)


def create_palette() -> Palette:
    black_rgb = RGB(
        red=0,
        green=0,
        blue=0,
    )

    black = PaletteColor(
        number=1,
        name="Black",
        rgb=black_rgb,
        lab=Lab(
            l=0.0,
            a=0.0,
            b=0.0,
        ),
    )

    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(black,),
    )


def create_determinism_palette() -> Palette:
    return Palette(
        id="determinism",
        manufacturer="Test",
        display_name="Determinism",
        version=1,
        colors=(
            PaletteColor(
                number=1,
                name="Black",
                rgb=RGB(
                    red=0,
                    green=0,
                    blue=0,
                ),
                lab=Lab(
                    l=0.0,
                    a=0.0,
                    b=0.0,
                ),
            ),
            PaletteColor(
                number=2,
                name="Gray",
                rgb=RGB(
                    red=128,
                    green=128,
                    blue=128,
                ),
                lab=Lab(
                    l=53.6,
                    a=0.0,
                    b=0.0,
                ),
            ),
            PaletteColor(
                number=3,
                name="White",
                rgb=RGB(
                    red=255,
                    green=255,
                    blue=255,
                ),
                lab=Lab(
                    l=100.0,
                    a=0.0,
                    b=0.0,
                ),
            ),
        ),
    )


def create_unique_color_image() -> InputImage:
    colors = tuple(
        RGB(
            red=value,
            green=value,
            blue=value,
        )
        for value in (
            10,
            20,
            30,
            40,
            50,
        )
    )

    return InputImage.from_rows((colors,))


def create_determinism_image() -> InputImage:
    colors = tuple(
        RGB(
            red=value,
            green=value,
            blue=value,
        )
        for value in (
            0,
            16,
            64,
            96,
            128,
            160,
            224,
            255,
        )
    )

    return InputImage.from_rows(
        (
            (
                colors[0],
                colors[3],
                colors[6],
                colors[1],
            ),
            (
                colors[7],
                colors[4],
                colors[2],
                colors[5],
            ),
            (
                colors[3],
                colors[0],
                colors[7],
                colors[4],
            ),
        )
    )


def test_parallel_quantizer_submits_deterministic_chunks() -> None:
    image = create_unique_color_image()
    palette = create_palette()
    color_distance = DeltaE76()

    captured_chunks: list[tuple[QuantizationChunk, ...]] = []

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
            captured_chunks.append(
                chunks,
            )

            # Index 0, the first palette color, for every color.
            return tuple(
                (
                    index,
                    bytes(
                        len(packed_colors) // COLOR_BYTES,
                    ),
                )
                for index, packed_colors in chunks
            )

    quantizer = ParallelImageQuantizer(
        color_distance=color_distance,
        executor=FakeExecutor(),
        worker_count=2,
        break_even_workload=1,
    )

    quantizer.quantize(
        image,
        palette,
    )

    assert captured_chunks == [
        (
            (
                0,
                bytes(
                    (
                        10,
                        10,
                        10,
                        20,
                        20,
                        20,
                        30,
                        30,
                        30,
                    ),
                ),
            ),
            (
                1,
                bytes(
                    (
                        40,
                        40,
                        40,
                        50,
                        50,
                        50,
                    ),
                ),
            ),
        ),
    ]


def test_parallel_quantizer_reorders_chunk_results_deterministically() -> None:
    image = create_unique_color_image()
    palette = create_palette()
    black = palette.colors[0]

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
            results = tuple(
                (
                    index,
                    bytes(
                        len(packed_colors) // COLOR_BYTES,
                    ),
                )
                for index, packed_colors in chunks
            )

            return tuple(
                reversed(
                    results,
                ),
            )

    quantizer = ParallelImageQuantizer(
        color_distance=DeltaE76(),
        executor=FakeExecutor(),
        worker_count=2,
        break_even_workload=1,
    )

    result = quantizer.quantize(
        image,
        palette,
    )

    assert result == QuantizedImage.from_rows(
        (
            (
                black,
                black,
                black,
                black,
                black,
            ),
        )
    )


def test_parallel_quantizer_matches_sequential_result_across_worker_counts() -> None:
    image = create_determinism_image()
    palette = create_determinism_palette()
    color_distance = DeltaE2000()

    expected = ImageQuantizer(
        color_distance=color_distance,
    ).quantize(
        image,
        palette,
    )

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
            quantizer = ImageQuantizer(
                color_distance=color_distance,
            )

            results: list[QuantizationChunkResult] = []

            index_by_color = {
                color: index
                for index, color in enumerate(
                    palette.colors,
                )
            }

            for chunk_index, packed_colors in chunks:
                colors = tuple(
                    RGB(
                        packed_colors[offset],
                        packed_colors[offset + 1],
                        packed_colors[offset + 2],
                    )
                    for offset in range(
                        0,
                        len(packed_colors),
                        COLOR_BYTES,
                    )
                )

                chunk_image = InputImage.from_rows(
                    (colors,),
                )

                quantized_chunk = quantizer.quantize(
                    chunk_image,
                    palette,
                )

                results.append(
                    (
                        chunk_index,
                        bytes(
                            index_by_color[palette_color]
                            for palette_color in (quantized_chunk.rows_at(0))
                        ),
                    ),
                )

            return tuple(
                reversed(
                    results,
                ),
            )

    for worker_count in (
        2,
        3,
        4,
        8,
    ):
        quantizer = ParallelImageQuantizer(
            color_distance=color_distance,
            executor=FakeExecutor(),
            worker_count=worker_count,
            break_even_workload=1,
        )

        result = quantizer.quantize(
            image,
            palette,
        )

        assert result == expected


def test_parallel_quantizer_uses_sequential_path_for_single_worker() -> None:
    image = create_unique_color_image()
    palette = create_palette()
    color_distance = DeltaE76()

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

    quantizer = ParallelImageQuantizer(
        color_distance=color_distance,
        executor=FakeExecutor(),
        worker_count=1,
        break_even_workload=1,
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


def test_parallel_quantizer_rejects_non_positive_worker_count() -> None:
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
            return ()

    try:
        ParallelImageQuantizer(
            color_distance=DeltaE76(),
            executor=FakeExecutor(),
            worker_count=0,
            break_even_workload=1,
        )
    except ValueError as error:
        assert str(error) == ("worker_count must be greater than zero")
    else:
        raise AssertionError(
            "Expected ValueError for invalid worker count.",
        )
