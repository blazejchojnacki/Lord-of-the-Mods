"""
@file src/lotm/ini/formatter.py
@brief Formatting and atomic serialization utilities for SAGE .ini, .inc, and .str files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
import re
from collections.abc import Buffer
from pathlib import Path

from lotm._core import ini as _ini
from .parser import RootItem

ConstructFile = _ini.ConstructFile
ConstructLevel = _ini.ConstructLevel
IniParseError = _ini.IniParseError
ScriptNode = _ini.ScriptNode
StrEntry = _ini.StrEntry


def _normalize_ast(
    doc: ConstructFile,
    *,
    normalize_end_tokens: bool,
    normalize_header_spacing: bool,
) -> None:
    """Apply in-place closure token and header spacing normalizations across a ConstructFile AST."""
    stack: list[RootItem] = list(doc)
    while stack:
        node = stack.pop()
        if isinstance(node, ConstructLevel):
            if normalize_end_tokens and node.end_token.lower() == "end":
                node.end_token = "End"
            if normalize_header_spacing:
                node._class = " ".join(node._class.split())
                node.name = " ".join(node.name.split())
                node.identifier = " ".join(node.identifier.split())
            stack.extend(node)
        elif isinstance(node, ScriptNode):
            if normalize_end_tokens and node.end_token.lower() == "endscript":
                node.end_token = "EndScript"
            if normalize_header_spacing:
                node.name = "BeginScript"
                node.identifier = " ".join(node.identifier.split())
        elif isinstance(node, StrEntry):
            if normalize_end_tokens and node.end_token.lower() == "end":
                node.end_token = "End"
            if normalize_header_spacing:
                node.category = " ".join(node.category.split())
                node.identifier = " ".join(node.identifier.split())


def format_ini(
    file_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str] | None = None,
    *,
    strict: bool = False,
    file_content: str | Buffer | None = None,
    normalize_end_tokens: bool = False,
    normalize_header_spacing: bool = False,
    coalesce_blank_lines: bool = False,
) -> str:
    """
    Parse and format a SAGE .ini, .inc, or .str file with normalized 4-space indentation.

    Parameters
    ----------
    file_path : str | os.PathLike[str]
        Source configuration file path.
    output_path : str | os.PathLike[str] | None, default=None
        Optional destination path to write the formatted text atomically.
    strict : bool, default=False
        If True, raises IniParseError if structural errors are encountered.
    file_content : str | Buffer | None, default=None
        Optional in-memory string or binary buffer protocol object.
    normalize_end_tokens : bool, default=False
        If True, normalizes block and entry closing keywords (`END`, `end`, `ENd`) to
        canonical `"End"` and script closures to `"EndScript"`.
    normalize_header_spacing : bool, default=False
        If True, normalizes whitespace in block headers (`_class`, `name`, `identifier`,
        and `BeginScript` headers).
    coalesce_blank_lines : bool, default=False
        If True, collapses runs of multiple consecutive blank lines into a single blank line.

    Returns
    -------
    str
        Formatted configuration text.

    Raises
    ------
    IniParseError
        If parsing fails or strict mode detects delimiter or level mismatches.
    OSError
        If writing or atomically replacing `output_path` fails.

    Examples
    --------
    >>> text = format_ini("Armor.ini", file_content="Armor A\\nArmor = DEFAULT 10%\\nEND\\n", normalize_end_tokens=True)
    >>> text.endswith("End\\n\\n")
    True
    """
    doc = ConstructFile(os.fspath(file_path), strict, file_content)
    if normalize_end_tokens or normalize_header_spacing:
        _normalize_ast(
            doc,
            normalize_end_tokens=normalize_end_tokens,
            normalize_header_spacing=normalize_header_spacing,
        )
    formatted = doc.print()
    if coalesce_blank_lines:
        formatted = re.sub(r"\n{3,}", "\n\n", formatted)

    if output_path is not None:
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_dest = dest.with_name(f".{dest.name}.lotm_tmp")
        try:
            tmp_dest.write_text(formatted, encoding="utf-8")
            os.replace(tmp_dest, dest)
        except BaseException:
            tmp_dest.unlink(missing_ok=True)
            raise
    return formatted
