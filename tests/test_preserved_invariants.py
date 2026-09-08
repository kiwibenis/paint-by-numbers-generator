# SPDX-FileCopyrightText: 2026 kiwibenis
# SPDX-License-Identifier: AGPL-3.0-only
# Additional terms under AGPL-3.0 section 7 apply; see ADDITIONAL-TERMS.md

"""
Mechanical checks for the properties ADR-0002 requires of the source.

These properties hold today. They are the kind that a later change breaks
without anything failing, because nothing in the program depends on them
being true. The checks exist so that breaking one is a decision rather
than an accident.

What can be checked here is the shape of the source, not its behavior.
Where an invariant is only partly mechanical, the test says so rather
than pretending to cover it.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

_SOURCE_ROOT = Path("src")

_FORBIDDEN_CALLS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
    },
)

_FORBIDDEN_ATTRIBUTE_CALLS = frozenset(
    {
        "system",
        "popen",
        "execv",
        "execve",
        "fork",
        "forkpty",
        "spawnl",
        "spawnv",
        "mktemp",
    },
)

_FORBIDDEN_IMPORTS = frozenset(
    {
        # Command execution.
        "subprocess",
        # Deserialization of anything but internally produced data.
        "pickle",
        "marshal",
        "shelve",
        "dbm",
        # Network access.
        "socket",
        "ssl",
        "urllib",
        "http",
        "requests",
        "httpx",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "telnetlib",
        "xmlrpc",
        "webbrowser",
        # Native code loading.
        "ctypes",
    },
)

_CONFIGURATION_PARSERS = frozenset(
    {
        "yaml",
        "configparser",
        "pickle",
    },
)

_XML_PARSER_PREFIXES = (
    "xml.etree",
    "xml.dom",
    "xml.sax",
    "xml.parsers",
)

_CPU_COUNT_MODULES = frozenset(
    {
        "src/pbn/application/generator_application.py",
    },
)

_WRITING_MODULES = frozenset(
    {
        "src/pbn/cli/main.py",
    },
)
"""
The modules permitted to write to the file system.

One, holding one call. Generation returns the document as bytes and the
command line writes it to the configured path, so there is a single
place where output reaches a disk and a single path to reason about.
"""

_WRITING_METHODS = frozenset(
    {
        "write_bytes",
        "write_text",
        "touch",
        "mkdir",
        "rename",
        "replace",
        "unlink",
        "rmdir",
        "symlink_to",
        "hardlink_to",
        "chmod",
    },
)
"""
Path methods that write, named unambiguously enough to check.

`save`, `remove` and `write` are deliberately absent. Each is a method
name shared with objects that touch nothing: a canvas saving into a
buffer, a set discarding a member, a port returning bytes. Including
them would produce findings that have to be waived, and a check with
waivers stops being read.
"""

_WRITING_MODULE_FUNCTIONS = {
    "os": frozenset(
        {
            "makedirs",
            "remove",
            "unlink",
            "rmdir",
            "rename",
            "replace",
            "mkdir",
            "open",
        },
    ),
    "shutil": frozenset(
        {
            "copy",
            "copy2",
            "copyfile",
            "copytree",
            "move",
            "rmtree",
        },
    ),
}
"""
Writing functions reached through their module, which disambiguates
the names that are otherwise too common to check.
"""

_WRITING_OPEN_MODES = ("w", "a", "x", "+")


def _source_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            _SOURCE_ROOT.rglob("*.py"),
        ),
    )


def _parsed() -> Iterator[tuple[Path, ast.Module]]:
    for path in _source_files():
        yield path, ast.parse(
            path.read_text(
                encoding="utf-8",
            ),
        )


def _imported_modules(
    tree: ast.Module,
) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name

        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def _imported_roots(
    tree: ast.Module,
) -> Iterator[str]:
    for module in _imported_modules(tree):
        yield module.split(".")[0]


def test_the_source_tree_is_not_empty() -> None:
    """
    A guard for the checks below, which pass trivially on nothing.
    """
    assert len(_source_files()) > 50


def test_no_dynamic_code_execution() -> None:
    offenders = [
        f"{path}:{node.lineno} {node.func.id}"
        for path, tree in _parsed()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FORBIDDEN_CALLS
    ]

    assert offenders == []


def test_no_process_or_temporary_file_calls() -> None:
    offenders = [
        f"{path}:{node.lineno} {node.func.attr}"
        for path, tree in _parsed()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _FORBIDDEN_ATTRIBUTE_CALLS
    ]

    assert offenders == []


def test_no_shell_keyword_anywhere() -> None:
    offenders = [
        f"{path}:{node.lineno}"
        for path, tree in _parsed()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "shell"
    ]

    assert offenders == []


def test_no_forbidden_imports() -> None:
    """
    Covers command execution, deserialization, network and native code.
    """
    offenders = [
        f"{path}: {root}"
        for path, tree in _parsed()
        for root in _imported_roots(tree)
        if root in _FORBIDDEN_IMPORTS
    ]

    assert offenders == []


def test_configuration_is_parsed_with_tomllib_only() -> None:
    """
    `tomllib` cannot execute code. The alternatives can.
    """
    configuration_module = _SOURCE_ROOT / "pbn" / "infrastructure" / "config_loader.py"
    tree = ast.parse(
        configuration_module.read_text(
            encoding="utf-8",
        ),
    )
    roots = set(
        _imported_roots(tree),
    )

    assert "tomllib" in roots
    assert not (roots & _CONFIGURATION_PARSERS)


def test_no_module_parses_configuration_with_another_library() -> None:
    offenders = [
        f"{path}: {root}"
        for path, tree in _parsed()
        for root in _imported_roots(tree)
        if root in _CONFIGURATION_PARSERS
    ]

    assert offenders == []


def test_no_xml_parser_is_imported() -> None:
    """
    The XML parsers carry entity expansion and external entity exposure.

    The check names parser modules rather than the complete `xml` package
    because that package also contains helpers that do not parse input.

    Production source requires no XML parser, so parser-module imports are
    rejected without exemptions.
    """
    offenders = [
        f"{path}: {module}"
        for path, tree in _parsed()
        for module in _imported_modules(tree)
        if module.startswith(_XML_PARSER_PREFIXES)
    ]

    assert offenders == []


def test_worker_counts_come_from_one_place() -> None:
    """
    Worker counts derive from configuration and available CPUs only.

    The mechanical half is that the CPU count is read in one module. That
    it is not derived from input data is a property of that module's code
    and is not checked here.
    """
    offenders = [
        str(path)
        for path, tree in _parsed()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "cpu_count"
        and str(path).replace("\\", "/") not in _CPU_COUNT_MODULES
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "path",
    _source_files(),
    ids=str,
)
def test_broad_exception_handlers_reraise(
    path: Path,
) -> None:
    """
    ADR-0002 permits a broad handler only if it re-raises as a project
    error. A handler that swallows would hide exactly the failures the
    disclosure boundary of ADR-0019 is meant to classify.
    """
    tree = ast.parse(
        path.read_text(
            encoding="utf-8",
        ),
    )

    offenders = [
        f"{path}:{handler.lineno}"
        for handler in ast.walk(tree)
        if isinstance(handler, ast.ExceptHandler)
        and _is_broad(handler)
        and not any(isinstance(node, ast.Raise) for node in ast.walk(handler))
    ]

    assert offenders == []


def _is_broad(
    handler: ast.ExceptHandler,
) -> bool:
    if handler.type is None:
        return True

    if isinstance(handler.type, ast.Name):
        return handler.type.id in {
            "Exception",
            "BaseException",
        }

    return False


def test_the_source_never_imports_the_developer_tools() -> None:
    """
    The checks above cover `src` only.

    `tools` holds developer tooling that is never shipped and may use
    what the application must not, such as `subprocess` for measuring a
    run in its own process. That exemption only holds while nothing in
    `src` reaches into it.
    """
    offenders = [
        f"{path}: {root}"
        for path, tree in _parsed()
        for root in _imported_roots(tree)
        if root == "tools"
    ]

    assert offenders == []


def test_no_absolute_paths_are_written_into_the_source() -> None:
    """
    A hard-coded output location would leave the configured one.
    """
    offenders = [
        f"{path}:{node.lineno}"
        for path, tree in _parsed()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and (
            node.value.startswith("/tmp")
            or node.value.startswith("/var")
            or node.value.startswith("C:\\")
        )
    ]

    assert offenders == []


def _open_mode(
    node: ast.Call,
) -> str | None:
    """
    Return the mode an `open` call requests, if it is a literal.
    """
    if node.args and isinstance(node.args[0], ast.Constant):
        first = node.args[0].value

        if isinstance(first, str) and not isinstance(
            node.func,
            ast.Name,
        ):
            return first

    if (
        len(node.args) > 1
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return node.args[1].value

    for keyword in node.keywords:
        if (
            keyword.arg == "mode"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ):
            return keyword.value.value

    return None


def _writes(
    tree: ast.Module,
) -> Iterator[tuple[int, str]]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func

        if isinstance(function, ast.Attribute):
            if function.attr in _WRITING_METHODS:
                yield node.lineno, f".{function.attr}()"
                continue

            if isinstance(
                function.value, ast.Name
            ) and function.attr in _WRITING_MODULE_FUNCTIONS.get(
                function.value.id,
                frozenset(),
            ):
                yield (
                    node.lineno,
                    f"{function.value.id}.{function.attr}()",
                )
                continue

        name = (
            function.attr
            if isinstance(function, ast.Attribute)
            else function.id if isinstance(function, ast.Name) else None
        )

        if name != "open":
            continue

        mode = _open_mode(
            node,
        )

        if mode is not None and any(flag in mode for flag in _WRITING_OPEN_MODES):
            yield node.lineno, f"open({mode!r})"


def test_the_file_system_is_written_from_one_place() -> None:
    """
    Output goes to the configured path and nowhere else.

    The mechanical half is that a write can only occur in one module.
    That the path it writes to is the configured one is a property of
    that module's few lines, and is read rather than checked.

    ADR-0016 keeps security isolation outside the generator. Generation
    therefore has one project-owned output write site to reason about.
    """
    offenders = [
        f"{path}:{line} {what}"
        for path, tree in _parsed()
        if str(path).replace("\\", "/") not in _WRITING_MODULES
        for line, what in _writes(tree)
    ]

    assert offenders == []


def test_the_writing_module_holds_a_single_write() -> None:
    """
    One permitted module is not the same as one write.

    Without this, the check above would pass on a module that wrote to
    several places, which is the thing it exists to prevent.
    """
    writes = [
        f"{path}:{line} {what}"
        for path, tree in _parsed()
        if str(path).replace("\\", "/") in _WRITING_MODULES
        for line, what in _writes(tree)
    ]

    assert len(writes) == 1, writes
