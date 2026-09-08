# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

from pbn.exceptions import (
    PaletteCatalogueError,
    PaletteError,
    PaletteNotFoundError,
)
from pbn.models import Palette

from .palette_file_name import (
    PaletteIdentity,
    is_valid_identity,
    palette_file_name,
    parse_palette_file_name,
)
from .palette_loader import PaletteLoader


class PaletteManager:
    """
    Central access point for palettes.
    """

    def __init__(self) -> None:
        self._directory = Path("palettes")
        self._loader = PaletteLoader()

    def available(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (
                palette.id,
                palette.version,
            )
            for palette in self.available_palettes()
        )

    def available_palettes(self) -> tuple[Palette, ...]:
        """
        Load every palette the directory offers.

        A caller selects an identifier, so something has to tell it
        which identifiers exist. Reading the directory itself would mean
        reproducing the file naming rule and the schema, and would
        report palettes that cannot in fact be loaded.

        A document that does not load is skipped rather than raised. An
        operator adding a broken palette should not make the ones
        already there unlistable, and the failure is theirs to see when
        they select it. Every palette failure counts as not loading: this
        caught only an invalid document, so one dangling symlink in the
        directory raised `PaletteNotFoundError` out of here and the
        catalogue reported nothing at all, which is the opposite of what
        the paragraph above says it does.

        A name alone does not make an entry selectable. `get` refuses a
        path that leaves the directory once resolved, so the catalogue
        has to refuse the same ones, or a symlink pointing outside is
        listed here and rejected there.

        A catalogue that cannot be read is raised rather than reported
        as empty. The directory is relative to the working directory, so
        an empty result would be what running from the wrong place looks
        like, and a caller would show an empty chooser instead of a
        failure. An existing but empty directory still reports nothing,
        which is the true statement that none are installed.

        `iterdir` rather than `glob`: measured, `glob` returns an empty
        result for a directory it may not read, which would have made
        the check below unreachable.
        """
        palettes: list[Palette] = []

        if not self._directory.is_dir():
            raise PaletteCatalogueError(
                f"No palette directory: {self._directory.resolve()}",
            )

        try:
            files = sorted(
                entry for entry in self._directory.iterdir() if entry.suffix == ".json"
            )
        except OSError as exc:
            raise PaletteCatalogueError(
                f"Could not read the palette directory: {self._directory}",
            ) from exc

        for file in files:
            if (
                parse_palette_file_name(
                    file.name,
                )
                is None
            ):
                # A name this does not recognise is a name `get` could
                # not have built, so listing it would offer a palette
                # that cannot be selected.
                continue

            if not self._is_inside_directory(
                file,
            ):
                continue

            try:
                palette = self._loader.load(
                    file,
                )
            except PaletteError:
                continue

            palettes.append(
                palette,
            )

        return tuple(
            sorted(
                palettes,
                key=lambda palette: (
                    palette.id,
                    palette.version,
                ),
            ),
        )

    def get(
        self,
        palette_id: str,
        version: int,
    ) -> Palette:
        """
        Load one palette by identifier and version.

        The identifier reaches a file system path, so it is validated
        against an explicit character set rather than merely against being
        empty. Path concatenation is not a containment control on its own,
        because an absolute component replaces the base directory, so the
        resolved path is verified to remain inside it afterwards.
        """
        identity = PaletteIdentity(
            palette_id=palette_id,
            version=version,
        )

        if not is_valid_identity(
            identity,
        ):
            raise PaletteNotFoundError(
                "Unknown palette.",
            )

        file = self._directory / palette_file_name(
            identity,
        )

        self._ensure_inside_directory(
            file,
        )

        try:
            return self._loader.load(
                file,
            )
        except PaletteError as exc:
            # One message for every rejection. A caller that can tell a
            # missing palette from an invalid one learns which files
            # exist, and the loader's message carries a file system path.
            # The original error stays available as the cause, so a log
            # can record what a response must not.
            raise PaletteNotFoundError(
                "Unknown palette.",
            ) from exc

    def _ensure_inside_directory(
        self,
        file: Path,
    ) -> None:
        if not self._is_inside_directory(
            file,
        ):
            raise PaletteNotFoundError(
                "Unknown palette.",
            )

    def _is_inside_directory(
        self,
        file: Path,
    ) -> bool:
        """
        Return whether the file is inside the palette directory once resolved.

        Resolved rather than compared as written, because path
        concatenation is not a containment control on its own: an absolute
        component replaces the base directory, and a symlink inside the
        directory can point anywhere.

        `resolve` raises for a file system it cannot follow, and `OSError`
        is not the only type it raises: a symlink loop reaches this as
        `RuntimeError`, which used to leave `get` through every `except`
        in the process and reach a caller as a traceback and exit code 1.
        An entry the file system cannot resolve is not inside the
        directory in any sense a caller can use.
        """
        try:
            resolved = file.resolve()
            directory = self._directory.resolve()
        except (
            OSError,
            RuntimeError,
        ):
            return False

        return resolved.is_relative_to(
            directory,
        )
