# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
A JPEG the library reports as `MPO`, and what of it is used.

Phones attach auxiliary frames to an ordinary JPEG through an MPF index:
a depth map on one, a gain map on another. The file keeps its `.jpg`
name and its JPEG magic bytes, but Pillow's JPEG factory reclasses the
opened image to `MPO` when it finds the index, and the detected-format
check refused it on that ground alone.

That refusal turned away a large share of camera output for a property
that does not describe the picture. This module covers the narrow
exception that replaces it, and, more importantly, its edges: what still
has to be refused, and that nothing but frame zero is ever read.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pbn.config import ImageInputLimitsConfig
from pbn.exceptions import ImageTooLargeError, UnsupportedImageFormatError
from pbn.infrastructure.image_decoder_policy import reachable_image_decoders
from pbn.infrastructure.image_loader import ImageLoader
from tests.image_limits import TEST_IMAGE_INPUT_LIMITS

MP_ENTRY_TAG = 0xB002


def limits(
    **overrides: object,
) -> ImageInputLimitsConfig:
    return replace(
        TEST_IMAGE_INPUT_LIMITS,
        # A keyword mapping cannot be matched against the field types of
        # the dataclass, so the check is deferred to replace itself,
        # which raises TypeError on an unknown field.
        **overrides,  # type: ignore[arg-type]
    )


def structured_image(
    width: int,
    height: int,
    seed: int,
) -> Image.Image:
    """
    An image whose pixels differ, so that a mixed-up frame would show.
    """
    return Image.fromarray(
        np.random.default_rng(
            seed,
        ).integers(
            0,
            256,
            size=(height, width, 3),
            dtype=np.uint8,
        ),
    )


def write_jpeg_with_auxiliary_frame(
    path: Path,
    primary: Image.Image,
    auxiliary: Image.Image,
) -> Path:
    """
    Write a JPEG carrying one auxiliary frame behind an MPF index.

    Constructed rather than shipped as a fixture. The structure a phone
    produces is reproduced exactly, and the test says what it is instead
    of a binary file implying it.
    """
    primary.save(
        path,
        format="MPO",
        save_all=True,
        append_images=[
            auxiliary,
        ],
    )

    return path


def test_the_constructed_file_has_the_structure_under_test(
    tmp_path: Path,
) -> None:
    """
    A guard on every test below, which would otherwise pass on a plain
    JPEG that never exercised the exception at all.
    """
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.jpg",
        structured_image(80, 120, seed=1),
        structured_image(40, 60, seed=2),
    )

    with Image.open(
        path,
    ) as image:
        assert image.format == "MPO"

        # Reached the way the loader reaches them. Both attributes exist
        # on the multi-picture image class only, and Image.open is
        # declared as returning the base class.
        assert (
            getattr(
                image,
                "n_frames",
                None,
            )
            == 2
        )

        mpinfo = getattr(
            image,
            "mpinfo",
            None,
        )

        assert mpinfo is not None

        primary = mpinfo[MP_ENTRY_TAG][0]["Attribute"]

        assert primary["ImageDataFormat"] == "JPEG"
        assert primary["MPType"] == "Baseline MP Primary Image"


def test_the_multi_picture_decoder_stays_out_of_the_registry() -> None:
    """
    The exception rests on this.

    `MPO` is reached only through the JPEG factory, which runs after the
    extension has already been checked. Were the decoder registered, a
    file of any accepted name could be sniffed into it, and accepting
    `MPO` would widen far more than a JPEG with auxiliary frames.
    """
    assert "MPO" not in reachable_image_decoders()


def test_a_jpeg_with_auxiliary_frames_is_accepted(
    tmp_path: Path,
) -> None:
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.jpg",
        structured_image(80, 120, seed=1),
        structured_image(40, 60, seed=2),
    )

    image = ImageLoader().load(
        path,
        limits(),
    )

    assert (image.width, image.height) == (80, 120)


def frame_pixels(
    path: Path,
    frame: int,
) -> bytes:
    """
    Return one frame's pixels, decoded from the same encoded bytes.

    Compared against a separately written JPEG the two would differ on
    encoding parameters rather than on content, which would say nothing
    about which frame was read.
    """
    with Image.open(
        path,
    ) as image:
        image.seek(
            frame,
        )

        return image.convert(
            "RGB",
        ).tobytes()


def test_only_the_primary_frame_is_normalized(
    tmp_path: Path,
) -> None:
    """
    The assertion the exception stands or falls on.

    Both frames are the same size here and differ only in content, so
    matching one of them is a statement about which was read and not
    about which happened to fit.
    """
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.jpg",
        structured_image(80, 120, seed=1),
        structured_image(80, 120, seed=2),
    )

    loaded = ImageLoader().load(
        path,
        limits(),
    )

    assert loaded.pixels == frame_pixels(
        path,
        0,
    )
    assert loaded.pixels != frame_pixels(
        path,
        1,
    )


def test_the_limits_are_applied_to_the_primary_frame(
    tmp_path: Path,
) -> None:
    """
    The auxiliary frame is smaller, so a bound read from it would let an
    oversized primary through.
    """
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.jpg",
        structured_image(80, 120, seed=1),
        structured_image(8, 12, seed=2),
    )

    with pytest.raises(
        ImageTooLargeError,
    ):
        ImageLoader().load(
            path,
            limits(
                maximum_width=64,
                maximum_height=64,
                maximum_pixel_count=4096,
                processing_pixel_count=4096,
            ),
        )


def test_auxiliary_frames_behind_another_extension_are_rejected(
    tmp_path: Path,
) -> None:
    """
    The exception is tied to the extension claiming JPEG.

    Without that, `MPO` would become acceptable content for every
    supported name, and the detected-format check would stop meaning
    what it says for three formats in order to relax one.
    """
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.png",
        structured_image(80, 120, seed=1),
        structured_image(40, 60, seed=2),
    )

    with pytest.raises(
        UnsupportedImageFormatError,
    ):
        ImageLoader().load(
            path,
            limits(),
        )


@pytest.mark.parametrize(
    "corrupt",
    (
        pytest.param(
            lambda index: {},
            id="index-absent",
        ),
        pytest.param(
            lambda index: {
                **index,
                MP_ENTRY_TAG: [],
            },
            id="no-entries",
        ),
        pytest.param(
            lambda index: {
                **index,
                MP_ENTRY_TAG: "not a list",
            },
            id="entries-not-a-list",
        ),
        pytest.param(
            lambda index: {
                **index,
                MP_ENTRY_TAG: [
                    {},
                ],
            },
            id="entry-without-attributes",
        ),
        pytest.param(
            lambda index: {
                **index,
                MP_ENTRY_TAG: [
                    {
                        "Attribute": {
                            "ImageDataFormat": "Non JPEG",
                            "MPType": "Baseline MP Primary Image",
                        },
                    },
                ],
            },
            id="primary-is-not-jpeg",
        ),
        pytest.param(
            lambda index: {
                **index,
                MP_ENTRY_TAG: [
                    {
                        "Attribute": {
                            "ImageDataFormat": "JPEG",
                            "MPType": "Large Thumbnail (VGA Equivalent)",
                        },
                    },
                ],
            },
            id="first-entry-is-a-thumbnail",
        ),
        pytest.param(
            lambda index: {
                **index,
                MP_ENTRY_TAG: [
                    {
                        "Attribute": {
                            "ImageDataFormat": "JPEG",
                            "MPType": "Undefined",
                        },
                    },
                ],
            },
            id="first-entry-undefined",
        ),
    ),
)
def test_an_index_that_does_not_declare_a_jpeg_primary_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corrupt: object,
) -> None:
    """
    Every way the index can fail to say what the exception requires.

    The index is replaced after opening rather than crafted on disk,
    because the library will not write a malformed one and a hand-built
    file would be asserting against this module's idea of the format
    rather than against the library's reading of it.
    """
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.jpg",
        structured_image(80, 120, seed=1),
        structured_image(40, 60, seed=2),
    )

    original = Image.open

    def open_with_corrupted_index(
        *arguments: object,
        **keywords: object,
    ) -> Image.Image:
        image = original(
            *arguments,  # type: ignore[arg-type]
            **keywords,  # type: ignore[arg-type]
        )

        image.mpinfo = corrupt(  # type: ignore[attr-defined, operator]
            getattr(
                image,
                "mpinfo",
                {},
            ),
        )

        return image

    monkeypatch.setattr(
        Image,
        "open",
        open_with_corrupted_index,
    )

    with pytest.raises(
        UnsupportedImageFormatError,
    ):
        ImageLoader().load(
            path,
            limits(),
        )


def test_a_plain_jpeg_is_unaffected(
    tmp_path: Path,
) -> None:
    """
    The exception must not have become the rule.
    """
    path = tmp_path / "plain.jpg"

    structured_image(80, 120, seed=1).save(
        path,
        format="JPEG",
    )

    with Image.open(
        path,
    ) as image:
        assert image.format == "JPEG"

    loaded = ImageLoader().load(
        path,
        limits(),
    )

    assert (loaded.width, loaded.height) == (80, 120)


def test_content_of_another_supported_format_is_still_refused(
    tmp_path: Path,
) -> None:
    """
    A PNG behind a JPEG name is not made acceptable by any of this.

    A supported format on purpose. An unsupported one is unidentifiable
    rather than identified and refused, because its decoder is
    deregistered, so it would exercise a different rejection than the
    one this relaxes.
    """
    path = tmp_path / "actually_png.jpg"

    structured_image(8, 8, seed=3).save(
        path,
        format="PNG",
    )

    with pytest.raises(
        UnsupportedImageFormatError,
    ):
        ImageLoader().load(
            path,
            limits(),
        )


def test_the_stream_is_never_advanced_past_the_primary_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Asserted by making a seek fail rather than by reading the loader.

    A later change that iterated the frames would decode attacker
    content the limits were never applied to, and would do it silently.
    """
    path = write_jpeg_with_auxiliary_frame(
        tmp_path / "photo.jpg",
        structured_image(80, 120, seed=1),
        structured_image(40, 60, seed=2),
    )

    from PIL import MpoImagePlugin

    def refuse_seek(
        self: object,
        frame: int,
    ) -> None:
        raise AssertionError(
            f"the loader advanced to frame {frame}",
        )

    monkeypatch.setattr(
        MpoImagePlugin.MpoImageFile,
        "seek",
        refuse_seek,
    )

    assert ImageLoader().load(
        path,
        limits(),
    )
