# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class GeometryError(PbnError):
    """
    Base class for outline geometry errors.
    """

    public_message: ClassVar[str] = "The outline geometry could not be produced."
    caused_by_request: ClassVar[bool] = False


class GeometryAccelerationError(GeometryError):
    """
    Accelerated geometry evaluation could not decide a case safely.

    The accelerated path is an installation choice rather than a
    property of the request, so an undecidable case is an operational
    failure even though a particular image triggered it.
    """

    public_message: ClassVar[str] = "The outline geometry could not be produced."
    caused_by_request: ClassVar[bool] = False


class GeometryUnavailableError(GeometryError):
    """
    The geometry library required by ADR-0015 could not be used.

    Distinct from `GeometryAccelerationError`, which concerns a case the
    accelerated path refused to decide. This one means the path does not
    exist, which is a fault of the installation rather than of a run.
    """

    public_message: ClassVar[str] = "The service is not installed correctly."
    caused_by_request: ClassVar[bool] = False
