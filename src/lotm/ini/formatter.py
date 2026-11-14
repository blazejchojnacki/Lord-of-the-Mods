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
IniParseError = _ini.IniParseError


def format_ini(
    file_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str] | None = None,
    *,
    strict: bool = False,
    file_content: str | Buffer | None = None,
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
    >>> text = format_ini("Armor.ini", file_content="Armor A\\nArmor = DEFAULT 10%\\nEnd\\n")
    >>> "    Armor = DEFAULT 10%" in text
    True
    """
    doc = ConstructFile(os.fspath(file_path), strict, file_content)
    formatted = doc.print()
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
