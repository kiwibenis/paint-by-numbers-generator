# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The bounds `palette-format.md` states are the bounds the loader enforces.

That document claims to define the storage format completely, and
`palette-authoring-guide.md` points at it for mechanical bounds instead of
maintaining a second copy. The claim is worth making only if it stays true,
and a number in prose has no way of noticing that the constant beside it
changed.

The two documents had drifted the other way first: the guide carried its own
copy of the schema and of every bound while opening the section with "the
complete authoritative schema is documented in `palette-format.md`". Neither
copy was wrong at the time. Both were free to stop being right.

Each row of the bounds table is matched by its label, so a row that is renamed
or removed fails rather than passing silently.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pbn.infrastructure.palette_document import (
    MAXIMUM_COLOR_COUNT,
    MAXIMUM_PALETTE_DOCUMENT_BYTES,
    MAXIMUM_TEXT_LENGTH,
)
from pbn.infrastructure.palette_file_name import (
    MAXIMUM_PALETTE_VERSION,
    MINIMUM_PALETTE_VERSION,
    PALETTE_ID_PATTERN,
)
from tests.test_palette_text_is_renderable import accepted_characters

FORMAT_DOCUMENT = Path("docs/palette-format.md")

AUTHORING_DOCUMENT = Path("docs/palette-authoring-guide.md")

READERS_DOCUMENT = Path("README.md")
"""
The document a reader meets first, which describes the format loosely
on purpose. It may say that a palette holds up to a certain number of
colors, because that is orientation a caller can act on. What it may not
do is carry a bound that means nothing without the reason beside it.
"""

ORIENTATION_VALUES = frozenset(
    {
        MAXIMUM_COLOR_COUNT,
    },
)
"""
Bounds the README may state.

`256` answers a question a caller asks before writing anything: how big
may my palette be. The renderable-character count answers nothing on its
own, because the number only means something together with the encoding
and the renderer it comes from, both of which the format document holds.
"""

ROW_PATTERN = re.compile(
    r"^\| ([^|]+?) \| ([^|]+?) \|$",
    re.MULTILINE,
)

CODE_SPAN_PATTERN = re.compile(
    r"`[^`]*`",
)


def identifier_length_bounds() -> tuple[int, int]:
    """
    Return the identifier length the pattern accepts.
    """
    match = re.search(
        r"\{(\d+),(\d+)\}",
        PALETTE_ID_PATTERN.pattern,
    )

    assert match is not None, PALETTE_ID_PATTERN.pattern

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


def documented_bounds() -> dict[str, tuple[int, ...]]:
    """
    Return the numbers each bound row states, by row label.

    Thousands separators are removed so the document can stay readable
    while the comparison stays exact.

    Code spans are removed first. A span in a value cell is a literal the
    format accepts rather than a bound on it, and the identifier row lists
    `0-9` among the characters it permits.
    """
    found: dict[str, tuple[int, ...]] = {}

    for label, value in ROW_PATTERN.findall(
        FORMAT_DOCUMENT.read_text(
            encoding="utf-8",
        ),
    ):
        numbers = tuple(
            int(
                number.replace(
                    ",",
                    "",
                ),
            )
            for number in re.findall(
                r"\d[\d,]*",
                CODE_SPAN_PATTERN.sub(
                    "",
                    value,
                ),
            )
        )

        if numbers:
            found[label.strip()] = numbers

    return found


def expected_bounds() -> dict[str, tuple[int, ...]]:
    """
    Return the same numbers, taken from what enforces them.
    """
    minimum_identifier, maximum_identifier = identifier_length_bounds()

    return {
        "Document size": (MAXIMUM_PALETTE_DOCUMENT_BYTES,),
        "Colors per palette": (
            1,
            MAXIMUM_COLOR_COUNT,
        ),
        "Text field length": (
            1,
            MAXIMUM_TEXT_LENGTH,
        ),
        "Renderable characters": (
            len(
                accepted_characters(),
            ),
        ),
        "Color number": (1,),
        "RGB channel": (
            0,
            255,
        ),
        "Identifier": (
            minimum_identifier,
            maximum_identifier,
        ),
        "Version": (
            MINIMUM_PALETTE_VERSION,
            MAXIMUM_PALETTE_VERSION,
        ),
    }


def numeric_range_pattern(
    minimum: int,
    maximum: int,
) -> re.Pattern[str]:
    """
    Match a prose restatement of one numeric range.

    Backticks are optional because Markdown prose may write either
    `0` through `255` or 0 through 255. The common textual and dash
    separators are accepted so changing prose style cannot hide the
    duplicated rule.
    """
    return re.compile(
        (
            rf"(?:"
            rf"`?{minimum}`?\s*(?:to|through|[-–—])\s*`?{maximum}`?"
            rf"|"
            rf"between\s+`?{minimum}`?\s+and\s+`?{maximum}`?"
            rf")"
        ),
        re.IGNORECASE,
    )


@pytest.mark.parametrize(
    "label",
    tuple(
        expected_bounds(),
    ),
)
def test_the_documented_bound_is_the_enforced_one(
    label: str,
) -> None:
    documented = documented_bounds()

    assert label in documented, (
        f"{FORMAT_DOCUMENT} no longer states a bound for {label!r}; "
        "the table is the one place this rule is written down"
    )

    assert documented[label] == expected_bounds()[label], (
        f"{FORMAT_DOCUMENT} states {documented[label]} for {label!r}, "
        f"the code enforces {expected_bounds()[label]}"
    )


def test_every_bound_row_is_accounted_for() -> None:
    """
    The direction the check above cannot see: a row added to the table
    that nothing compares against.
    """
    table = FORMAT_DOCUMENT.read_text(
        encoding="utf-8",
    ).split(
        "## Bounds",
    )[1]

    labels = {
        label.strip()
        for label, value in ROW_PATTERN.findall(
            table.split(
                "\n\n`true`",
            )[0],
        )
        if re.search(r"\d", value)
    }

    assert labels == set(
        expected_bounds(),
    )


def test_the_authoring_guide_does_not_repeat_distinctive_bound_values() -> None:
    """
    Preserve the existing protection for values distinctive enough to search
    globally without confusing ordinary authoring examples for bounds.
    """
    text = AUTHORING_DOCUMENT.read_text(
        encoding="utf-8",
    )

    for value in (
        f"{MAXIMUM_PALETTE_DOCUMENT_BYTES:,}",
        str(
            MAXIMUM_PALETTE_DOCUMENT_BYTES,
        ),
        str(
            MAXIMUM_TEXT_LENGTH,
        ),
        str(
            MAXIMUM_PALETTE_VERSION,
        ),
    ):
        assert value not in text, (
            f"{AUTHORING_DOCUMENT} states {value}, which "
            f"{FORMAT_DOCUMENT} is authoritative for"
        )


@pytest.mark.parametrize(
    (
        "label",
        "minimum",
        "maximum",
    ),
    tuple(
        (
            label,
            values[0],
            values[1],
        )
        for label, values in expected_bounds().items()
        if len(values) == 2
    ),
)
def test_the_authoring_guide_does_not_restate_a_numeric_range(
    label: str,
    minimum: int,
    maximum: int,
) -> None:
    """
    Catch range bounds even when the guide phrases them differently.

    The old check could reject a repeated maximum such as `9999`, but it
    could not see the RGB rule written as `0` through `255`. Deriving these
    pairs from the same expected-bound map keeps the regression check tied to
    the format table instead of introducing another manually maintained list.
    """
    text = AUTHORING_DOCUMENT.read_text(
        encoding="utf-8",
    )

    match = numeric_range_pattern(
        minimum,
        maximum,
    ).search(
        text,
    )

    assert match is None, (
        f"{AUTHORING_DOCUMENT} restates the {label!r} range as "
        f"{match.group(0)!r}; {FORMAT_DOCUMENT} is authoritative for it"
    )


def test_the_authoring_guide_points_at_the_format_document() -> None:
    """
    Removing a restatement is only half of it. A reader has to be told
    where the rule went.
    """
    assert (
        AUTHORING_DOCUMENT.read_text(
            encoding="utf-8",
        ).count(
            "palette-format.md",
        )
        >= 5
    )


def test_the_documented_character_set_is_the_accepted_one() -> None:
    """
    The identifier row lists characters rather than bounding a number, so
    the check above cannot see it.

    Compared against what the pattern accepts one character at a time,
    rather than against the pattern text, so a rewritten but equivalent
    pattern passes and a narrowed one does not.
    """
    accepted = {
        chr(code_point)
        for code_point in range(0x2200)
        if PALETTE_ID_PATTERN.fullmatch(
            chr(code_point),
        )
    }

    documented: set[str] = set()

    for label, value in ROW_PATTERN.findall(
        FORMAT_DOCUMENT.read_text(
            encoding="utf-8",
        ),
    ):
        if label.strip() != "Identifier":
            continue

        for span in CODE_SPAN_PATTERN.findall(
            value,
        ):
            literal = span.strip(
                "`",
            )

            if len(literal) == 3 and literal[1] == "-":
                documented |= {
                    chr(code_point)
                    for code_point in range(
                        ord(literal[0]),
                        ord(literal[2]) + 1,
                    )
                }
            else:
                documented.add(
                    literal,
                )

    assert documented, f"{FORMAT_DOCUMENT} has no identifier row to read"

    assert documented == accepted


def test_the_readme_states_no_bound_it_does_not_explain() -> None:
    """
    The README described the format loosely and stated two of its bounds.

    `256` stays, as orientation a caller can act on. The renderable-character
    count is gone from it: the number without the encoding and the renderer
    beside it tells a reader nothing, and it was the second place that number
    lived.
    """
    text = READERS_DOCUMENT.read_text(
        encoding="utf-8",
    )

    for label, values in expected_bounds().items():
        for value in values:
            if value in ORIENTATION_VALUES or value in (0, 1):
                continue

            assert not re.search(
                rf"(?<!\d){value}(?!\d)",
                text,
            ), (
                f"{READERS_DOCUMENT} states {value} for {label!r}, which "
                f"{FORMAT_DOCUMENT} is authoritative for"
            )


def test_the_readme_points_at_the_format_document() -> None:
    """
    Removing the number is only half of it. A reader has to be told where
    the complete rule lives, or the README reads as the whole story.
    """
    assert "palette-format.md" in READERS_DOCUMENT.read_text(
        encoding="utf-8",
    )
