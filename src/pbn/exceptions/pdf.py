# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from typing import ClassVar

from .base import PbnError


class PdfExportError(PbnError):
    """
    PDF export failed.
    """

    public_message: ClassVar[str] = "The document could not be exported."
    caused_by_request: ClassVar[bool] = False
