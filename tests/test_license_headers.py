# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Verify that Python source files carry the required license notices.

The project is licensed under `AGPL-3.0-only` with additional terms under
sections 7(b) and 7(c). Section 7 requires applicable additional terms to be
stated in the relevant source files or for those files to contain a notice
indicating where the terms can be found.

Every Python source file under `src`, `tests` and `tools` therefore carries
three header lines:

    the copyright holder;

    the SPDX license identifier;

    the pointer to `ADDITIONAL-TERMS.md`.

The tests also keep the header consistent with the package metadata, license
text and additional-terms file.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from tools.benchmark_region_complexity import REPOSITORY_ROOT

SOURCE_DIRECTORIES = (
    "src",
    "tests",
    "tools",
)

ADDITIONAL_TERMS_FILE = "ADDITIONAL-TERMS.md"

LICENSE_FILE = "LICENSE"

SPDX_IDENTIFIER = "AGPL-3.0-only"

HEADER_LINES = (
    "# SPDX-FileCopyrightText: 2026 kiwibenis",
    f"# SPDX-License-Identifier: {SPDX_IDENTIFIER}",
    (
        "# Additional terms under AGPL-3.0 section 7 apply; "
        f"see {ADDITIONAL_TERMS_FILE}"
    ),
)

PROJECT_FILE = REPOSITORY_ROOT / "pyproject.toml"

SOURCE_MODULES = tuple(
    sorted(
        path
        for directory in SOURCE_DIRECTORIES
        for path in (REPOSITORY_ROOT / directory).rglob("*.py")
    ),
)


def header_lines_of(
    path: Path,
) -> tuple[str, ...]:
    """
    Return the leading lines corresponding to the required license header.
    """
    return tuple(
        path.read_text(
            encoding="utf-8",
        ).splitlines()[: len(HEADER_LINES)],
    )


def test_the_source_modules_were_found() -> None:
    """
    Ensure the repository scan covers representative production and test code.
    """
    names = {path.name for path in SOURCE_MODULES}

    assert "palette_file_name.py" in names
    assert "test_license_headers.py" in names

    assert len(SOURCE_MODULES) > 250


@pytest.mark.parametrize(
    "path",
    SOURCE_MODULES,
    ids=lambda path: str(
        path.relative_to(
            REPOSITORY_ROOT,
        ),
    ),
)
def test_the_module_carries_the_license_header(
    path: Path,
) -> None:
    """
    Require every Python source file in the covered trees to carry the header.
    """
    found = header_lines_of(
        path,
    )

    assert found == HEADER_LINES, (
        f"{path.relative_to(REPOSITORY_ROOT)} does not open with the "
        f"required license header; AGPL-3.0 section 7 requires the "
        f"applicable additional terms to be stated or pointed at in the "
        f"source file, and this file opens with {found}"
    )


def test_a_module_without_the_header_is_reported(
    tmp_path: Path,
) -> None:
    """
    Verify that an unmarked Python source file does not satisfy the check.
    """
    unmarked = tmp_path / "unmarked_module.py"

    unmarked.write_text(
        '"""\nA module without a license header.\n"""\n',
        encoding="utf-8",
    )

    assert (
        header_lines_of(
            unmarked,
        )
        != HEADER_LINES
    )


def test_the_header_names_the_declared_license() -> None:
    """
    Keep source-file SPDX identifiers aligned with package metadata.
    """
    declared = tomllib.loads(
        PROJECT_FILE.read_text(
            encoding="utf-8",
        ),
    )[
        "project"
    ]["license"]

    assert declared == SPDX_IDENTIFIER


def test_the_license_file_is_the_named_license() -> None:
    """
    Verify that LICENSE identifies the GNU Affero GPL version 3.
    """
    text = (REPOSITORY_ROOT / LICENSE_FILE).read_text(
        encoding="utf-8",
    )

    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3, 19 November 2007" in text
    assert "END OF TERMS AND CONDITIONS" in text


def test_the_additional_terms_file_holds_the_section_seven_terms() -> None:
    """
    Verify that the referenced attribution and origin terms remain present.
    """
    text = (REPOSITORY_ROOT / ADDITIONAL_TERMS_FILE).read_text(
        encoding="utf-8",
    )

    assert "Section 7(b) and 7(c)" in text
    assert "Originally developed by kiwibenis" in text
    assert (
        "Original source: " "https://github.com/kiwibenis/paint-by-numbers-generator"
    ) in text
    assert "must not misrepresent their origin" in text


def test_the_additional_terms_file_ships_with_the_package() -> None:
    """
    Ensure both legal files are included in built package distributions.
    """
    license_files = tomllib.loads(
        PROJECT_FILE.read_text(
            encoding="utf-8",
        ),
    )[
        "project"
    ]["license-files"]

    assert LICENSE_FILE in license_files
    assert ADDITIONAL_TERMS_FILE in license_files
