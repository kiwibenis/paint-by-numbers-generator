# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar


class PbnError(Exception):
    """
    Base class for all project-specific exceptions.

    Every error carries two messages for two audiences, per ADR-0019. The
    message the exception is constructed with is the diagnostic message
    and is written for the operator. The public message is a fixed class
    attribute written for a caller that is not trusted.

    The defaults disclose the least and blame the operation rather than
    the request, so that a subclass which forgets to declare them fails
    towards silence rather than towards disclosure.
    """

    public_message: ClassVar[str] = "The request could not be processed."
    """
    Message that may be shown to an untrusted caller.

    Never interpolated. A message that cannot carry a value cannot leak
    one, which is what makes this property checkable by inspecting the
    classes rather than every raise site.
    """

    caused_by_request: ClassVar[bool] = False
    """
    Whether the request caused this error rather than the operation.

    An interface derives a client error from `True` and a server error
    from `False`.
    """

    @property
    def diagnostic_message(self) -> str:
        """
        Return the message written for the operator.

        May name paths, values and internal steps, and belongs in logs
        and in the trusted local interface rather than in a response to
        an untrusted caller.
        """
        return str(self)
