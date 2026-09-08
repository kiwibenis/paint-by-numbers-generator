# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class ConfigurationError(PbnError):
    """
    Raised when the application configuration is invalid.

    Configuration is operator data. A caller cannot influence it, so an
    invalid configuration is an operational failure.
    """

    public_message: ClassVar[str] = "The service is not configured correctly."
    caused_by_request: ClassVar[bool] = False
