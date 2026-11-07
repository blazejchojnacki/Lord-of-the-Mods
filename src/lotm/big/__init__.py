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
ProgressReport = big.ProgressReport
BigDiff = big.BigDiff
BigDiffResult = big.BigDiffResult
BigOverlay = big.BigOverlay
BigOverlayEntry = big.BigOverlayEntry
BigArchiveError = big.BigArchiveError
BigFormatError = big.BigFormatError
BigSecurityError = big.BigSecurityError

from .differ import create_patch, create_patch_to_memory, diff
from .overlay import load_overlay
from .packer import pack, pack_to_memory
from .unpacker import unpack

__all__ = [
    "BigArchive",
    "BigPacker",
    "BigEntry",
    "ProgressReport",
    "BigDiff",
    "BigDiffResult",
    "BigOverlay",
    "BigOverlayEntry",
    "BigArchiveError",
    "BigFormatError",
    "BigSecurityError",
    "create_patch",
    "create_patch_to_memory",
    "diff",
    "load_overlay",
    "pack",
    "pack_to_memory",
    "unpack",
]
