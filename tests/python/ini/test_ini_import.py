"""
@file tests/python/ini/test_import.py
@brief Module import and symbol availability tests for lotm.ini.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import types


def test_core_ini_submodule_import() -> None:
    from lotm._core import ini as core_ini

    assert isinstance(core_ini, types.ModuleType)
    assert hasattr(core_ini, "ConstructFile")
    assert hasattr(core_ini, "ConstructLevel")
    assert hasattr(core_ini, "StrDocument")
    assert hasattr(core_ini, "StrEntry")
    assert hasattr(core_ini, "StrParser")
    assert hasattr(core_ini, "IniParseError")
    assert hasattr(core_ini, "load_file")
    assert hasattr(core_ini, "recognize_structure")
    assert hasattr(core_ini, "scan_file_for_errors")
    assert hasattr(core_ini, "parse_buffer")


def test_package_public_interface_and_all_exports() -> None:
    import lotm.ini as ini_pkg

    expected_symbols = {
        "SUPPORTED_EXTENSIONS",
        "AstNode",
        "CommentNode",
        "ConstructFile",
        "ConstructLevel",
        "IncludeNode",
        "IniParseError",
        "StatementNode",
        "StrDocument",
        "StrEntry",
        "StrParser",
        "UnwrappedAstNode",
        "iter_unwrapped_items",
        "load_file",
        "parse_buffer",
        "parse_ini_file",
        "parse_str_file",
        "recognize_structure",
        "scan_directory_for_errors",
        "scan_file_for_errors",
        "unwrap_node",
    }

    assert set(ini_pkg.__all__) == expected_symbols
    for symbol in expected_symbols:
        assert hasattr(ini_pkg, symbol), f"Symbol {symbol} missing in lotm.ini"


def test_ini_cli_module_import() -> None:
    import lotm.ini.ini_cli as cli_mod

    assert hasattr(cli_mod, "main")
    assert hasattr(cli_mod, "cli_entry")
    assert hasattr(cli_mod, "build_parser")
    assert hasattr(cli_mod, "EXIT_SUCCESS")
    assert hasattr(cli_mod, "EXIT_ERROR")
    assert hasattr(cli_mod, "EXIT_PARSE_FAILURE")
