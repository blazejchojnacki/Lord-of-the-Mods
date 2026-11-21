"""
@file src/lotm/pipeline/stages.py
@brief Pluggable entry transformation stages for the lotm.pipeline archive bridge.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from collections.abc import Buffer, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from lotm.ini import (
    ConstructFile,
    FormatOptions,
    StrDocument,
    parse_ini,
    parse_str,
)


@runtime_checkable
class EntryStage(Protocol):
    """Protocol for modular archive entry transformations across asset formats."""

    def matches(self, entry_name: str) -> bool:
        """Return True if this stage applies to the normalized or raw entry path."""
        ...

    def apply(self, entry_name: str, payload: Buffer, *, strict: bool = False) -> bytes:
        """Transform a raw entry payload buffer into serialized bytes."""
        ...


@dataclass(frozen=True)
class IniAstStage:
    """
    Mutates and serializes `.ini` or `.inc` entries parsed from zero-copy archive buffers.

    Parameters
    ----------
    mutator : Callable[[ConstructFile], None]
        In-place AST mutator invoked on the parsed `ConstructFile`.
    extensions : tuple[str, ...], default=(".ini", ".inc")
        Lowercase filename extensions handled by this stage.
    format_options : FormatOptions | None, default=None
        Optional serialization options passed to `ConstructFile.print()`.
    """

    mutator: Callable[[ConstructFile], None]
    extensions: tuple[str, ...] = (".ini", ".inc")
    format_options: FormatOptions | None = None

    def matches(self, entry_name: str) -> bool:
        """Return True if `entry_name` ends with a configured `.ini`/`.inc` extension."""
        lower = entry_name.replace("\\", "/").lower()
        return any(lower.endswith(ext) for ext in self.extensions)

    def apply(self, entry_name: str, payload: Buffer, *, strict: bool = False) -> bytes:
        """Parse `payload` zero-copy into a `ConstructFile`, mutate it, and return UTF-8 bytes."""
        doc = parse_ini(entry_name, strict=strict, file_content=payload)
        self.mutator(doc)
        rendered = doc.print() if self.format_options is None else doc.print(self.format_options)
        return rendered.encode("utf-8")


@dataclass(frozen=True)
class StrAstStage:
    """
    Mutates and serializes `.str` localization entries parsed from zero-copy archive buffers.

    Parameters
    ----------
    mutator : Callable[[StrDocument], None]
        In-place AST mutator invoked on the parsed `StrDocument`.
    format_options : FormatOptions | None, default=None
        Optional serialization options passed to `StrDocument.print()`.
    """

    mutator: Callable[[StrDocument], None]
    format_options: FormatOptions | None = None

    def matches(self, entry_name: str) -> bool:
        """Return True if `entry_name` ends with `.str` (case-insensitive)."""
        return entry_name.replace("\\", "/").lower().endswith(".str")

    def apply(self, entry_name: str, payload: Buffer, *, strict: bool = False) -> bytes:
        """Parse `payload` zero-copy into a `StrDocument`, mutate it, and return UTF-8 bytes."""
        doc = parse_str(entry_name, strict=strict, file_content=payload)
        self.mutator(doc)
        rendered = doc.print() if self.format_options is None else doc.print(self.format_options)
        return rendered.encode("utf-8")


@dataclass(frozen=True)
class FormatConfigStage:
    """
    Formats `.ini`, `.inc`, or `.str` archive entries using `FormatOptions`.

    Parameters
    ----------
    options : FormatOptions | None, default=None
        Serialization options applied during AST printing.
    extensions : tuple[str, ...], default=(".ini", ".inc", ".str")
        Lowercase filename extensions formatted by this stage.
    """

    options: FormatOptions | None = None
    extensions: tuple[str, ...] = (".ini", ".inc", ".str")

    def matches(self, entry_name: str) -> bool:
        """Return True if `entry_name` has a supported configuration or localization extension."""
        lower = entry_name.replace("\\", "/").lower()
        return any(lower.endswith(ext) for ext in self.extensions)

    def apply(self, entry_name: str, payload: Buffer, *, strict: bool = False) -> bytes:
        """Parse `payload` zero-copy and serialize it with `options` into UTF-8 bytes."""
        lower = entry_name.replace("\\", "/").lower()
        opts = self.options if self.options is not None else FormatOptions()
        if lower.endswith(".str"):
            doc = parse_str(entry_name, strict=strict, file_content=payload)
        else:
            doc = parse_ini(entry_name, strict=strict, file_content=payload)
        return doc.print(opts).encode("utf-8")
