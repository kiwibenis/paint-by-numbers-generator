# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from pbn.exceptions import ConfigurationError

cli_main = importlib.import_module(
    "pbn.cli.main",
)


def test_generate_reports_config_file_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_error = ConfigurationError(
        "Could not read configuration file: missing.toml",
    )

    def fake_load_config_values(
        config_file: Path,
        value_names: tuple[str, ...],
    ) -> dict[str, object]:
        assert config_file == Path(
            "missing.toml",
        )
        assert value_names

        raise config_error

    monkeypatch.setattr(
        cli_main,
        "load_config_values",
        fake_load_config_values,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            "missing.toml",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code != 0

    captured = capsys.readouterr()

    assert (
        "ConfigurationError: "
        "Could not read configuration file: missing.toml" in captured.err
    )
