# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pbn.application.overlap_detector_port import OverlapDetectorPort
from pbn.exceptions import GeometryUnavailableError

GEOMETRY_LIBRARY = "shapely"
"""
Distribution the accelerated predicates are implemented against.
"""


def build_overlap_detector() -> OverlapDetectorPort:
    """
    Build the accelerated overlap detector.

    The geometry library is a mandatory dependency per ADR-0015, so this
    raises rather than returning a marker for the caller to fall back on.
    Normal generation has no supported reference-path fallback.

    An absent library and one that is present but fails to load are
    reported separately, because the first is an installation fault and
    the second an environment or version fault.
    """
    try:
        from .shapely_overlap_detector import ShapelyOverlapDetector

    except ModuleNotFoundError as exc:
        if (exc.name or "").split(".")[0] == GEOMETRY_LIBRARY:
            raise GeometryUnavailableError(
                f"The geometry library {GEOMETRY_LIBRARY} is not "
                f"installed. It is a mandatory dependency.",
            ) from exc

        raise GeometryUnavailableError(
            f"The geometry library {GEOMETRY_LIBRARY} is installed but "
            f"a module it requires is missing: {exc.name}.",
        ) from exc

    except ImportError as exc:
        raise GeometryUnavailableError(
            f"The geometry library {GEOMETRY_LIBRARY} is installed but "
            f"could not be loaded.",
        ) from exc

    return ShapelyOverlapDetector()
