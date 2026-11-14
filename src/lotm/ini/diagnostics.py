"""
@file src/lotm/ini/diagnostics.py
@brief Structural scanning and AST inspection utilities for SAGE .ini, .inc, and .str files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
from collections.abc import Buffer
from dataclasses import dataclass, field
from pathlib import Path

from lotm._core import ini as _ini
from .parser import SUPPORTED_EXTENSIONS, RootItem

ConstructFile = _ini.ConstructFile
ConstructLevel = _ini.ConstructLevel
IncludeNode = _ini.IncludeNode
IniParseError = _ini.IniParseError
ScriptNode = _ini.ScriptNode
StrEntry = _ini.StrEntry


@dataclass(frozen=True)
class IniInspectionReport:
    """
    Structured summary of a parsed SAGE .ini, .inc, or .str document.

    Attributes
    ----------
    file_path : Path
        Path to the inspected configuration document.
    file_type : str
        Normalized lowercase file extension ('.ini', '.inc', or '.str').
    start_level : int
        Recognized starting nesting depth (0 for top-level files, >=0 for .inc).
    define_count : int
        Number of top-level #define macro directives.
    include_count : int
        Total number of #include directives across all nesting levels.
    total_top_level_items : int
        Number of root-level AST nodes or StrEntry items.
    block_counts : dict[str, int]
        Frequency map of top-level ConstructLevel classes or StrEntry categories.
    errors : list[str]
        List of structural or delimiter mismatch diagnostics.
    """

    file_path: Path
    file_type: str
    start_level: int
    define_count: int
    include_count: int
    total_top_level_items: int
    block_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def scan_ini(
    target_path: str | os.PathLike[str],
    *,
    strict: bool = False,
) -> dict[Path, list[str]]:
    """
    Scan a configuration file or directory tree for delimiter and nesting errors.

    Parameters
    ----------
    target_path : str | os.PathLike[str]
        File path or root directory to scan recursively for .ini, .inc, and .str files.
    strict : bool, default=False
        If True, raises IniParseError on the first file containing errors.

    Returns
    -------
    dict[Path, list[str]]
        Mapping of file paths to their list of diagnostic error strings (empty list if clean).

    Raises
    ------
    IniParseError
        If `target_path` does not exist or if `strict` is True and a scanned file
        contains structural errors.

    Examples
    --------
    >>> results = scan_ini("data/ini")  # doctest: +SKIP
    """
    target = Path(target_path)
    if not target.exists():
        raise IniParseError(f"Target path does not exist: {target}")

    if target.is_file():
        candidates = [target]
    else:
        candidates = sorted(
            p
            for p in target.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    report: dict[Path, list[str]] = {}
    for file_path in candidates:
        if strict:
            doc = ConstructFile(str(file_path), True)
            report[file_path] = list(doc.errors)
        else:
            report[file_path] = list(_ini.scan_file_for_errors(str(file_path)))

    return report


def _count_includes_iterative(items: list[RootItem]) -> int:
    """Count IncludeNode instances iteratively across an AST item list."""
    count = 0
    stack: list[RootItem] = list(items)
    while stack:
        node = stack.pop()
        if isinstance(node, IncludeNode):
            count += 1
        elif isinstance(node, ConstructLevel):
            stack.extend(node.items)
    return count


def inspect_ini(
    file_path: str | os.PathLike[str],
    *,
    strict: bool = False,
    file_content: str | Buffer | None = None,
) -> IniInspectionReport:
    """
    Inspect a SAGE configuration file and return a structural summary report.

    Parameters
    ----------
    file_path : str | os.PathLike[str]
        Path to the .ini, .inc, or .str file.
    strict : bool, default=False
        If True, raises IniParseError if structural errors are present.
    file_content : str | Buffer | None, default=None
        Optional in-memory string or binary buffer protocol object.

    Returns
    -------
    IniInspectionReport
        Structural breakdown of blocks, directives, and diagnostics.

    Raises
    ------
    IniParseError
        If the file cannot be parsed or if `strict` is True and structural errors exist.

    Examples
    --------
    >>> report = inspect_ini("Weapon.ini", file_content="Weapon Bow\\nEnd\\n")
    >>> report.block_counts["Weapon"]
    1
    """
    path_obj = Path(file_path)
    doc = ConstructFile(os.fspath(path_obj), strict, file_content)
    top_items = doc.items

    block_counts: dict[str, int] = {}
    for item in top_items:
        if isinstance(item, ConstructLevel):
            key = item._class or "<AnonymousBlock>"
            block_counts[key] = block_counts.get(key, 0) + 1
        elif isinstance(item, StrEntry):
            key = item.category or "<Uncategorized>"
            block_counts[key] = block_counts.get(key, 0) + 1
        elif isinstance(item, ScriptNode):
            block_counts["BeginScript"] = block_counts.get("BeginScript", 0) + 1

    return IniInspectionReport(
        file_path=path_obj,
        file_type=path_obj.suffix.lower() or ".ini",
        start_level=doc.start_level,
        define_count=len(doc.defines),
        include_count=_count_includes_iterative(top_items),
        total_top_level_items=len(top_items),
        block_counts=block_counts,
        errors=list(doc.errors),
    )
