# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
What crosses the process boundary, and how many processes it crosses to.

`multiprocessing` pickles what it sends. Two properties therefore matter
and neither is visible in an import list, which is as far as the
mechanical checks in `test_preserved_invariants.py` reach.

The first is that nothing attacker-shaped is pickled. An image supplies
values, not types: the numbers inside an `RGB` come from the input, the
`RGB` does not. Unpickling reconstructs types this project named, and a
document that could choose the type would be a different exposure
entirely.

The second is that the number of worker processes has an upper bound
that does not come from the input. It does not, but the exact claim in
the roadmap, that the count never derives from input data, is not the
one that holds. See the test that says so.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass

import pytest

from pbn.application.parallel_image_quantizer import (
    ParallelImageQuantizer,
)
from pbn.application.quantization_executor_port import (
    COLOR_BYTES,
    QuantizationChunk,
    QuantizationChunkResult,
)
from pbn.color.color_distance import ColorDistance
from pbn.color.delta_e_2000 import DeltaE2000
from pbn.models import (
    RGB,
    InputImage,
    Lab,
    Palette,
    PaletteColor,
)

ALLOWED_TYPES: tuple[type, ...] = (
    bool,
    bytes,
    float,
    int,
    str,
    type(None),
    tuple,
    RGB,
    Lab,
    Palette,
    PaletteColor,
    DeltaE2000,
)
"""
Every type permitted to cross the boundary.

Plain values, and the project's own frozen models. A type not named here
crossing the boundary is the thing this module exists to catch, whether
it arrives as a dictionary, a callable, or a class from a dependency.

`RGB`, `Lab` and `PaletteColor` remain listed although ADR-0014 took the
colors out of the chunks and the results: the palette still crosses, and
it is made of them.
"""


def offending_types(
    value: object,
    seen: set[int] | None = None,
) -> list[str]:
    """
    Return the names of types in `value` that may not be pickled here.

    Walks tuples and the fields of the project's frozen models, because
    a permitted container holding a forbidden object is exactly the
    shape a check on the top level would miss.
    """
    seen = set() if seen is None else seen

    if id(value) in seen:
        return []

    seen.add(
        id(value),
    )

    if not isinstance(
        value,
        ALLOWED_TYPES,
    ):
        return [
            type(value).__name__,
        ]

    offenders: list[str] = []

    if isinstance(
        value,
        tuple,
    ):
        for item in value:
            offenders += offending_types(
                item,
                seen,
            )

        return offenders

    for field in getattr(
        type(value),
        "__slots__",
        (),
    ):
        offenders += offending_types(
            getattr(
                value,
                field,
            ),
            seen,
        )

    # A permitted type without `__slots__` carries its state in a
    # dictionary, and that state is pickled with it. The strategy object
    # is empty today; a later one holding something is the case this
    # covers.
    for attribute in (
        vars(
            value,
        ).values()
        if hasattr(
            value,
            "__dict__",
        )
        else ()
    ):
        offenders += offending_types(
            attribute,
            seen,
        )

    return offenders


@dataclass
class RecordingExecutor:
    """
    Stands in for the process pool and records what it was handed.
    """

    calls: list[
        tuple[
            tuple[QuantizationChunk, ...],
            Palette,
            ColorDistance,
        ]
    ]

    def quantize_chunks(
        self,
        chunks: tuple[QuantizationChunk, ...],
        palette: Palette,
        color_distance: ColorDistance,
    ) -> tuple[QuantizationChunkResult, ...]:
        self.calls.append(
            (
                chunks,
                palette,
                color_distance,
            ),
        )

        return tuple(
            (
                index,
                bytes(
                    len(packed_colors) // COLOR_BYTES,
                ),
            )
            for index, packed_colors in chunks
        )


def create_palette() -> Palette:
    return Palette(
        id="test",
        version=1,
        manufacturer="Test",
        display_name="Test",
        colors=tuple(
            PaletteColor(
                number=index + 1,
                name=f"Color {index}",
                rgb=RGB(
                    red=index * 30 % 256,
                    green=index * 50 % 256,
                    blue=index * 70 % 256,
                ),
                lab=Lab(
                    l=float(index),
                    a=0.0,
                    b=0.0,
                ),
            )
            for index in range(8)
        ),
    )


def create_image(
    unique_colors: int,
) -> InputImage:
    """
    An image whose pixels take exactly `unique_colors` distinct values.
    """
    pixels = bytearray()

    for index in range(unique_colors):
        pixels += bytes(
            (
                index % 256,
                (index * 7) % 256,
                (index * 13) % 256,
            ),
        )

    return InputImage(
        width=unique_colors,
        height=1,
        pixels=bytes(
            pixels,
        ),
    )


def quantize_with(
    unique_colors: int,
    worker_count: int,
) -> RecordingExecutor:
    executor = RecordingExecutor(
        calls=[],
    )

    ParallelImageQuantizer(
        color_distance=DeltaE2000(),
        executor=executor,
        worker_count=worker_count,
        break_even_workload=1,
    ).quantize(
        create_image(
            unique_colors,
        ),
        create_palette(),
    )

    return executor


def test_only_named_types_cross_the_boundary() -> None:
    """
    An image supplies values, not types.

    Asserted on what the executor is actually handed, not on the type
    annotations of the port, because an annotation is not what gets
    pickled.
    """
    executor = quantize_with(
        unique_colors=32,
        worker_count=4,
    )

    assert executor.calls

    for chunks, palette, color_distance in executor.calls:
        assert (
            offending_types(
                chunks,
            )
            == []
        )
        assert (
            offending_types(
                palette,
            )
            == []
        )
        assert (
            offending_types(
                color_distance,
            )
            == []
        )


def test_everything_crossing_the_boundary_survives_a_round_trip() -> None:
    """
    The boundary is a pickle, so it has to be one.

    A type that cannot be pickled fails at the boundary rather than in a
    test, and only under the configuration that enables parallel
    quantization.
    """
    executor = quantize_with(
        unique_colors=32,
        worker_count=4,
    )

    for payload in executor.calls[0]:
        assert (
            pickle.loads(
                pickle.dumps(
                    payload,
                ),
            )
            is not None
        )


def test_the_type_check_rejects_a_foreign_object() -> None:
    """
    Without this, the two tests above would pass on an empty allowlist
    check that never rejects anything.
    """
    assert offending_types(
        (
            1,
            RGB(
                red=1,
                green=2,
                blue=3,
            ),
            {"a": 1},
        ),
    ) == [
        "dict",
    ]


@pytest.mark.parametrize(
    "unique_colors",
    (
        2,
        3,
        17,
        64,
        255,
    ),
)
def test_the_worker_count_never_exceeds_the_configured_bound(
    unique_colors: int,
) -> None:
    """
    The bound comes from configuration and the CPU count.

    One chunk becomes one worker process in the executor, so the number
    of chunks is the number of processes and is what has to be bounded.
    """
    worker_count = 4

    executor = quantize_with(
        unique_colors=unique_colors,
        worker_count=worker_count,
    )

    for chunks, _, _ in executor.calls:
        assert len(chunks) <= worker_count


def test_input_lowers_the_worker_count_and_cannot_raise_it() -> None:
    """
    The roadmap item says the count never derives from input data. It
    does, and only downward.

    `min(worker_count, len(unique_colors))` is the derivation. Splitting
    eight colors across sixteen processes would produce empty chunks, so
    the input does decide, within a ceiling it cannot move. Recorded as
    the property that holds rather than ticked as the one that does not.
    """
    few = quantize_with(
        unique_colors=3,
        worker_count=16,
    )

    assert [len(chunks) for chunks, _, _ in few.calls] == [
        3,
    ]

    many = quantize_with(
        unique_colors=255,
        worker_count=16,
    )

    assert [len(chunks) for chunks, _, _ in many.calls] == [
        16,
    ]
