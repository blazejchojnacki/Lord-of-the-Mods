"""
@file src/lotm/big/_paths.py
@brief Internal virtual archive path helpers for EA BIG4 entries.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations


def _to_big_path(entry_name: str) -> str:
    """Normalize virtual archive directory separators to EA BIG4 backslashes."""
    return entry_name.replace("/", "\\")


def _normalize_entry_path(entry_name: str) -> str:
    """Normalize a virtual archive entry path for case-insensitive extension matching."""
    return entry_name.replace("\\", "/").lower()
