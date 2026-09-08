# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

from pbn.exceptions import InvalidPaletteError
from pbn.infrastructure import (
    PaletteLoader,
    PaletteManager,
)


def test_list_palette_files() -> None:
    loader = PaletteLoader()

    valid_palettes: list[str] = []
    invalid_filenames: list[str] = []
    invalid_definitions: list[str] = []

    for file in sorted(
        Path("palettes").glob("*.json"),
    ):
        stem = file.stem

        if "-v" not in stem:
            invalid_filenames.append(
                file.name,
            )
            continue

        palette_id, version_text = stem.rsplit(
            "-v",
            1,
        )

        if not palette_id:
            invalid_filenames.append(
                file.name,
            )
            continue

        try:
            int(version_text)
        except ValueError:
            invalid_filenames.append(
                file.name,
            )
            continue

        try:
            loader.load(file)
        except InvalidPaletteError:
            invalid_definitions.append(
                file.name,
            )
            continue

        valid_palettes.append(
            file.name,
        )

    print()
    print("Valid palettes:")

    for filename in valid_palettes:
        print(f"  {filename}")

    print()
    print("Invalid palette filenames:")

    for filename in invalid_filenames:
        print(f"  {filename}")

    print()
    print("Invalid palette definitions:")

    for filename in invalid_definitions:
        print(f"  {filename}")


def test_find_all_palette_versions() -> None:
    manager = PaletteManager()

    available = manager.available()

    assert available == (
        ("amsterdamStandardRoyalTalents24", 1),
        ("amsterdamStandardRoyalTalents36", 1),
        ("amsterdamStandardRoyalTalents48", 1),
        ("amsterdamStandardRoyalTalents90", 1),
        ("faberCastellPolychromos120", 1),
        ("faberCastellPolychromos60", 1),
        ("reference8", 1),
    )


def test_get_multiple_palette_versions() -> None:
    manager = PaletteManager()

    polychromos = manager.get(
        palette_id="faberCastellPolychromos60",
        version=1,
    )

    reference = manager.get(
        palette_id="reference8",
        version=1,
    )

    assert polychromos.id == "faberCastellPolychromos60"
    assert polychromos.version == 1

    assert reference.id == "reference8"
    assert reference.version == 1


def test_get_palette_version() -> None:
    manager = PaletteManager()

    palette = manager.get(
        palette_id="faberCastellPolychromos60",
        version=1,
    )

    assert palette.id == "faberCastellPolychromos60"
    assert palette.version == 1


def test_get_faber_castell_polychromos120_palette_version() -> None:
    manager = PaletteManager()

    palette = manager.get(
        palette_id="faberCastellPolychromos120",
        version=1,
    )

    assert palette.id == "faberCastellPolychromos120"
    assert palette.version == 1


def test_get_amsterdam_standard_series_palette_versions() -> None:
    manager = PaletteManager()

    palette_ids = (
        "amsterdamStandardRoyalTalents24",
        "amsterdamStandardRoyalTalents36",
        "amsterdamStandardRoyalTalents48",
        "amsterdamStandardRoyalTalents90",
    )

    for palette_id in palette_ids:
        palette = manager.get(
            palette_id=palette_id,
            version=1,
        )

        assert palette.id == palette_id
        assert palette.manufacturer == "Royal Talens"
        assert palette.version == 1
