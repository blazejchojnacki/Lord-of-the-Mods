"""
@file tests/python/ini/test_ini_import.py
@brief Public namespace and C++ extension binding import tests for lotm.ini.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import lotm
import lotm._core as _core
import lotm.ini as ini


def test_core_ini_submodule_exists() -> None:
    """Verify that the private C++ extension exposes the ini submodule and top-level lotm exports ini."""
    assert hasattr(_core, "ini")
    assert hasattr(lotm, "ini")
    assert "ini" in lotm.__all__


def test_public_ini_exports_all_symbols() -> None:
    """Verify that every symbol declared in lotm.ini.__all__ is present and bound."""
    expected_exports = {
        "LEVEL_INDENT",
        "INI_ENDS",
        "MAX_INI_DEPTH",
        "SUPPORTED_EXTENSIONS",
        "IniParseError",
        "CommentNode",
        "StatementNode",
        "IncludeNode",
        "ScriptNode",
        "ConstructLevel",
        "StrEntry",
        "StrDocument",
        "StrParser",
        "ConstructFile",
        "AstNode",
        "RootItem",
        "IniInspectionReport",
        "recognize_structure",
        "validate_include",
        "load_file",
        "scan_file_for_errors",
        "parse_ini",
        "parse_str",
        "format_ini",
        "scan_ini",
        "inspect_ini",
    }
    assert set(ini.__all__) == expected_exports
    for symbol in expected_exports:
        assert hasattr(ini, symbol), f"Missing export: {symbol}"


def test_constants_and_exception_inheritance() -> None:
    """Verify module constants and that IniParseError inherits from ValueError."""
    assert ini.LEVEL_INDENT == "    "
    assert ini.INI_ENDS == ("End", "END", "end")
    assert ini.MAX_INI_DEPTH == 16
    assert _core.ini.MAX_INI_FILE_SIZE == 64 * 1024 * 1024
    assert _core.ini.SAGE_MAX_BLOCK_NAME_LEN == 256
    assert _core.ini.SAGE_MAX_IDENTIFIER_LEN == 512
    assert ini.SUPPORTED_EXTENSIONS == (".ini", ".inc", ".str")
    assert issubclass(ini.IniParseError, ValueError)
