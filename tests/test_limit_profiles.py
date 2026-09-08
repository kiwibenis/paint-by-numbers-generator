# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
ADR-0016 requires two limit profiles that differ in values only.

A profile that also differs in which controls apply would let a control
be silently absent from the stricter one, which is the failure this
checks for.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from pathlib import Path

from pbn.infrastructure.config_loader import load_config

_TRUSTED = Path("config/example.toml")
_UNTRUSTED = Path("config/untrusted.toml")


def _read(
    path: Path,
) -> dict[str, object]:
    with path.open("rb") as handle:
        document: dict[str, object] = tomllib.load(handle)

    return document


def _keys(
    table: object,
    prefix: str = "",
) -> Iterator[str]:
    if not isinstance(table, dict):
        return

    for key, value in table.items():
        path = f"{prefix}{key}"

        yield path
        yield from _keys(
            value,
            f"{path}.",
        )


def test_both_profiles_declare_the_same_controls() -> None:
    assert set(
        _keys(_read(_TRUSTED)),
    ) == set(
        _keys(_read(_UNTRUSTED)),
    )


def test_both_profiles_load() -> None:
    assert load_config(_TRUSTED)
    assert load_config(_UNTRUSTED)


def test_the_untrusted_profile_bounds_input_more_tightly() -> None:
    trusted = load_config(_TRUSTED).image_input_limits
    untrusted = load_config(_UNTRUSTED).image_input_limits

    assert untrusted.maximum_pixel_count < trusted.maximum_pixel_count
    assert untrusted.maximum_width < trusted.maximum_width
    assert untrusted.maximum_height < trusted.maximum_height


def test_the_processing_resolution_matches_the_measured_limits() -> None:
    """
    The recorded wall-clock and address-space values were measured at
    this resolution and do not carry over to another.
    """
    assert (
        load_config(
            _UNTRUSTED,
        ).image_input_limits.processing_pixel_count
        == 1_600_000
    )
