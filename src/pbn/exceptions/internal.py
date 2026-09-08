# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class InvariantViolationError(PbnError):
    """
    The project's own processing produced a state it says cannot occur.

    Distinct from every other error here, which describes something about
    the request or the environment. This one describes a defect: an
    outline that is not closed, a palette search that found no candidate,
    a merge stage that left work it had already decided to do. A run that
    reaches one of these has found a bug rather than a bad input.

    These conditions were raised as `RuntimeError` and so escaped the
    process contract entirely: the caller saw exit code 1 rather than one
    of the four codes ADR-0026 defines, an empty `--json` stdout rather
    than the failure object it promises, and a traceback naming
    installation paths on standard error, which is the disclosure ADR-0019
    exists to prevent.

    Attributed to the operation rather than to the request. An image may
    be what triggered the defect, but a caller cannot correct a defect by
    changing what it sent, and the exit code has to say so.
    """

    public_message: ClassVar[str] = "The request could not be processed."
    caused_by_request: ClassVar[bool] = False
