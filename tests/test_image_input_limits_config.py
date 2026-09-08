# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from pathlib import Path

import pytest

from pbn.application.generator_config_builder import (
    build_image_input_limits_config,
    missing_config_values,
)
from pbn.application.generator_config_validator import (
    GeneratorConfigValidator,
)
from pbn.config import ImageInputLimitsConfig
from pbn.exceptions import ConfigurationError
from pbn.infrastructure.config_loader import load_config

_CONFIG_VALUE_NAMES = (
    "maximum_input_pixel_count",
    "maximum_input_width",
    "maximum_input_height",
    "processing_pixel_count",
)


def _values(
    **overrides: object,
) -> dict[str, object]:
    values: dict[str, object] = {
        "maximum_input_pixel_count": 50_000_000,
        "maximum_input_width": 20_000,
        "maximum_input_height": 20_000,
        "processing_pixel_count": 1_600_000,
    }
    values.update(overrides)

    return values


def _config(
    **overrides: object,
) -> ImageInputLimitsConfig:
    values: dict[str, object] = {
        "maximum_pixel_count": 50_000_000,
        "maximum_width": 20_000,
        "maximum_height": 20_000,
        "processing_pixel_count": 1_600_000,
    }
    values.update(overrides)

    return ImageInputLimitsConfig(**values)  # type: ignore[arg-type]


def test_complete_values_build_the_configuration() -> None:
    config = build_image_input_limits_config(
        _values(),
    )

    assert config.maximum_pixel_count == 50_000_000
    assert config.maximum_width == 20_000
    assert config.maximum_height == 20_000
    assert config.processing_pixel_count == 1_600_000


@pytest.mark.parametrize(
    "name",
    _CONFIG_VALUE_NAMES,
)
def test_every_value_is_required(
    name: str,
) -> None:
    values = _values()
    del values[name]

    with pytest.raises(ConfigurationError):
        build_image_input_limits_config(
            values,
        )


@pytest.mark.parametrize(
    "name",
    _CONFIG_VALUE_NAMES,
)
def test_missing_values_are_reported_by_the_generator_config(
    name: str,
) -> None:
    assert name in missing_config_values(
        {},
    )


def test_boolean_is_not_accepted_as_an_integer_limit() -> None:
    with pytest.raises(ConfigurationError):
        build_image_input_limits_config(
            _values(
                maximum_input_pixel_count=True,
            ),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"maximum_pixel_count": 0},
        {"maximum_width": 0},
        {"maximum_height": 0},
        {"processing_pixel_count": 0},
        {"maximum_pixel_count": -1},
    ],
)
def test_non_positive_limits_are_rejected(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ConfigurationError):
        GeneratorConfigValidator().validate_image_input_limits(
            _config(**overrides),
        )


def test_processing_resolution_above_the_maximum_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        GeneratorConfigValidator().validate_image_input_limits(
            _config(
                maximum_pixel_count=1_000_000,
                processing_pixel_count=1_000_001,
            ),
        )


def test_pixel_count_above_the_dimension_product_is_rejected() -> None:
    """
    A pixel limit that no accepted image can reach bounds nothing.
    """
    with pytest.raises(ConfigurationError):
        GeneratorConfigValidator().validate_image_input_limits(
            _config(
                maximum_width=1_000,
                maximum_height=1_000,
                maximum_pixel_count=1_000_001,
                processing_pixel_count=1_000,
            ),
        )


def test_example_configuration_provides_the_limits() -> None:
    config = load_config(
        Path("config/example.toml"),
    )

    limits = config.image_input_limits

    assert limits.processing_pixel_count == 1_600_000
    assert limits.maximum_pixel_count >= limits.processing_pixel_count
    assert limits.maximum_width > 0
    assert limits.maximum_height > 0


def test_missing_input_limits_section_is_rejected(
    tmp_path: Path,
) -> None:
    source = Path("config/example.toml").read_text()
    start = source.index("[input_limits]")
    end = source.index("[output]")

    path = tmp_path / "without_limits.toml"
    path.write_text(
        source[:start] + source[end:],
    )

    with pytest.raises(ConfigurationError):
        load_config(
            path,
        )
