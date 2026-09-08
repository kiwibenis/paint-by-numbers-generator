# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from pbn.exceptions import (
    ConfigurationError,
    ImageError,
    ImageNotFoundError,
    PbnError,
    RegionError,
    RegionPaintabilityError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(ConfigurationError, PbnError)
    assert issubclass(ImageError, PbnError)
    assert issubclass(ImageNotFoundError, ImageError)
    assert issubclass(RegionError, PbnError)
    assert issubclass(RegionPaintabilityError, RegionError)
