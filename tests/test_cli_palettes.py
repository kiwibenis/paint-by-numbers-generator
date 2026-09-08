# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
The palette listing is part of the integration contract.

A caller selects an identifier and cannot supply a document, so
something has to tell it which identifiers exist. Without this command a
front end would read `palettes/` itself, which means reproducing the
file naming rule and the schema, and offering palettes that do not load.

Driven as a subprocess for the same reason as
`test_untrusted_input_contract.py`: what a caller in another language
sees is an exit code and a stream, not a return value.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pbn.cli.contract import EXIT_OPERATION, EXIT_SUCCESS
from pbn.infrastructure.palette_manager import PaletteManager


def run_palettes(
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pbn",
            "palettes",
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )


@pytest.fixture(scope="module")
def listing() -> dict[str, object]:
    completed = run_palettes(
        "--json",
    )

    assert completed.returncode == EXIT_SUCCESS, completed.stderr

    payload = json.loads(
        completed.stdout,
    )

    assert isinstance(
        payload,
        dict,
    )

    return payload


def test_the_listing_is_one_object_reporting_success(
    listing: dict[str, object],
) -> None:
    assert listing["status"] == "succeeded"
    assert set(listing) == {
        "status",
        "palettes",
    }


def test_every_entry_carries_the_fields_a_chooser_needs(
    listing: dict[str, object],
) -> None:
    palettes = listing["palettes"]

    assert isinstance(
        palettes,
        list,
    )
    assert palettes

    for entry in palettes:
        assert set(entry) == {
            "id",
            "version",
            "manufacturer",
            "display_name",
            "color_count",
        }
        assert isinstance(
            entry["id"],
            str,
        )
        assert isinstance(
            entry["version"],
            int,
        )
        assert entry["color_count"] > 0


def test_the_listing_matches_what_generation_would_accept(
    listing: dict[str, object],
) -> None:
    """
    A listed palette that `generate` refuses would be worse than no
    listing, because a front end would offer it.
    """
    palettes = listing["palettes"]

    assert isinstance(
        palettes,
        list,
    )

    listed = {
        (
            entry["id"],
            entry["version"],
        )
        for entry in palettes
    }

    assert listed == set(
        PaletteManager().available(),
    )

    for palette_id, version in sorted(
        listed,
    ):
        assert PaletteManager().get(
            str(palette_id),
            int(version),
        )


def test_the_listing_is_ordered(
    listing: dict[str, object],
) -> None:
    """
    Directory order is not an order. A caller showing the listing
    unchanged should not see it move between runs.
    """
    palettes = listing["palettes"]

    assert isinstance(
        palettes,
        list,
    )

    keys = [
        (
            entry["id"],
            entry["version"],
        )
        for entry in palettes
    ]

    assert keys == sorted(
        keys,
    )


def test_the_human_listing_goes_to_standard_output() -> None:
    """
    Unlike `generate`, which writes nothing there without `--json`.

    ADR-0026 puts the result on standard output. For generation the
    result is a file the caller already named; here it is the listing
    itself.
    """
    completed = run_palettes()

    assert completed.returncode == EXIT_SUCCESS
    assert "reference8 v1" in completed.stdout
    assert "Reference 8" in completed.stdout


def test_the_listing_does_not_disclose_the_palette_directory() -> None:
    for completed in (
        run_palettes(),
        run_palettes(
            "--json",
        ),
    ):
        assert "palettes/" not in completed.stdout
        assert "palettes\\" not in completed.stdout


def test_a_missing_catalogue_is_an_operation_failure(
    tmp_path: Path,
) -> None:
    """
    Not a request failure: there is no request to blame.

    The palette directory is relative to the working directory. Were
    this reported as an empty listing, running from the wrong place
    would look exactly like a deployment with no palettes installed, and
    a front end would show an empty chooser instead of failing.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pbn",
            "palettes",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    assert completed.returncode == EXIT_OPERATION

    payload = json.loads(
        completed.stdout,
    )

    assert payload["status"] == "failed"
    assert payload["error"]["type"] == "PaletteCatalogueError"
    assert payload["error"]["caused_by_request"] is False


def test_an_empty_catalogue_is_an_empty_listing(
    tmp_path: Path,
) -> None:
    """
    Distinct from the case above, which is the point of separating them.

    An existing directory holding nothing is the true statement that no
    palettes are installed, and a caller can act on it.
    """
    (tmp_path / "palettes").mkdir()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pbn",
            "palettes",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    assert completed.returncode == EXIT_SUCCESS
    assert json.loads(
        completed.stdout,
    ) == {
        "status": "succeeded",
        "palettes": [],
    }


def test_a_palette_that_does_not_load_is_skipped(
    tmp_path: Path,
) -> None:
    """
    One broken document must not make the others unlistable.

    The operator sees that failure when the palette is selected, where
    it names the palette. Refusing the whole catalogue would hide the
    working ones behind it.
    """
    directory = tmp_path / "palettes"
    directory.mkdir()

    (directory / "broken-v1.json").write_text(
        "{ not json",
        encoding="utf-8",
    )
    (directory / "usable-v1.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "id": "usable",
                    "manufacturer": "Test",
                    "display_name": "Usable",
                    "version": 1,
                },
                "colors": [
                    {
                        "number": 1,
                        "name": "White",
                        "rgb": {
                            "red": 255,
                            "green": 255,
                            "blue": 255,
                        },
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pbn",
            "palettes",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    assert completed.returncode == EXIT_SUCCESS

    palettes = json.loads(
        completed.stdout,
    )["palettes"]

    assert [entry["id"] for entry in palettes] == [
        "usable",
    ]
