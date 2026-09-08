# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The one place that decides what a palette file is called.

The rule existed in three places at two strictness levels. `PaletteManager.get`
validated an identifier against a character set and a version range and then
built a file name from it. `PaletteManager.available_palettes` and
`PaletteLoader._parse_filename` took a file name apart with a `-v` split, an
`int()` and a check that the identifier was not empty.

A catalogue built with the loose rule therefore advertised palettes the strict
rule refuses. Measured, five distinct routes reached that state: an identifier
holding a character outside the set, an identifier longer than the limit, a
version above the range, and two that `int()` accepts while the file name does
not survive being rebuilt, because `int("01")` is `1` and `int("1_0")` is `10`.

Parsing and formatting are inverses here, which is what closes the last two:
a name is accepted only if formatting the identity it yields reproduces that
same name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PALETTE_ID_PATTERN = re.compile(
    r"[A-Za-z0-9]{1,64}",
)
"""
Characters an identifier may hold, and how many.

Restricted because the identifier reaches a file system path. A separate
containment check still verifies the resolved path, because a character set
is not a containment control on its own.
"""

MINIMUM_PALETTE_VERSION = 1
MAXIMUM_PALETTE_VERSION = 9999

VERSION_SEPARATOR = "-v"

FILE_SUFFIX = ".json"


@dataclass(frozen=True, slots=True)
class PaletteIdentity:
    """
    The pair that names one palette, per ADR-0007.
    """

    palette_id: str
    version: int


def is_valid_identity(
    identity: PaletteIdentity,
) -> bool:
    """
    Return whether this pair may name a palette at all.

    `bool` is excluded explicitly. It is an `int` in Python, and `True`
    would otherwise pass as version one.
    """
    if isinstance(identity.version, bool) or not isinstance(
        identity.version,
        int,
    ):
        return False

    if not isinstance(identity.palette_id, str):
        return False

    if not PALETTE_ID_PATTERN.fullmatch(
        identity.palette_id,
    ):
        return False

    return MINIMUM_PALETTE_VERSION <= identity.version <= MAXIMUM_PALETTE_VERSION


def palette_file_name(
    identity: PaletteIdentity,
) -> str:
    """
    Return the file name this identity is stored under.

    Defined for a valid identity. A caller holding an invalid one has
    nothing to look for, and `is_valid_identity` answers that first.
    """
    return (
        f"{identity.palette_id}"
        f"{VERSION_SEPARATOR}"
        f"{identity.version}"
        f"{FILE_SUFFIX}"
    )


def parse_palette_file_name(
    file_name: str,
) -> PaletteIdentity | None:
    """
    Return the identity a file name denotes, or `None` if it denotes none.

    `None` rather than an exception, because the two callers want opposite
    things from an unrecognised name: the catalogue skips it, the loader
    rejects the document. Neither wants to phrase the other's failure.
    """
    if not file_name.endswith(
        FILE_SUFFIX,
    ):
        return None

    stem = file_name[: -len(FILE_SUFFIX)]

    palette_id, separator, version_text = stem.rpartition(
        VERSION_SEPARATOR,
    )

    if not separator:
        return None

    # `int` accepts a sign, surrounding whitespace, underscore separators
    # and non-ASCII digits, none of which a file name written by this
    # module can contain.
    if not version_text.isascii() or not version_text.isdigit():
        return None

    identity = PaletteIdentity(
        palette_id=palette_id,
        version=int(
            version_text,
        ),
    )

    if not is_valid_identity(
        identity,
    ):
        return None

    if (
        palette_file_name(
            identity,
        )
        != file_name
    ):
        # A leading zero parses and then names a different file.
        return None

    return identity
