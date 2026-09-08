# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The parts of `dependency-security.md` that are the project's own stay true.

That document holds three kinds of number and says so. Only two of them can
be checked here, and the distinction is the point rather than an omission:

    a declared bound is the project's own and belongs to `pyproject.toml`;
    a project invariant is asserted by a test and a change is a defect;
    an observation was true of a named version on a named date.

The Declared column and the four reachable formats are checked. The Measured
column is not, and must not be: those are the versions that happened to be
installed when the document was written, and a test would turn a fact about
the world into an obligation on it, failing on every unrelated upgrade until
someone edited prose to make a test pass.

The document already carried the date. What it did not separate was which of
its numbers the date applies to. `43 decoders registered` is a property of
two named library versions and does not drift over time; `4 reachable` is
this project's and drifts never.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from pbn.infrastructure.image_decoder_policy import SUPPORTED_IMAGE_FORMATS

DOCUMENT = Path("docs/dependency-security.md")

PROJECT_FILE = Path("pyproject.toml")

DEPENDENCY_ROW_PATTERN = re.compile(
    r"^\| (\w[\w.-]*) \| `([^`]+)` \| ([^|]*) \|([^|]*)\|$",
    re.MULTILINE,
)


def documented_dependencies() -> dict[str, str]:
    """
    Return the declared specifier the document states, by package.
    """
    return {
        package.lower(): declared
        for package, declared, _, _ in DEPENDENCY_ROW_PATTERN.findall(
            DOCUMENT.read_text(
                encoding="utf-8",
            ),
        )
    }


def declared_dependencies() -> dict[str, str]:
    """
    Return the declared specifier `pyproject.toml` carries, by package.
    """
    found: dict[str, str] = {}

    for requirement in tomllib.loads(
        PROJECT_FILE.read_text(
            encoding="utf-8",
        ),
    )[
        "project"
    ]["dependencies"]:
        match = re.fullmatch(
            r"([A-Za-z][\w.-]*)(.*)",
            requirement,
        )

        assert match is not None, requirement

        found[match.group(1).lower()] = match.group(2)

    return found


def test_the_document_states_the_dependencies() -> None:
    """
    Without this, a pattern that stopped matching would leave the check
    below comparing two empty mappings.
    """
    assert len(
        documented_dependencies(),
    ) == len(
        declared_dependencies(),
    )

    assert len(declared_dependencies()) >= 3


@pytest.mark.parametrize(
    "package",
    sorted(
        declared_dependencies(),
    ),
)
def test_the_documented_bound_is_the_declared_one(
    package: str,
) -> None:
    documented = documented_dependencies()

    assert (
        package in documented
    ), f"{DOCUMENT} does not list {package}, which {PROJECT_FILE} declares"

    assert documented[package] == declared_dependencies()[package], (
        f"{DOCUMENT} states {documented[package]!r} for {package}, "
        f"{PROJECT_FILE} declares {declared_dependencies()[package]!r}"
    )


def test_the_document_names_the_formats_that_stay_reachable() -> None:
    """
    The other half the project owns: which decoders survive the allowlist.

    A format added to the policy without being named here would leave the
    document describing a narrower boundary than the one in force, which is
    the direction that matters for a document about security state.
    """
    text = DOCUMENT.read_text(
        encoding="utf-8",
    )

    for image_format in SUPPORTED_IMAGE_FORMATS:
        assert image_format in text, f"{DOCUMENT} does not name {image_format}"

    assert len(SUPPORTED_IMAGE_FORMATS) == 4, (
        "the document states four reachable decoders in words; "
        f"the policy now has {len(SUPPORTED_IMAGE_FORMATS)}"
    )
