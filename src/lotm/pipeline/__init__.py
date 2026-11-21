"""
@file src/lotm/pipeline/__init__.py
@brief Modular archive-to-AST and asset transformation pipeline for lotm.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from .editor import (
    ArchiveEditor,
    ArchiveHandle,
    ArchiveInput,
    TransformResult,
    transform_archive,
)
from .stages import EntryStage, FormatConfigStage, IniAstStage, StrAstStage

__all__ = [
    "ArchiveEditor",
    "ArchiveHandle",
    "ArchiveInput",
    "EntryStage",
    "FormatConfigStage",
    "IniAstStage",
    "StrAstStage",
    "TransformResult",
    "transform_archive",
]
