# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from multiprocessing import get_context
from multiprocessing.context import BaseContext

import pytest

from pbn.color import DeltaE76
from pbn.infrastructure import process_quantization_executor
from pbn.infrastructure.process_quantization_executor import (
    ProcessQuantizationExecutor,
)
from pbn.models import (
    RGB,
    Lab,
    Palette,
    PaletteColor,
)


def create_palette() -> Palette:
    black_rgb = RGB(
        red=0,
        green=0,
        blue=0,
    )

    white_rgb = RGB(
        red=255,
        green=255,
        blue=255,
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

    white = PaletteColor(
        number=2,
        name="White",
        rgb=white_rgb,
        lab=Lab(
            l=100.0,
            a=0.0,
            b=0.0,
        ),
    )

    return Palette(
        id="test",
        manufacturer="Test",
        display_name="Test",
        version=1,
        colors=(
            black,
            white,
        ),
    )


def test_quantize_chunks_executes_palette_matching_in_spawn_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    palette = create_palette()

    black_rgb = palette.colors[0].rgb
    white_rgb = palette.colors[1].rgb

    requested_contexts: list[str] = []

    # Taken from multiprocessing rather than read back off the module
    # under test, which imported the name and does not re-export it.
    # The patch below still has to target the module, because that is
    # where the call resolves.
    real_get_context = get_context

    def recording_get_context(
        method: str,
    ) -> BaseContext:
        requested_contexts.append(
            method,
        )

        return real_get_context(
            method,
        )

    monkeypatch.setattr(
        process_quantization_executor,
        "get_context",
        recording_get_context,
    )

    executor = ProcessQuantizationExecutor()

    result = executor.quantize_chunks(
        (
            (
                0,
                bytes(
                    (
                        black_rgb.red,
                        black_rgb.green,
                        black_rgb.blue,
                    ),
                ),
            ),
            (
                1,
                bytes(
                    (
                        white_rgb.red,
                        white_rgb.green,
                        white_rgb.blue,
                    ),
                ),
            ),
        ),
        palette,
        DeltaE76(),
    )

    ordered_result = tuple(
        sorted(
            result,
            key=lambda chunk_result: (chunk_result[0]),
        ),
    )

    assert requested_contexts == [
        "spawn",
    ]

    # One palette index per color, addressing `palette.colors`.
    assert ordered_result == (
        (
            0,
            bytes(
                (0,),
            ),
        ),
        (
            1,
            bytes(
                (1,),
            ),
        ),
    )


def test_quantize_chunks_returns_empty_result_for_empty_work() -> None:
    executor = ProcessQuantizationExecutor()

    result = executor.quantize_chunks(
        (),
        create_palette(),
        DeltaE76(),
    )

    assert result == ()
