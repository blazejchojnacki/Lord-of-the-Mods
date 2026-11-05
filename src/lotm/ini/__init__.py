"""
@file src/lotm/ini/__init__.py
@brief Public package interface for lotm.ini parsing utilities.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from lotm.ini.parser import (
     SUPPORTED_EXTENSIONS,
    AstNode,
    CommentNode,
    ConstructFile,
    ConstructLevel,
    IncludeNode,
    IniParseError,
    StatementNode,
    StrDocument,
    StrEntry,
    StrParser,
    UnwrappedAstNode,
    iter_unwrapped_items,
    load_file,
    parse_buffer,
    parse_ini_file,
    parse_str_file,
    recognize_structure,
    scan_directory_for_errors,
    scan_file_for_errors,
    unwrap_node,
)

__all__ = [
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
]
