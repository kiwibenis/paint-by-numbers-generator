# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from dataclasses import FrozenInstanceError

import pytest

from pbn.models import Label, Outline, VectorDocument


def test_vector_document_allows_missing_palette_metadata() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(),
    )

    assert document.palette_id is None
    assert document.palette_version is None


def test_vector_document_rejects_incomplete_palette_metadata() -> None:
    with pytest.raises(ValueError):
        VectorDocument(
            outlines=(),
            labels=(),
            palette_id="test",
        )

    with pytest.raises(ValueError):
        VectorDocument(
            outlines=(),
            labels=(),
            palette_version=1,
        )


def test_vector_document_stores_outlines_and_labels() -> None:
    outline = Outline(
        region_id=1,
        points=(
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ),
    )

    label = Label(
        region_id=1,
        text="1",
        position=(
            5.0,
            5.0,
        ),
    )

    document = VectorDocument(
        outlines=(outline,),
        labels=(label,),
        palette_id="test",
        palette_version=1,
    )

    assert document.outlines == (outline,)
    assert document.labels == (label,)
    assert document.palette_id == "test"
    assert document.palette_version == 1


def test_vector_document_is_immutable() -> None:
    document = VectorDocument(
        outlines=(),
        labels=(),
    )

    with pytest.raises(FrozenInstanceError):
        document.palette_id = "test"  # type: ignore[misc]
