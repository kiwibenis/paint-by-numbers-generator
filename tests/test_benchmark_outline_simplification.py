# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

from __future__ import annotations

from inspect import Parameter, signature
from types import SimpleNamespace
from typing import cast

import pytest

from pbn.application.generator_application import GeneratorApplication
from pbn.application.image_loader_port import ImageLoaderPort
from pbn.config.models import GeneratorConfig
from pbn.infrastructure.config_loader import load_config
from pbn.models import InputImage, Palette
from tools import benchmark_outline_simplification


def test_benchmark_cases_cover_all_performance_images() -> None:
    assert benchmark_outline_simplification.BENCHMARK_CASES == (
        "simple_smaller",
        "simple",
        "medium_smaller",
        "medium",
        "complex_smaller",
        "complex",
    )


def test_the_profile_supplies_the_colour_distance() -> None:
    """
    The benchmark used to override the loaded profile's colour distance with
    a constant of its own, and a test asserted that constant against itself,
    which detects an edit to the constant but never a disagreement with the
    shipped profile.
    """
    assert (
        load_config(
            benchmark_outline_simplification.REPOSITORY_ROOT
            / "config"
            / "example.toml",
        ).color_distance
        == "delta_e_2000"
    )


def test_the_loaded_profile_keeps_its_generation_policy() -> None:
    """
    Only the palette is overridden, so the colour distance the benchmark
    runs is the one the profile ships.
    """
    _, _, config = benchmark_outline_simplification.load_case(
        "simple_smaller",
    )

    profile = load_config(
        benchmark_outline_simplification.REPOSITORY_ROOT / "config" / "example.toml",
    )

    assert config.color_distance == profile.color_distance
    assert config.minimum_region_size_mm == profile.minimum_region_size_mm
    assert config.palette == benchmark_outline_simplification.PALETTE_ID


def test_benchmark_uses_established_polychromos_palette() -> None:
    assert benchmark_outline_simplification.PALETTE_ID == "faberCastellPolychromos60"
    assert benchmark_outline_simplification.PALETTE_VERSION == 1


def test_benchmark_result_reports_median_durations() -> None:
    result = benchmark_outline_simplification.BenchmarkResult(
        case="simple",
        disabled_durations_seconds=(
            6.0,
            4.0,
            5.0,
        ),
        enabled_durations_seconds=(
            4.0,
            3.0,
            5.0,
        ),
        disabled_outline_points=1000,
        enabled_outline_points=600,
    )

    assert result.median_disabled_seconds == pytest.approx(
        5.0,
    )
    assert result.median_enabled_seconds == pytest.approx(
        4.0,
    )
    assert result.speedup == pytest.approx(
        1.25,
    )


def test_benchmark_result_reports_outline_point_reduction() -> None:
    result = benchmark_outline_simplification.BenchmarkResult(
        case="simple",
        disabled_durations_seconds=(5.0,),
        enabled_durations_seconds=(4.0,),
        disabled_outline_points=1000,
        enabled_outline_points=600,
    )

    assert result.outline_point_reduction == 400
    assert result.outline_point_reduction_percent == pytest.approx(
        40.0,
    )


def test_measure_generation_toggles_simplification_and_counts_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = cast(
        InputImage,
        object(),
    )
    palette = cast(
        Palette,
        object(),
    )
    base_config = cast(
        GeneratorConfig,
        SimpleNamespace(
            font_size_pt=3,
        ),
    )
    benchmark_config = cast(
        GeneratorConfig,
        SimpleNamespace(
            font_size_pt=3,
        ),
    )
    document = SimpleNamespace(
        outlines=(
            SimpleNamespace(
                points=(
                    (0.0, 0.0),
                    (1.0, 0.0),
                    (1.0, 1.0),
                ),
                hole_rings=(
                    (
                        (0.2, 0.2),
                        (0.4, 0.2),
                    ),
                ),
            ),
            SimpleNamespace(
                points=(
                    (5.0, 5.0),
                    (6.0, 5.0),
                ),
                hole_rings=(),
            ),
        ),
    )

    replacements: list[tuple[object, dict[str, object]]] = []
    generated_configs: list[object] = []

    def fake_replace(
        config: object,
        **changes: object,
    ) -> object:
        replacements.append(
            (
                config,
                changes,
            ),
        )
        return benchmark_config

    loaded_images: list[object] = []
    generated_paths: list[object] = []

    class FakeGeneratorApplication:
        """
        Mirrors the real construction and call signature.

        The previous version of this fake took no constructor arguments
        and a keyword-only `image`. Both had been gone from
        `GeneratorApplication` for some time, and because the fake
        replaced the real class the tool kept passing here while failing
        with a `TypeError` on its first real call.
        `test_the_fake_matches_the_real_generator_application` now pins
        the two together.
        """

        def __init__(
            self,
            progress_reporter: object = None,
            quantization_executor: object = None,
            *,
            image_loader: object,
            overlap_detector: object,
        ) -> None:
            loaded_images.append(
                image_loader,
            )

        def generate(
            self,
            image_path: object,
            palette: object,
            config: object,
        ) -> object:
            generated_paths.append(
                image_path,
            )
            generated_configs.append(
                config,
            )
            return document

    times = iter(
        (
            10.0,
            12.5,
        ),
    )

    monkeypatch.setattr(
        benchmark_outline_simplification,
        "replace",
        fake_replace,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "GeneratorApplication",
        FakeGeneratorApplication,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "build_overlap_detector",
        lambda: object(),
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "perf_counter",
        lambda: next(times),
    )

    duration, outline_points = benchmark_outline_simplification.measure_generation(
        "medium",
        image,
        palette,
        base_config,
        simplification_enabled=True,
    )

    assert replacements == [
        (
            base_config,
            {
                "outline_simplification_enabled": True,
            },
        ),
    ]
    assert generated_configs == [
        benchmark_config,
    ]

    assert generated_paths == [
        benchmark_outline_simplification.case_image_path(
            "medium",
        ),
    ]

    # The decode stays outside the measured region, which is the whole
    # reason the loader is preloaded rather than the real one.
    assert [
        loader.image
        for loader in loaded_images
        if isinstance(
            loader,
            benchmark_outline_simplification.PreloadedImageLoader,
        )
    ] == [
        image,
    ]

    assert duration == pytest.approx(
        2.5,
    )
    assert outline_points == 7


def test_the_fake_matches_the_real_generator_application() -> None:
    """
    A fake that replaces a class cannot detect that the class changed.

    The test above swaps `GeneratorApplication` for a fake, so it kept
    passing while the tool called a signature that no longer existed.
    The failure surfaced only on a real run. Asserted here against the
    real class, which is the part a fake can never cover.
    """
    construction = signature(
        GeneratorApplication.__init__,
    ).parameters

    assert construction["image_loader"].kind is Parameter.KEYWORD_ONLY
    assert construction["overlap_detector"].kind is Parameter.KEYWORD_ONLY

    assert list(
        signature(
            GeneratorApplication.generate,
        ).parameters,
    ) == [
        "self",
        "image_path",
        "palette",
        "config",
    ]


def test_the_preloaded_loader_satisfies_the_loader_port() -> None:
    """
    The benchmark hands its own loader to the real constructor.

    A loader whose signature drifted from the port would fail the same
    way, at the first real run rather than here.
    """
    assert list(
        signature(
            benchmark_outline_simplification.PreloadedImageLoader.load,
        ).parameters,
    ) == list(
        signature(
            ImageLoaderPort.load,
        ).parameters,
    )


def test_run_case_measures_requested_number_of_paired_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = cast(
        InputImage,
        object(),
    )
    palette = cast(
        Palette,
        object(),
    )
    config = cast(
        GeneratorConfig,
        object(),
    )

    calls: list[bool] = []

    disabled_measurements = iter(
        (
            (4.0, 1000),
            (6.0, 1000),
        ),
    )
    enabled_measurements = iter(
        (
            (2.0, 600),
            (3.0, 600),
        ),
    )

    def fake_measure_generation(
        measured_case: object,
        measured_image: object,
        measured_palette: object,
        measured_config: object,
        *,
        simplification_enabled: bool,
    ) -> tuple[float, int]:
        assert measured_case == "simple"
        assert measured_image is image
        assert measured_palette is palette
        assert measured_config is config

        calls.append(
            simplification_enabled,
        )

        if simplification_enabled:
            return next(
                enabled_measurements,
            )

        return next(
            disabled_measurements,
        )

    monkeypatch.setattr(
        benchmark_outline_simplification,
        "measure_generation",
        fake_measure_generation,
    )

    result = benchmark_outline_simplification.run_case(
        "simple",
        image,
        palette,
        config,
        runs=2,
    )

    assert calls == [
        False,
        True,
        True,
        False,
    ]
    assert result.case == "simple"
    assert result.disabled_durations_seconds == (
        4.0,
        6.0,
    )
    assert result.enabled_durations_seconds == (
        2.0,
        3.0,
    )
    assert result.disabled_outline_points == 1000
    assert result.enabled_outline_points == 600


def test_run_case_rejects_non_positive_run_count() -> None:
    image = cast(
        InputImage,
        object(),
    )
    palette = cast(
        Palette,
        object(),
    )
    config = cast(
        GeneratorConfig,
        object(),
    )

    with pytest.raises(
        ValueError,
        match="runs must be greater than zero",
    ):
        benchmark_outline_simplification.run_case(
            "simple",
            image,
            palette,
            config,
            runs=0,
        )


def test_load_case_uses_established_benchmark_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_config = object()
    benchmark_config = cast(
        GeneratorConfig,
        object(),
    )
    image = cast(
        InputImage,
        object(),
    )
    palette = cast(
        Palette,
        object(),
    )

    loaded_config_paths: list[object] = []
    loaded_image_paths: list[object] = []
    replacements: list[tuple[object, dict[str, object]]] = []
    palette_requests: list[tuple[str, int]] = []

    def fake_load_config(path: object) -> object:
        loaded_config_paths.append(
            path,
        )
        return loaded_config

    def fake_load_image(
        path: object,
        limits: object = None,
    ) -> InputImage:
        loaded_image_paths.append(
            path,
        )
        return image

    def fake_replace(
        config: object,
        **changes: object,
    ) -> GeneratorConfig:
        replacements.append(
            (
                config,
                changes,
            ),
        )
        return benchmark_config

    class FakePaletteManager:
        def get(
            self,
            palette_id: str,
            version: int,
        ) -> Palette:
            palette_requests.append(
                (
                    palette_id,
                    version,
                ),
            )
            return palette

    monkeypatch.setattr(
        benchmark_outline_simplification,
        "load_config",
        fake_load_config,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "load_image",
        fake_load_image,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "replace",
        fake_replace,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "PaletteManager",
        FakePaletteManager,
    )

    loaded_image, loaded_palette, config = benchmark_outline_simplification.load_case(
        "simple",
    )

    assert loaded_config_paths == [
        (benchmark_outline_simplification.REPOSITORY_ROOT / "config" / "example.toml"),
    ]
    assert loaded_image_paths == [
        (
            benchmark_outline_simplification.REPOSITORY_ROOT
            / "examples"
            / "input"
            / "simple.png"
        ),
    ]
    assert replacements == [
        (
            loaded_config,
            {
                "palette": "faberCastellPolychromos60",
                "palette_version": 1,
            },
        ),
    ]
    assert palette_requests == [
        (
            "faberCastellPolychromos60",
            1,
        ),
    ]
    assert loaded_image is image
    assert loaded_palette is palette
    assert config is benchmark_config


def test_format_result_reports_timing_and_point_effect() -> None:
    result = benchmark_outline_simplification.BenchmarkResult(
        case="simple",
        disabled_durations_seconds=(5.0,),
        enabled_durations_seconds=(4.0,),
        disabled_outline_points=1000,
        enabled_outline_points=600,
    )

    assert benchmark_outline_simplification.format_result(
        result,
    ) == (
        "simple: "
        "disabled=5.000s, "
        "enabled=4.000s, "
        "speedup=1.25x, "
        "points_disabled=1000, "
        "points_enabled=600, "
        "point_reduction=400 (40.00%)"
    )


def test_parser_accepts_run_count() -> None:
    args = benchmark_outline_simplification.build_parser().parse_args(
        [
            "--runs",
            "5",
        ],
    )

    assert args.runs == 5


def test_parser_accepts_single_benchmark_case() -> None:
    args = benchmark_outline_simplification.build_parser().parse_args(
        [
            "--case",
            "medium_smaller",
        ],
    )

    assert args.case == "medium_smaller"


def test_main_runs_all_benchmark_cases(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image = object()
    palette = object()
    config = object()

    loaded_cases: list[str] = []
    run_calls: list[
        tuple[
            str,
            object,
            object,
            object,
            int,
        ]
    ] = []

    first_result = object()
    second_result = object()

    class FakeParser:
        def parse_args(self) -> SimpleNamespace:
            return SimpleNamespace(
                runs=3,
                case=None,
            )

    def fake_load_case(
        case: str,
    ) -> tuple[object, object, object]:
        loaded_cases.append(
            case,
        )
        return (
            image,
            palette,
            config,
        )

    def fake_run_case(
        case: str,
        measured_image: object,
        measured_palette: object,
        measured_config: object,
        *,
        runs: int,
    ) -> object:
        run_calls.append(
            (
                case,
                measured_image,
                measured_palette,
                measured_config,
                runs,
            ),
        )

        if case == "first":
            return first_result

        return second_result

    def fake_format_result(
        result: object,
    ) -> str:
        if result is first_result:
            return "first result"

        return "second result"

    monkeypatch.setattr(
        benchmark_outline_simplification,
        "BENCHMARK_CASES",
        (
            "first",
            "second",
        ),
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "build_parser",
        lambda: FakeParser(),
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "load_case",
        fake_load_case,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "run_case",
        fake_run_case,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "format_result",
        fake_format_result,
    )

    benchmark_outline_simplification.main()

    assert loaded_cases == [
        "first",
        "second",
    ]
    assert run_calls == [
        (
            "first",
            image,
            palette,
            config,
            3,
        ),
        (
            "second",
            image,
            palette,
            config,
            3,
        ),
    ]
    assert capsys.readouterr().out == ("first result\n" "second result\n")


def test_main_runs_only_selected_benchmark_case(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image = object()
    palette = object()
    config = object()
    result = object()

    loaded_cases: list[str] = []
    run_cases: list[str] = []

    class FakeParser:
        def parse_args(self) -> SimpleNamespace:
            return SimpleNamespace(
                runs=1,
                case="medium_smaller",
            )

    def fake_load_case(
        case: str,
    ) -> tuple[object, object, object]:
        loaded_cases.append(
            case,
        )
        return (
            image,
            palette,
            config,
        )

    def fake_run_case(
        case: str,
        measured_image: object,
        measured_palette: object,
        measured_config: object,
        *,
        runs: int,
    ) -> object:
        assert measured_image is image
        assert measured_palette is palette
        assert measured_config is config
        assert runs == 1

        run_cases.append(
            case,
        )
        return result

    def fake_format_result(
        measured_result: object,
    ) -> str:
        if measured_result is result:
            return "selected result"

        return "unexpected result"

    monkeypatch.setattr(
        benchmark_outline_simplification,
        "build_parser",
        lambda: FakeParser(),
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "load_case",
        fake_load_case,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "run_case",
        fake_run_case,
    )
    monkeypatch.setattr(
        benchmark_outline_simplification,
        "format_result",
        fake_format_result,
    )

    benchmark_outline_simplification.main()

    assert loaded_cases == [
        "medium_smaller",
    ]
    assert run_cases == [
        "medium_smaller",
    ]
    assert capsys.readouterr().out == ("selected result\n")
