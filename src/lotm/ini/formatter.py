"""
@file src/lotm/ini/formatter.py
@brief Formatting and atomic serialization utilities for SAGE .ini, .inc, and .str files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
from collections.abc import Buffer
from pathlib import Path

from lotm._core import ini as _ini

ConstructFile = _ini.ConstructFile
FormatOptions = _ini.FormatOptions
IniParseError = _ini.IniParseError


def format_ini(
    file_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str] | None = None,
    *,
    strict: bool = False,
    file_content: str | Buffer | None = None,
    options: FormatOptions | None = None,
    enforce_equals: bool = False,
    normalize_end_tokens: bool = False,
    normalize_header_spacing: bool = False,
    normalize_statement_equals: bool = False,
    normalize_comments: bool = False,
    coalesce_blank_lines: bool = False,
) -> str:
    """
    Parse and format a SAGE .ini, .inc, or .str file with configurable serialization rules.

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
    options : FormatOptions | None, default=None
        Optional pre-configured FormatOptions instance. Individual boolean keyword toggles
        are OR-merged onto `options` when supplied.
    enforce_equals : bool, default=False
        If True, emits canonical `=` for delimiters that canonically expect `=`.
    normalize_end_tokens : bool, default=False
        If True, normalizes block and entry closing keywords (`END`, `end`, `ENd`) to
        canonical `"End"` and script closures to `"EndScript"`.
    normalize_header_spacing : bool, default=False
        If True, normalizes whitespace in block headers (`_class`, `name`, `identifier`,
        and `BeginScript` headers).
    normalize_statement_equals : bool, default=False
        If True, normalizes spacing around `=` in key-value statements to `Key = Value`.
    normalize_comments : bool, default=False
        If True, normalizes comment prefixes (`//` or `;`) to canonical `; `.
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
    effective_opts = FormatOptions(
        indent=options.indent if options is not None else _ini.LEVEL_INDENT,
        enforce_equals=bool(options.enforce_equals if options is not None else False) or enforce_equals,
        normalize_end_tokens=bool(options.normalize_end_tokens if options is not None else False) or normalize_end_tokens,
        normalize_header_spacing=bool(options.normalize_header_spacing if options is not None else False) or normalize_header_spacing,
        normalize_statement_equals=bool(options.normalize_statement_equals if options is not None else False) or normalize_statement_equals,
        normalize_comments=bool(options.normalize_comments if options is not None else False) or normalize_comments,
        coalesce_blank_lines=bool(options.coalesce_blank_lines if options is not None else False) or coalesce_blank_lines,
    )
    formatted = doc.print(effective_opts)

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
