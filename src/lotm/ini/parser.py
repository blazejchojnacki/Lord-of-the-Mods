"""
@file src/lotm/ini/parser.py
@brief High-level Python library API for SAGE .ini, .inc, and .str parsing.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TypeAlias

from lotm._core import ini as _ini

IniParseError = _ini.IniParseError
StatementNode = _ini.StatementNode
CommentNode = _ini.CommentNode
IncludeNode = _ini.IncludeNode
AstNode = _ini.AstNode
StrEntry = _ini.StrEntry
StrDocument = _ini.StrDocument
ConstructLevel = _ini.ConstructLevel
ConstructFile = _ini.ConstructFile
StrParser = _ini.StrParser
parse_buffer = _ini.parse_buffer

UnwrappedAstNode: TypeAlias = (
    StatementNode | CommentNode | IncludeNode | ConstructLevel | StrEntry
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".ini", ".inc", ".str"})


def unwrap_node(node: AstNode | UnwrappedAstNode) -> UnwrappedAstNode:
    """
    Unwrap a C++ AstNode wrapper into its underlying native AST node instance.

    Parameters
    ----------
    node : AstNode | UnwrappedAstNode
        The wrapped AstNode or an already unwrapped node.

    Returns
    -------
    UnwrappedAstNode
        The underlying StatementNode, CommentNode, IncludeNode, ConstructLevel, or StrEntry.

    Examples
    --------
    >>> raw = AstNode(StatementNode("Side = Mordor"))
    >>> inner = unwrap_node(raw)
    >>> inner.text
    'Side = Mordor'
    """
    if isinstance(node, AstNode):
        return node.value
    return node


def iter_unwrapped_items(
    container: ConstructFile | ConstructLevel,
) -> Iterator[UnwrappedAstNode]:
    """
    Yield unwrapped child AST nodes from a ConstructFile or ConstructLevel.

    Parameters
    ----------
    container : ConstructFile | ConstructLevel
        A parsed file or block container holding AstNode items.

    Yields
    ------
    UnwrappedAstNode
        Each child node unwrapped from its AstNode variant container.
    """
    for item in container.items:
        yield unwrap_node(item)


def parse_ini_file(file_path: str | Path, strict: bool = False) -> ConstructFile:
    """
    Parse a SAGE .ini, .inc, or .str file into a ConstructFile AST.

    Parameters
    ----------
    file_path : str | Path
        Path to the configuration file.
    strict : bool, default=False
        If True, raises IniParseError immediately upon encountering delimiter mismatches.

    Returns
    -------
    ConstructFile
        The constructed syntax tree and metadata for the file.

    Raises
    ------
    IniParseError
        If the file does not exist, has an unsupported extension, or fails strict parsing.
    """
    return ConstructFile(Path(file_path), strict)


def parse_str_file(file_path: str | Path, strict: bool = False) -> StrDocument:
    """
    Parse a SAGE .str localization file into a StrDocument AST.

    Parameters
    ----------
    file_path : str | Path
        Path to the .str file.
    strict : bool, default=False
        If True, raises IniParseError on unmatched closing keywords.

    Returns
    -------
    StrDocument
        Parsed string localization document.

    Raises
    ------
    IniParseError
        If the file is invalid or fails strict delimiter checks.
    """
    return StrParser.parse_file(Path(file_path), strict)


def load_file(file_path: str | Path) -> tuple[str, list[list[str]]]:
    """
    Load and format a SAGE configuration or text file.

    Parameters
    ----------
    file_path : str | Path
        Path to a .ini, .inc, .str, or .txt file.

    Returns
    -------
    tuple[str, list[list[str]]]
        A tuple of (formatted_content, delimiter_hierarchy).
    """
    return _ini.load_file(Path(file_path))


def recognize_structure(file_path: str | Path) -> tuple[list[list[str]], int]:
    """
    Detect the delimiter hierarchy and starting nesting level of a SAGE file.

    Parameters
    ----------
    file_path : str | Path
        Path to the file to inspect.

    Returns
    -------
    tuple[list[list[str]], int]
        A tuple of (delimiters_by_level, start_level).
    """
    return _ini.recognize_structure(Path(file_path))


def scan_file_for_errors(file_path: str | Path) -> list[str]:
    """
    Scan a single SAGE configuration file for structural or delimiter errors.

    Parameters
    ----------
    file_path : str | Path
        Path to the target file.

    Returns
    -------
    list[str]
        List of diagnostic error messages (empty if no errors were found).
    """
    return _ini.scan_file_for_errors(Path(file_path))


def scan_directory_for_errors(
    target_dir: str | Path,
    extensions: set[str] | frozenset[str] = SUPPORTED_EXTENSIONS,
) -> dict[Path, list[str]]:
    """
    Recursively scan a directory of SAGE configuration files for structural errors.

    Parameters
    ----------
    target_dir : str | Path
        Root directory to scan recursively.
    extensions : set[str] | frozenset[str], default=SUPPORTED_EXTENSIONS
        Set of lowercase file extensions (including leading dot) to include.

    Returns
    -------
    dict[Path, list[str]]
        Mapping of every scanned file path to its list of errors (including clean files
        with empty lists so callers can track total scanned file counts).

    Raises
    ------
    FileNotFoundError
        If target_dir does not exist.
    NotADirectoryError
        If target_dir exists but is not a directory.
    """
    root = Path(target_dir)
    if not root.exists():
        raise FileNotFoundError(f"Target directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {root}")

    normalized_exts = {ext.lower() for ext in extensions}
    candidate_files = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in normalized_exts
    )

    results: dict[Path, list[str]] = {}
    for file_path in candidate_files:
        results[file_path] = scan_file_for_errors(file_path)

    return results
