"""
@file src/lotm/big/__init__.py
@brief Unified public API for BIG archive features.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from lotm._core import big

BigArchive = big.BigArchive
BigPacker = big.BigPacker
BigEntry = big.BigEntry
BigArchiveError = big.BigArchiveError
BigFormatError = big.BigFormatError
BigSecurityError = big.BigSecurityError

from .packer import pack
from .unpacker import unpack

__all__ = [
    "BigArchive",
    "BigPacker",
    "BigEntry",
    "BigArchiveError",
    "BigFormatError",
    "BigSecurityError",
    "pack",
    "unpack",
]
