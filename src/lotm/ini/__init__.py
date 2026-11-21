"""
@file src/lotm/ini/__init__.py
@brief Unified public API for SAGE INI, INC, and STR configuration features.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from lotm._core import ini

LEVEL_INDENT = ini.LEVEL_INDENT
INI_ENDS = ini.INI_ENDS
MAX_INI_DEPTH = ini.MAX_INI_DEPTH
MAX_INI_FILE_SIZE = ini.MAX_INI_FILE_SIZE
SAGE_MAX_BLOCK_NAME_LEN = ini.SAGE_MAX_BLOCK_NAME_LEN
SAGE_MAX_IDENTIFIER_LEN = ini.SAGE_MAX_IDENTIFIER_LEN
IniParseError = ini.IniParseError
FormatOptions = ini.FormatOptions
CommentNode = ini.CommentNode
StatementNode = ini.StatementNode
IncludeNode = ini.IncludeNode
DefineNode = ini.DefineNode
ScriptNode = ini.ScriptNode
ConstructLevel = ini.ConstructLevel
StrEntry = ini.StrEntry
StrDocument = ini.StrDocument
StrParser = ini.StrParser
ConstructFile = ini.ConstructFile
validate_include = ini.validate_include
load_file = ini.load_file
scan_file_for_errors = ini.scan_file_for_errors

from .diagnostics import IniInspectionReport, inspect_ini, scan_ini
from .formatter import format_ini
from .parser import (
    SUPPORTED_EXTENSIONS,
    AstNode,
    RootItem,
    parse_ini,
    parse_str,
    recognize_structure,
)

__all__ = [
    "LEVEL_INDENT",
    "INI_ENDS",
    "MAX_INI_DEPTH",
    "MAX_INI_FILE_SIZE",
    "SAGE_MAX_BLOCK_NAME_LEN",
    "SAGE_MAX_IDENTIFIER_LEN",
    "SUPPORTED_EXTENSIONS",
    "IniParseError",
    "FormatOptions",
    "CommentNode",
    "StatementNode",
    "IncludeNode",
    "DefineNode",
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
]
