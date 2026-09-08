# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import pytest

from pbn.cli.main import build_parser


def test_generate_help_exposes_region_complexity_parameters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(
            [
                "generate",
                "--help",
            ],
        )

    assert exc_info.value.code == 0

    captured = capsys.readouterr()

    assert "--region-complexity-reduction-enabled" in captured.out
    assert "--max-regions" in captured.out
    assert "--maximum-merge-cost" in captured.out
    assert "--merge-cost-color-weight" in captured.out
    assert "--merge-cost-affected-area-weight" in captured.out
    assert "--merge-cost-border-weight" in captured.out
    assert "--merge-cost-geometry-weight" in captured.out
    assert "--merge-cost-enclosure-strength" in captured.out
    assert "--merge-cost-compactness-strength" in captured.out
    assert "--regions " not in captured.out


def test_generate_rejects_removed_regions_parameter() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "generate",
                "--regions",
                "350",
            ],
        )
