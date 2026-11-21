"""
@file src/lotm/ini/parser.py
@brief High-level Python entry points for parsing SAGE .ini, .inc, and .str configuration files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
from collections.abc import Buffer
from typing import TypeAlias

from lotm._core import ini as _ini

CommentNode = _ini.CommentNode
StatementNode = _ini.StatementNode
IncludeNode = _ini.IncludeNode
DefineNode = _ini.DefineNode
ScriptNode = _ini.ScriptNode
ConstructLevel = _ini.ConstructLevel
StrEntry = _ini.StrEntry
StrDocument = _ini.StrDocument
StrParser = _ini.StrParser
ConstructFile = _ini.ConstructFile
IniParseError = _ini.IniParseError

AstNode: TypeAlias = (
    CommentNode | StatementNode | IncludeNode | DefineNode | ScriptNode | ConstructLevel
)
RootItem: TypeAlias = AstNode | StrEntry

SUPPORTED_EXTENSIONS = (".ini", ".inc", ".str")


def recognize_structure(
    file_path: str | os.PathLike[str],
    file_content: str | Buffer | None = None,
) -> tuple[list[list[str]], int]:
    """
    Recognize the delimiter hierarchy and starting nesting depth of a SAGE .ini, .inc, or .str file.

    Parameters
    ----------
    file_path : str | os.PathLike[str]
        Path to the configuration file (used for extension recognition and disk reading
        when `file_content` is `None`).
    file_content : str | Buffer | None, default=None
        Optional in-memory string or binary buffer protocol object (`bytes`, `bytearray`,
        `memoryview`). Reads from disk when `None`.

    Returns
    -------
    tuple[list[list[str]], int]
        A tuple of `(delimiters, start_level)` where `delimiters` is the active schema
        hierarchy by nesting level and `start_level` is the detected starting depth.

    Raises
    ------
    IniParseError
        If `file_content` is `None` and the file cannot be opened or mapped from disk,
        or if the input exceeds `MAX_INI_FILE_SIZE`.

    Examples
    --------
    >>> delims, start_lvl = recognize_structure("Weapon.ini", b"Weapon Sword\\nEnd\\n")
    >>> start_lvl
    0
    >>> "Weapon" in delims[0]
    True
    """
    if isinstance(file_content, Buffer):
        return _ini.recognize_structure_buffer(os.fspath(file_path), file_content)
    return _ini.recognize_structure(os.fspath(file_path), file_content)


def parse_ini(
    file_path: str | os.PathLike[str],
    *,
    strict: bool = False,
    file_content: str | Buffer | None = None,
) -> ConstructFile:
    """
    Parse a SAGE .ini, .inc, or .str configuration file into a ConstructFile AST.

    Parameters
    ----------
    file_path : str | os.PathLike[str]
        Path to the configuration file (used for extension dispatch and diagnostics).
    strict : bool, default=False
        If True, raises IniParseError immediately on unclosed blocks or negative levels.
    file_content : str | Buffer | None, default=None
        Optional in-memory string or binary buffer protocol object (e.g. bytes, memoryview).
        Reads from disk when None.

    Returns
    -------
    ConstructFile
        Parsed root configuration AST.

    Raises
    ------
    IniParseError
        If the file path or extension is invalid, if strict mode detects structural
        mismatches, or if SAGE engine depth/buffer bounds are exceeded.

    Examples
    --------
    >>> doc = parse_ini("Weapon.ini", file_content="Weapon Sword\\n  Damage = 10\\nEnd\\n")
    >>> len(doc)
    1
    """
    return ConstructFile(os.fspath(file_path), strict, file_content)


def parse_str(
    file_path: str | os.PathLike[str],
    *,
    strict: bool = False,
    file_content: str | Buffer | None = None,
) -> StrDocument:
    """
    Parse a SAGE .str localization file into a dedicated StrDocument AST.

    Parameters
    ----------
    file_path : str | os.PathLike[str]
        Path to the .str localization file.
    strict : bool, default=False
        If True, raises IniParseError on unclosed entries or orphaned statements.
    file_content : str | Buffer | None, default=None
        Optional in-memory string or binary buffer protocol object.
        Reads from disk when None.

    Returns
    -------
    StrDocument
        Parsed localization document.

    Raises
    ------
    IniParseError
        If the file extension is not '.str', the file does not exist on disk when
        `file_content` is None, strict mode detects structural errors, or SAGE engine
        buffer bounds are exceeded.

    Examples
    --------
    >>> doc = parse_str("lotr.str", file_content='OBJECT:Unit\\n"Soldier"\\nEnd\\n')
    >>> len(doc.entries)
    1
    """
    if isinstance(file_content, Buffer):
        return _ini.parse_str_buffer(os.fspath(file_path), strict, file_content)
    return StrParser.parse_file(os.fspath(file_path), strict, file_content)
