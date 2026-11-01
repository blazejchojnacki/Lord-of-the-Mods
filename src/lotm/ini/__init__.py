"""
@file src/lotm/ini/__init__.py
@brief SAGE engine text configuration (.ini, .inc, .str) parser prototype.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from .parser import ConstructFile, ConstructLevel, IniParseError, load_file, scan_file_for_errors

__all__ = ["ConstructFile", "ConstructLevel", "IniParseError", "load_file", "scan_file_for_errors"]
