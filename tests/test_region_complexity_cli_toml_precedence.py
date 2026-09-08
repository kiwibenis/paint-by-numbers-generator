# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from pbn.config import GeneratorConfig
from tests.fake_image_loader import loader_class_for

cli_main = importlib.import_module(
    "pbn.cli.main",
)

EXAMPLE_CONFIG = Path(
    "config/example.toml",
)


def install_generation_fakes(
    monkeypatch: pytest.MonkeyPatch,
    captured: dict[str, object],
) -> None:
    def fake_load_image(
        image_path: Path,
        limits: object = None,
    ) -> object:
        captured["image_path"] = image_path
        return object()

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> object:
            captured["palette_id"] = palette_id
            captured["palette_version"] = version
            return object()

    class FakeGeneratorApplication:
        def __init__(
            self,
            progress_reporter: object,
            quantization_executor: object | None = None,
            overlap_detector: object | None = None,
            image_loader: object | None = None,
        ) -> None:
            pass

        def generate_pdf(
            self,
            image_path: object,
            palette: object,
            config: GeneratorConfig,
            pdf_exporter: object,
        ) -> bytes:
            captured["config"] = config
            return b"%PDF-test"

    monkeypatch.setattr(
        cli_main,
        "ImageLoader",
        loader_class_for(fake_load_image),
    )
    monkeypatch.setattr(
        cli_main,
        "PaletteManager",
        FakePaletteManager,
    )
    monkeypatch.setattr(
        cli_main,
        "GeneratorApplication",
        FakeGeneratorApplication,
    )


def run_generate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cli_values: list[str],
) -> GeneratorConfig:
    output_path = tmp_path / "output.pdf"
    captured: dict[str, object] = {}

    install_generation_fakes(
        monkeypatch,
        captured,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "pbn",
            "generate",
            "--config_file",
            str(EXAMPLE_CONFIG),
            "--output",
            str(output_path),
            *cli_values,
        ],
    )

    cli_main.main()

    config = captured["config"]

    assert isinstance(
        config,
        GeneratorConfig,
    )
    assert output_path.read_bytes() == b"%PDF-test"

    return config


def test_cli_region_complexity_values_override_toml_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = run_generate(
        monkeypatch,
        tmp_path,
        [
            "--region-complexity-reduction-enabled",
            "false",
            "--max-regions",
            "125",
            "--maximum-merge-cost",
            "0.200",
            "--merge-cost-color-weight",
            "0.25",
            "--merge-cost-affected-area-weight",
            "0.25",
            "--merge-cost-border-weight",
            "0.25",
            "--merge-cost-geometry-weight",
            "0.25",
            "--merge-cost-enclosure-strength",
            "0.25",
            "--merge-cost-compactness-strength",
            "0.75",
        ],
    )

    complexity = config.region_complexity
    merge_cost = complexity.merge_cost

    assert complexity.reduction_enabled is False
    assert complexity.max_regions == 125
    assert complexity.maximum_merge_cost == 0.200

    assert merge_cost.color_weight == 0.25
    assert merge_cost.affected_area_weight == 0.25
    assert merge_cost.border_weight == 0.25
    assert merge_cost.geometry_weight == 0.25
    assert merge_cost.enclosure_strength == 0.25
    assert merge_cost.compactness_strength == 0.75

    assert config.minimum_region_size_mm == 2.0


def test_single_cli_complexity_override_preserves_toml_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = run_generate(
        monkeypatch,
        tmp_path,
        [
            "--max-regions",
            "275",
        ],
    )

    complexity = config.region_complexity
    merge_cost = complexity.merge_cost

    assert complexity.reduction_enabled is True
    assert complexity.max_regions == 275
    assert complexity.maximum_merge_cost == 0.300

    assert merge_cost.color_weight == 0.40
    assert merge_cost.affected_area_weight == 0.25
    assert merge_cost.border_weight == 0.15
    assert merge_cost.geometry_weight == 0.20
    assert merge_cost.enclosure_strength == 0.50
    assert merge_cost.compactness_strength == 0.15
