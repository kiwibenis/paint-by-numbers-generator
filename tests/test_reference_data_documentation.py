# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Every shipped palette is documented, and every document points at a file.

The README states that `docs/reference-data/` records which published source
each reference value came from. That was untrue for five of the six shipped
palettes: only the Polychromos 60 document existed, and it still named
`palettes/polychromos60-v1.json` after the file had been renamed to
`palettes/faberCastellPolychromos60-v1.json`.

Nothing could have caught either. The claim lived in prose and the link
between a palette and its document was a convention rather than a checked
relation. Both directions are checked here, because a document that names a
file that no longer exists is the same failure as a file that no document
names.

The link was not the only thing living in prose. `reference8.md` stated that
the palette had no manufacturer while `reference8-v1.json` declared
`Paint-by-Numbers Generator`, which `pbn palettes` prints with every listing.
The document went on to say that the numbers were therefore not manufacturer
numbers and that no manufacturer sold those colours, all of it following from
the first sentence being wrong. A document may explain a value, and this one
contradicted it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PALETTE_DIRECTORY = Path("palettes")

DOCUMENTATION_DIRECTORY = Path("docs/reference-data")

PALETTE_FILE_PATTERN = re.compile(
    r"palettes/([A-Za-z0-9]+-v\d+\.json)",
)
"""
A palette file as the documents write it.

Matched against the file name rather than a palette identifier, so a rename
that leaves the identifier alone is still caught.
"""


def palette_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            PALETTE_DIRECTORY.glob(
                "*.json",
            ),
        ),
    )


def documentation_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            DOCUMENTATION_DIRECTORY.glob(
                "*.md",
            ),
        ),
    )


def documented_palette_names() -> dict[str, list[str]]:
    """
    Return every palette file name a document names, by document.
    """
    documented: dict[str, list[str]] = {}

    for document in documentation_files():
        for name in PALETTE_FILE_PATTERN.findall(
            document.read_text(
                encoding="utf-8",
            ),
        ):
            documented.setdefault(
                name,
                [],
            ).append(
                document.name,
            )

    return documented


def test_the_repository_ships_palettes_and_documents() -> None:
    """
    Without this, an empty directory would satisfy both tests below.
    """
    assert palette_files()
    assert documentation_files()


@pytest.mark.parametrize(
    "palette_file",
    palette_files(),
    ids=lambda path: path.name,
)
def test_every_shipped_palette_is_documented(
    palette_file: Path,
) -> None:
    assert (
        palette_file.name in documented_palette_names()
    ), f"{palette_file.name} has no document in {DOCUMENTATION_DIRECTORY}"


@pytest.mark.parametrize(
    "document",
    documentation_files(),
    ids=lambda path: path.name,
)
def test_every_document_names_palette_files_that_exist(
    document: Path,
) -> None:
    """
    The direction that the stale path would have failed.
    """
    named = PALETTE_FILE_PATTERN.findall(
        document.read_text(
            encoding="utf-8",
        ),
    )

    assert named, f"{document.name} names no palette file"

    for name in named:
        assert (
            PALETTE_DIRECTORY / name
        ).exists(), f"{document.name} names a missing {name}"


COLOR_ROW_PATTERN = re.compile(
    r"^\| (\d+) \| ([^|]+?) \| (\d+), (\d+), (\d+) \| `(#[0-9A-Fa-f]{6})` \|$",
    re.MULTILINE,
)
"""
A colour row as a document writes it, if it writes one at all.

Only `reference8.md` prints its values in full, because eight of them fit.
The pattern is general so that a table added to another document is checked
on the day it is added rather than on the day someone remembers this file.
"""


def documenting_file(
    palette_file: Path,
) -> Path:
    """
    Return the document that names this palette file.
    """
    names = documented_palette_names()[palette_file.name]

    assert len(names) == 1, f"{palette_file.name} is named by {names}"

    return DOCUMENTATION_DIRECTORY / names[0]


@pytest.mark.parametrize(
    "palette_file",
    palette_files(),
    ids=lambda path: path.name,
)
def test_the_document_names_the_manufacturer_the_palette_declares(
    palette_file: Path,
) -> None:
    """
    The statement `reference8.md` got wrong, checked against the file.

    A document that describes provenance and disagrees with the data about
    who made it is worse than one that says nothing, because a reader has no
    reason to open the JSON.
    """
    manufacturer = json.loads(
        palette_file.read_text(
            encoding="utf-8",
        ),
    )[
        "metadata"
    ]["manufacturer"]

    document = documenting_file(
        palette_file,
    )

    assert manufacturer in document.read_text(
        encoding="utf-8",
    ), f"{document.name} does not name {manufacturer!r}"


@pytest.mark.parametrize(
    "palette_file",
    palette_files(),
    ids=lambda path: path.name,
)
def test_a_documented_colour_table_matches_the_palette(
    palette_file: Path,
) -> None:
    """
    A document that transcribes values has to keep matching them.

    A document that transcribes none passes without asserting anything,
    which `test_at_least_one_document_transcribes_its_colours` guards
    against being true of all of them at once.
    """
    document = documenting_file(
        palette_file,
    )

    rows = COLOR_ROW_PATTERN.findall(
        document.read_text(
            encoding="utf-8",
        ),
    )

    if not rows:
        return

    colors = json.loads(
        palette_file.read_text(
            encoding="utf-8",
        ),
    )["colors"]

    assert len(rows) == len(colors), (
        f"{document.name} transcribes {len(rows)} colours for "
        f"{palette_file.name}, which has {len(colors)}"
    )

    for row, color in zip(
        rows,
        colors,
    ):
        number, name, red, green, blue, hex_value = row

        rgb = color["rgb"]

        assert (
            int(number),
            name.strip(),
            int(red),
            int(green),
            int(blue),
            hex_value.upper(),
        ) == (
            color["number"],
            color["name"],
            rgb["red"],
            rgb["green"],
            rgb["blue"],
            "#{:02X}{:02X}{:02X}".format(
                rgb["red"],
                rgb["green"],
                rgb["blue"],
            ),
        ), f"{document.name} disagrees with {palette_file.name}"


def test_at_least_one_document_transcribes_its_colours() -> None:
    """
    Without this, a pattern that stopped matching would leave the check
    above returning early for every palette.
    """
    transcribing = [
        document.name
        for document in documentation_files()
        if COLOR_ROW_PATTERN.search(
            document.read_text(
                encoding="utf-8",
            ),
        )
    ]

    assert transcribing == ["reference8.md"]
