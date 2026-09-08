# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The configuration the README quotes is the configuration that ships.

The README introduces a block with "The current example configuration is:"
and then reproduces `config/example.toml`. It had fallen behind by an entire
section: `[input_limits]` was missing, with its four required values.

That is not a cosmetic drift. The project has no program-internal
configuration defaults, so a reader who copies the quoted block gets a file
that cannot generate anything. It fails with

    ConfigurationError: Missing required configuration values:
    maximum_input_pixel_count, maximum_input_width, maximum_input_height,
    processing_pixel_count

and the block is the first thing a new reader copies.

Compared verbatim rather than value by value, because the README presents the
block as the file rather than as a summary of it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.infrastructure.config_loader import load_config

README = Path("README.md")

CONFIGURATION = Path("config/example.toml")

ANCHOR = "The current example configuration is:\n\n"

INDENT = "    "


def quoted_configuration() -> str:
    """
    Return the indented block, with the indentation removed.

    The block ends at the first line that is neither indented nor empty,
    which is how a Markdown indented code block ends.
    """
    text = README.read_text(
        encoding="utf-8",
    )

    assert text.count(ANCHOR) == 1, "the README no longer introduces the block"

    remainder = text[text.index(ANCHOR) + len(ANCHOR) :]

    lines: list[str] = []

    for line in remainder.splitlines(
        keepends=True,
    ):
        if line.strip() and not line.startswith(INDENT):
            break

        lines.append(
            line.removeprefix(INDENT),
        )

    return "".join(
        lines,
    ).rstrip(
        "\n",
    )


def test_the_readme_quotes_the_shipped_configuration_verbatim() -> None:
    assert quoted_configuration() == CONFIGURATION.read_text(
        encoding="utf-8",
    ).rstrip(
        "\n",
    )


def test_the_quoted_configuration_is_complete_enough_to_load(
    tmp_path: Path,
) -> None:
    """
    Why the comparison above matters, asserted rather than argued.

    A block that is missing a required value parses as TOML and fails only
    when something tries to use it, which is what happened here.
    """
    copied = tmp_path / "from_readme.toml"

    copied.write_text(
        quoted_configuration() + "\n",
        encoding="utf-8",
    )

    assert (
        load_config(
            copied,
        ).image_input_limits
        is not None
    )


def test_the_extraction_finds_a_block_at_all() -> None:
    """
    Without this, an extraction that silently returned nothing would satisfy
    a comparison against an empty file and would satisfy nothing else
    visibly.
    """
    block = quoted_configuration()

    assert block.startswith(
        "[input]",
    )
    assert "[input_limits]" in block


@pytest.mark.parametrize(
    "section",
    (
        "[input]",
        "[generation]",
        "[input_limits]",
        "[output]",
        "[pdf_legend]",
    ),
)
def test_every_configuration_section_is_quoted(
    section: str,
) -> None:
    """
    Named individually so a failure says which section went missing rather
    than only that two long strings differ.
    """
    assert section in quoted_configuration()
