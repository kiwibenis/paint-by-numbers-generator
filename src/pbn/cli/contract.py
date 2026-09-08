# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import json
import sys
from typing import Final

from pbn.exceptions import ConfigurationError, PbnError
from pbn.models import Palette

EXIT_SUCCESS: Final = 0
"""
A document was produced.
"""

EXIT_REQUEST: Final = 65
"""
The request caused the failure: the image, or a value that came with it.

`EX_DATAERR` in the `sysexits` convention. A front end answers a client
error to this.
"""

EXIT_CONFIGURATION: Final = 78
"""
The configuration caused the failure.

`EX_CONFIG`. Distinct from an operational failure because it names what
an operator has to change.
"""

EXIT_OPERATION: Final = 70
"""
The operation caused the failure: a defect, or the environment.

`EX_SOFTWARE`. A front end answers a server error to this.
"""


def exit_code_for(
    error: PbnError,
) -> int:
    """
    Return the exit code an error corresponds to.

    Derived from the attribution of ADR-0019 rather than from the class,
    so a new error type needs no change here. Configuration is separated
    because it names a different action than any other operational
    failure.
    """
    if isinstance(error, ConfigurationError):
        return EXIT_CONFIGURATION

    if error.caused_by_request:
        return EXIT_REQUEST

    return EXIT_OPERATION


def report_success(
    *,
    machine_readable: bool,
    output: str,
) -> None:
    """
    Report a produced document.

    In machine-readable mode this is the single object on standard
    output. Otherwise standard output stays empty, because a person
    already saw the progress on standard error.
    """
    if not machine_readable:
        return

    _write(
        {
            "status": "succeeded",
            "output": output,
        },
    )


def report_palettes(
    *,
    machine_readable: bool,
    palettes: tuple[Palette, ...],
) -> None:
    """
    Report the palettes a caller may select.

    Standard output carries the result, per ADR-0019 and ADR-0026, and
    here the result is the listing itself. That is why this writes to
    standard output in both modes, where `report_success` writes only in
    machine-readable mode: there the result is a file on a path the
    caller already knows.

    Nothing here is disclosing. The identifiers, names and counts are
    the operator's own catalogue, and a caller has to know them to
    select one. The directory holding them is not reported.
    """
    if not machine_readable:
        for palette in palettes:
            print(
                f"{palette.id} v{palette.version}  "
                f"{palette.display_name} "
                f"({palette.manufacturer}, "
                f"{len(palette.colors)} colors)",
            )

        return

    _write(
        {
            "status": "succeeded",
            "palettes": [
                {
                    "id": palette.id,
                    "version": palette.version,
                    "manufacturer": palette.manufacturer,
                    "display_name": palette.display_name,
                    "color_count": len(palette.colors),
                }
                for palette in palettes
            ],
        },
    )


def report_failure(
    *,
    machine_readable: bool,
    error: PbnError,
) -> None:
    """
    Report a failure, and put nothing disclosing on standard output.

    The message here is the one written for a stranger, per ADR-0019. A
    front end that prints what this puts on standard output cannot leak
    a path by doing so. The diagnostic message goes to standard error.
    """
    print(
        f"{type(error).__name__}: {error.diagnostic_message}",
        file=sys.stderr,
    )

    if not machine_readable:
        return

    _write(
        {
            "status": "failed",
            "error": {
                "type": type(error).__name__,
                "message": error.public_message,
                "caused_by_request": error.caused_by_request,
            },
        },
    )


def _write(
    payload: dict[str, object],
) -> None:
    print(
        json.dumps(
            payload,
            sort_keys=True,
        ),
        flush=True,
    )
