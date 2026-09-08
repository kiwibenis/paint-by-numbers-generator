# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Everything the catalogue offers can be selected.

`PaletteManager.available_palettes` and `PaletteManager.get` used to decide
what a palette file is called by two different rules. The catalogue split a
name on `-v`, ran `int()` over the rest and checked that the identifier was
not empty. The selection validated the identifier against a character set and
the version against a range, and then built the name itself.

Five distinct file names satisfied the first rule and not the second, so the
catalogue advertised palettes that could not be loaded:

    my.palette-v1.json          a character outside the accepted set
    <69 characters>-v1.json     an identifier longer than the limit
    goodid-v10000.json          a version above the accepted range
    leadingzero-v01.json        `int("01")` is 1, and `-v1.json` is a
                                different file
    underscoreint-v1_0.json     `int("1_0")` is 10, and `-v10.json` is a
                                different file

A chooser built from that catalogue offers an entry that fails when a person
picks it, and the failure says "Unknown palette" about something the same
program just listed.

Both now go through `pbn.infrastructure.palette_file_name`.

Palette identifiers are intentionally restricted to ASCII letters and digits.
Hyphens and underscores are therefore not valid inside an identifier, and
`-v` is the only separator between the identifier and its version.

The names were only half of it. This module first generated regular files
only, so it could not see the entries a directory can also hold. Three more
divergences lived there:

    a symlink pointing outside the directory was listed, and refused by
    `get`, which resolves the path and refuses one that leaves;

    one dangling symlink emptied the catalogue, because it caught
    `InvalidPaletteError` while the loader raises `PaletteNotFoundError`
    for a file that is not there;

    a symlink loop reached `get` as a `RuntimeError` from `Path.resolve`,
    left the error hierarchy entirely and reached a caller as a traceback
    and exit code 1.

A test that builds only the input it already expects is not a test of the
property, which is why the entries below are built as they are.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pbn.exceptions import PaletteNotFoundError
from pbn.infrastructure.palette_file_name import (
    PaletteIdentity,
    palette_file_name,
    parse_palette_file_name,
)
from pbn.infrastructure.palette_loader import PaletteLoader
from pbn.infrastructure.palette_manager import PaletteManager
from pbn.models import Palette

TEMPLATE = Path("palettes/reference8-v1.json")

LONG_IDENTIFIER = "toolongid" + "x" * 60

DIVERGENT_NAMES = (
    (
        "my.palette-v1.json",
        "my.palette",
        1,
    ),
    (
        f"{LONG_IDENTIFIER}-v1.json",
        LONG_IDENTIFIER,
        1,
    ),
    (
        "goodid-v10000.json",
        "goodid",
        10000,
    ),
    (
        "leadingzero-v01.json",
        "leadingzero",
        1,
    ),
    (
        "underscoreint-v1_0.json",
        "underscoreint",
        10,
    ),
)
"""
The five names the catalogue and selection historically disagreed about.

The identity beside each file name is the identity the document declares so
that the varied property remains the file-name contract.
"""

INVALID_IDENTIFIER_NAMES = (
    (
        "another_ok-v7.json",
        "another_ok",
        7,
    ),
    (
        "with-hyphen-v2.json",
        "with-hyphen",
        2,
    ),
    (
        "wrongseparator_v3.json",
        "wrongseparator",
        3,
    ),
)
"""
Names rejected by the current palette-file contract.

The first contains an underscore inside the identifier, the second contains a
hyphen inside the identifier, and the third uses `_v` instead of the required
`-v` version separator.
"""

REJECTED_NAMES = DIVERGENT_NAMES + INVALID_IDENTIFIER_NAMES

ACCEPTED_NAMES = (
    (
        "plainok-v1.json",
        "plainok",
        1,
    ),
    (
        "anotherOk-v7.json",
        "anotherOk",
        7,
    ),
    (
        "withHyphen-v2.json",
        "withHyphen",
        2,
    ),
)


def write_palette(
    directory: Path,
    *,
    file_name: str,
    palette_id: str,
    version: int,
) -> None:
    """
    Write a palette document that is valid apart from what is varied.

    Built from the shipped template so the colours and the schema are the
    real ones and the loader has nothing else to object to.
    """
    document = json.loads(
        TEMPLATE.read_text(
            encoding="utf-8",
        ),
    )

    document["metadata"]["id"] = palette_id
    document["metadata"]["version"] = version

    (directory / file_name).write_text(
        json.dumps(
            document,
        ),
        encoding="utf-8",
    )


def catalogue_directory(
    tmp_path: Path,
    entries: tuple[tuple[str, str, int], ...],
) -> Path:
    """
    Return a working directory holding a `palettes` directory of entries.
    """
    directory = tmp_path / "palettes"

    directory.mkdir()

    for file_name, palette_id, version in entries:
        write_palette(
            directory,
            file_name=file_name,
            palette_id=palette_id,
            version=version,
        )

    return tmp_path


def test_everything_the_catalogue_offers_can_be_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The property, over every accepted and rejected name at once.
    """
    monkeypatch.chdir(
        catalogue_directory(
            tmp_path,
            REJECTED_NAMES + ACCEPTED_NAMES,
        ),
    )

    manager = PaletteManager()

    for palette_id, version in manager.available():
        assert (
            manager.get(
                palette_id,
                version,
            ).id
            == palette_id
        )


def test_the_accepted_names_are_still_offered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Without this, a catalogue that offered nothing would satisfy the test
    above and would satisfy nothing else.
    """
    monkeypatch.chdir(
        catalogue_directory(
            tmp_path,
            REJECTED_NAMES + ACCEPTED_NAMES,
        ),
    )

    assert PaletteManager().available() == tuple(
        sorted((palette_id, version) for _, palette_id, version in ACCEPTED_NAMES),
    )


@pytest.mark.parametrize(
    (
        "file_name",
        "palette_id",
        "version",
    ),
    REJECTED_NAMES,
    ids=lambda value: str(value)[:24],
)
def test_a_rejected_name_is_neither_offered_nor_selectable(
    file_name: str,
    palette_id: str,
    version: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Named individually so a failure says which rejected name came back.
    """
    monkeypatch.chdir(
        catalogue_directory(
            tmp_path,
            (
                (
                    file_name,
                    palette_id,
                    version,
                ),
            ),
        ),
    )

    manager = PaletteManager()

    assert manager.available() == ()

    with pytest.raises(
        PaletteNotFoundError,
    ):
        manager.get(
            palette_id,
            version,
        )


@pytest.mark.parametrize(
    (
        "file_name",
        "palette_id",
        "version",
    ),
    DIVERGENT_NAMES,
    ids=lambda value: str(value)[:24],
)
def test_the_divergent_name_satisfied_the_rule_the_catalogue_used(
    file_name: str,
    palette_id: str,
    version: int,
) -> None:
    """
    These are regressions rather than names that were always refused.

    The rule reproduced here is the one `available_palettes` applied: split
    on `-v`, parse the rest as an integer, require a non-empty identifier.
    Each of the five passes it, which is why each of the five was listed.
    """
    stem = file_name.removesuffix(
        ".json",
    )

    assert "-v" in stem

    listed_id, version_text = stem.rsplit(
        "-v",
        1,
    )

    assert listed_id
    assert int(version_text) == version

    assert (
        parse_palette_file_name(
            file_name,
        )
        is None
    )


@pytest.mark.parametrize(
    "file_name",
    (
        "another_ok-v7.json",
        "with-hyphen-v2.json",
        "wrongseparator_v3.json",
    ),
)
def test_identifier_punctuation_and_wrong_separator_are_rejected(
    file_name: str,
) -> None:
    """
    Palette identifiers are alphanumeric and the version separator is `-v`.
    """
    assert (
        parse_palette_file_name(
            file_name,
        )
        is None
    )


@pytest.mark.parametrize(
    "identity",
    (
        PaletteIdentity(
            palette_id="reference8",
            version=1,
        ),
        PaletteIdentity(
            palette_id="a",
            version=9999,
        ),
        PaletteIdentity(
            palette_id="withHyphenAnd1",
            version=10,
        ),
        PaletteIdentity(
            palette_id="A" * 64,
            version=1,
        ),
    ),
    ids=lambda identity: f"{identity.palette_id[:12]}-v{identity.version}",
)
def test_a_valid_identity_survives_being_written_and_read_back(
    identity: PaletteIdentity,
) -> None:
    """
    What makes the two rules one rule: the name a selection builds is a
    name the catalogue recognises, and it yields the identity it was built
    from.
    """
    assert (
        parse_palette_file_name(
            palette_file_name(
                identity,
            ),
        )
        == identity
    )


def test_the_shipped_catalogue_is_selectable_in_full() -> None:
    """
    The property against the palettes the project actually ships, rather
    than only against constructed ones.
    """
    manager = PaletteManager()

    available = manager.available()

    assert available

    for palette_id, version in available:
        assert (
            manager.get(
                palette_id,
                version,
            ).version
            == version
        )


def test_an_unrecognised_name_is_skipped_without_being_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Why the catalogue checks the name as well as loading the document.

    Agreement is already guaranteed by the loader, which parses the name by
    the same rule and rejects a document whose name it does not recognise.
    The check in the catalogue earns its place by keeping a file it can
    never offer from being opened and parsed at all, up to the document
    size limit each time.

    Without this the check would be unfalsifiable: removing it changes
    nothing a caller can observe, which is not a property a check should
    have.
    """
    monkeypatch.chdir(
        catalogue_directory(
            tmp_path,
            REJECTED_NAMES + ACCEPTED_NAMES,
        ),
    )

    read: list[str] = []

    original = PaletteLoader.load

    def recording_load(
        self: PaletteLoader,
        file: Path,
    ) -> Palette:
        read.append(
            file.name,
        )

        return original(
            self,
            file,
        )

    monkeypatch.setattr(
        PaletteLoader,
        "load",
        recording_load,
    )

    PaletteManager().available()

    assert sorted(read) == sorted(file_name for file_name, _, _ in ACCEPTED_NAMES)


def build_entries(
    directory: Path,
) -> None:
    """
    Create every kind of directory entry a palette directory can hold.

    Only the last one is selectable. The others carry names `get` would
    build, so a name check alone cannot separate them.
    """
    outside = directory.parent / "outside"

    outside.mkdir()

    write_palette(
        outside,
        file_name="palette.json",
        palette_id="external",
        version=1,
    )

    (directory / "external-v1.json").symlink_to(
        outside / "palette.json",
    )

    (directory / "dangling-v1.json").symlink_to(
        directory / "absent.json",
    )

    first = directory / "loop-v1.json"
    second = directory / "loop2-v1.json"

    first.symlink_to(
        second,
    )
    second.symlink_to(
        first,
    )

    (directory / "adir-v1.json").mkdir()

    write_palette(
        directory,
        file_name="plainok-v1.json",
        palette_id="plainok",
        version=1,
    )


@pytest.fixture
def entry_directory(
    tmp_path: Path,
) -> Path:
    """
    Return a working directory holding those entries, or skip.

    A file system that cannot create a symlink cannot host the state under
    test, and passing there would say nothing.
    """
    directory = tmp_path / "palettes"

    directory.mkdir()

    try:
        build_entries(
            directory,
        )
    except (
        NotImplementedError,
        OSError,
    ) as error:  # pragma: no cover - platform dependent
        pytest.skip(
            f"symlinks unavailable: {error}",
        )

    return tmp_path


def test_the_catalogue_survives_every_kind_of_entry(
    entry_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    One dangling symlink used to raise out of here and report nothing, so
    a single broken entry hid every working palette beside it.
    """
    monkeypatch.chdir(
        entry_directory,
    )

    assert PaletteManager().available() == (
        (
            "plainok",
            1,
        ),
    )


def test_everything_offered_beside_those_entries_can_be_selected(
    entry_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The same property as above, over a directory holding entries that are
    not regular files.
    """
    monkeypatch.chdir(
        entry_directory,
    )

    manager = PaletteManager()

    for palette_id, version in manager.available():
        assert (
            manager.get(
                palette_id,
                version,
            ).id
            == palette_id
        )


@pytest.mark.parametrize(
    "palette_id",
    (
        "external",
        "dangling",
        "loop",
        "adir",
    ),
)
def test_selecting_an_unusable_entry_stays_inside_the_hierarchy(
    palette_id: str,
    entry_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    `PaletteNotFoundError` rather than whatever the file system raised.

    `Path.resolve` answers a symlink loop with `RuntimeError`, which is not
    an `OSError` and not a `PbnError`, so it passed through the CLI and
    reached a caller as a traceback instead of exit code 65.
    """
    monkeypatch.chdir(
        entry_directory,
    )

    with pytest.raises(
        PaletteNotFoundError,
    ):
        PaletteManager().get(
            palette_id,
            1,
        )


def test_the_external_document_is_otherwise_loadable(
    entry_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Why the symlink case says something about containment rather than
    about the document.

    The same file loads when it sits in the directory, so what the
    catalogue and the selection agree to refuse is where it is, not what
    it holds.
    """
    monkeypatch.chdir(
        entry_directory,
    )

    (entry_directory / "palettes" / "external-v1.json").unlink()

    (entry_directory / "outside" / "palette.json").rename(
        entry_directory / "palettes" / "external-v1.json",
    )

    manager = PaletteManager()

    assert (
        "external",
        1,
    ) in manager.available()

    assert (
        manager.get(
            "external",
            1,
        ).id
        == "external"
    )
