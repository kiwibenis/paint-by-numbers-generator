# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
A loader that returns a prepared image without touching the file system.

Generation reaches its input only through the loader port, so tests that
exercise generation supply one rather than an already-loaded image.
"""

from __future__ import annotations

from pathlib import Path

from pbn.core.image_input_rules import ImageInputLimits
from pbn.models import InputImage


class FakeImageLoader:
    """
    Returns a fixed image and records what it was asked for.
    """

    def __init__(
        self,
        image: InputImage,
    ) -> None:
        self._image = image
        self.requested_paths: list[Path] = []
        self.requested_limits: list[ImageInputLimits] = []

    def load(
        self,
        image_path: Path,
        limits: ImageInputLimits,
    ) -> InputImage:
        self.requested_paths.append(
            image_path,
        )
        self.requested_limits.append(
            limits,
        )

        return self._image


def loader_class_for(
    load_function: object,
) -> type:
    """
    Wrap a plain load function as a loader the port accepts.

    Command-line tests replace loading with a function. The application
    reaches its input through a loader object, so the function is wrapped
    rather than the tests being rewritten around it.
    """

    class _FunctionImageLoader:
        def load(
            self,
            image_path: Path,
            limits: ImageInputLimits,
        ) -> object:
            return load_function(  # type: ignore[operator]
                image_path,
                limits,
            )

    return _FunctionImageLoader
