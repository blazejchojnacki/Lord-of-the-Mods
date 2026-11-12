"""
@file src/lotm/_core.pyi
@brief Type stubs for the private C++ native extension core.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections.abc import Buffer, Callable, Iterator, Sequence
import os
from pathlib import Path
from typing import TypeAlias, overload

class big:
    class BigArchiveError(RuntimeError): ...
    class BigFormatError(BigArchiveError): ...
    class BigSecurityError(BigArchiveError): ...

    class ProgressReport:
        @property
        def entry_name(self) -> str: ...
        @property
        def bytes_transferred(self) -> int: ...
        @property
        def file_size(self) -> int: ...
        @property
        def total_bytes_transferred(self) -> int: ...
        @property
        def total_archive_size(self) -> int: ...
        def __repr__(self) -> str: ...

    class BigArchive:
        def __init__(self, file_path: str | os.PathLike[str]) -> None: ...
        @property
        def file_path(self) -> Path: ...
        @property
        def closed(self) -> bool: ...
        def close(self) -> None: ...
        def __enter__(self) -> 'big.BigArchive': ...
        def __exit__(
            self,
            exc_type: object = None,
            exc_val: object = None,
            exc_tb: object = None
        ) -> None: ...
        def read_entry(self, entry: str | os.PathLike[str] | 'big.BigEntry') -> bytes: ...
        def stream_entry(self, entry: str | os.PathLike[str] | 'big.BigEntry', chunk_callback: Callable[[memoryview], bool | None]) -> None: ...
        def extract_all(
            self, 
            output_dir: str | os.PathLike[str], 
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None,
            filter_pattern: str = "",
            create_directories: bool = True
        ) -> None: ...
        def get_entries(self, filter_pattern: str = "") -> list['big.BigEntry']: ...

    class BigEntry:
        @property
        def name(self) -> str: ...
        @property
        def offset(self) -> int: ...
        @property
        def size(self) -> int: ...
        def __eq__(self, other: object) -> bool: ...
        def __lt__(self, other: 'big.BigEntry') -> bool: ...
        def __hash__(self) -> int: ...
        def __repr__(self) -> str: ...

    class BigPacker:
        @staticmethod
        def pack_from_directory(
            source_dir: str | os.PathLike[str], 
            output_file: str | os.PathLike[str], 
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None
        ) -> None: ...
        @staticmethod
        def pack_to_memory(
            source: str | os.PathLike[str] | Sequence[tuple[str, Buffer]],
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None
        ) -> bytes: ...

    class BigDiffResult:
        @property
        def added(self) -> list['big.BigEntry']: ...
        @property
        def removed(self) -> list['big.BigEntry']: ...
        @property
        def modified(self) -> list['big.BigEntry']: ...
        @property
        def unchanged(self) -> list['big.BigEntry']: ...
        @property
        def has_differences(self) -> bool: ...
        def __repr__(self) -> str: ...

    class BigDiff:
        @overload
        @staticmethod
        def compare(
            base: 'big.BigArchive',
            target: 'big.BigArchive',
            filter_pattern: str = ""
        ) -> 'big.BigDiffResult': ...

        @overload
        @staticmethod
        def compare(
            base: str | os.PathLike[str],
            target: str | os.PathLike[str],
            filter_pattern: str = ""
        ) -> 'big.BigDiffResult': ...

        @overload
        @staticmethod
        def create_patch_to_memory(
            base: 'big.BigArchive',
            target: 'big.BigArchive',
            filter_pattern: str = "",
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None
        ) -> bytes: ...

        @overload
        @staticmethod
        def create_patch_to_memory(
            base: str | os.PathLike[str],
            target: str | os.PathLike[str],
            filter_pattern: str = "",
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None
        ) -> bytes: ...

        @overload
        @staticmethod
        def create_patch(
            base: 'big.BigArchive',
            target: 'big.BigArchive',
            output_file: str | os.PathLike[str],
            filter_pattern: str = "",
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None
        ) -> None: ...

        @overload
        @staticmethod
        def create_patch(
            base: str | os.PathLike[str],
            target: str | os.PathLike[str],
            output_file: str | os.PathLike[str],
            filter_pattern: str = "",
            progress_callback: Callable[['big.ProgressReport'], bool | None] | None = None
        ) -> None: ...

    class BigOverlayEntry:
        @property
        def entry(self) -> 'big.BigEntry': ...
        @property
        def source_archive(self) -> Path: ...
        @property
        def override_count(self) -> int: ...
        @property
        def name(self) -> str: ...
        @property
        def size(self) -> int: ...
        @property
        def offset(self) -> int: ...
        def __eq__(self, other: object) -> bool: ...
        def __lt__(self, other: 'big.BigOverlayEntry') -> bool: ...
        def __hash__(self) -> int: ...
        def __repr__(self) -> str: ...

    class BigOverlay:
        def __init__(self) -> None: ...
        @property
        def closed(self) -> bool: ...
        def close(self) -> None: ...
        def __enter__(self) -> 'big.BigOverlay': ...
        def __exit__(
            self,
            exc_type: object = None,
            exc_val: object = None,
            exc_tb: object = None
        ) -> None: ...
        @staticmethod
        def from_directory(dir_path: str | os.PathLike[str]) -> 'big.BigOverlay': ...
        @staticmethod
        def from_archives(archive_paths: Sequence[str | os.PathLike[str]]) -> 'big.BigOverlay': ...
        def mount(self, archive_path: str | os.PathLike[str]) -> None: ...
        @property
        def mounted_archives(self) -> list[Path]: ...
        def get_entries(self, filter_pattern: str = "") -> list['big.BigOverlayEntry']: ...
        def resolve(self, entry_name: str | os.PathLike[str]) -> 'big.BigOverlayEntry': ...
        def read_entry(self, entry_name: str | os.PathLike[str]) -> bytes: ...
        def stream_entry(self, entry_name: str | os.PathLike[str], chunk_callback: Callable[[memoryview], bool | None]) -> None: ...

class ini:
    LEVEL_INDENT: str
    INI_ENDS: tuple[str, ...]
    MAX_INI_DEPTH: int

    class IniParseError(ValueError): ...

    class CommentNode:
        text: str
        def __init__(self, text: str = "") -> None: ...
        def __eq__(self, other: object) -> bool: ...
        def __repr__(self) -> str: ...

    class StatementNode:
        text: str
        comment: str
        def __init__(self, text: str = "", comment: str = "") -> None: ...
        def __eq__(self, other: object) -> bool: ...
        def __repr__(self) -> str: ...

    class IncludeNode:
        raw_path: str
        comment: str
        def __init__(self, raw_path: str = "", comment: str = "") -> None: ...
        @property
        def clean_path(self) -> str: ...
        def __eq__(self, other: object) -> bool: ...
        def __repr__(self) -> str: ...

    class ScriptNode:
        name: str
        identifier: str
        comment: str
        header_comment: str
        end_token: str
        end_comment: str
        content: list[str]
        def __init__(
            self,
            name: str = "BeginScript",
            identifier: str = "",
            comment: str = "",
            header_comment: str = "",
            end_token: str = "EndScript",
            end_comment: str = "",
            content: Sequence[str] = (),
        ) -> None: ...
        def print(self, level: int = 0, file_type: str = ".ini") -> str: ...
        def __eq__(self, other: object) -> bool: ...
        def __repr__(self) -> str: ...

    AstNode: TypeAlias = (
        CommentNode | StatementNode | IncludeNode | ScriptNode | 'ini.ConstructLevel'
    )
    StrChildNode: TypeAlias = CommentNode | StatementNode

    class ConstructLevel:
        _class: str
        name: str
        identifier: str
        comment: str
        header_comment: str
        end_token: str
        end_comment: str
        items: list['ini.AstNode']
        def __init__(
            self,
            _class: str = "",
            name: str = "",
            identifier: str = "",
            comment: str = "",
            header_comment: str = "",
            end_token: str = "",
            end_comment: str = "",
        ) -> None: ...
        def append(self, item: 'ini.AstNode') -> None: ...
        def __len__(self) -> int: ...
        def __getitem__(self, index: int) -> 'ini.AstNode': ...
        def __setitem__(self, index: int, item: 'ini.AstNode') -> None: ...
        def __iter__(self) -> Iterator['ini.AstNode']: ...
        def print(self, level: int = 0, file_type: str = ".ini") -> str: ...
        def __eq__(self, other: object) -> bool: ...
        def __repr__(self) -> str: ...

    class StrEntry:
        category: str
        identifier: str
        comment: str
        header_comment: str
        end_token: str
        end_comment: str
        items: list['ini.StrChildNode']
        def __init__(
            self,
            category: str,
            identifier: str,
            comment: str = "",
            header_comment: str = "",
            end_token: str = "End",
            end_comment: str = "",
            items: Sequence['ini.StrChildNode'] = (),
        ) -> None: ...
        def print(self) -> str: ...
        def __eq__(self, other: object) -> bool: ...
        def __repr__(self) -> str: ...

    StrDocEntry: TypeAlias = StrEntry | CommentNode | StatementNode
    RootItem: TypeAlias = AstNode | StrEntry

    class StrDocument:
        name: str
        entries: list['ini.StrDocEntry']
        errors: list[str]
        def __init__(
            self,
            name: str = "",
            entries: Sequence['ini.StrDocEntry'] = (),
            errors: Sequence[str] = (),
        ) -> None: ...
        def print(self) -> str: ...
        def __repr__(self) -> str: ...

    class StrParser:
        @staticmethod
        def parse_file(
            file_path: str | os.PathLike[str],
            strict: bool = False,
            file_content: str | None = None,
        ) -> 'ini.StrDocument': ...

    class ConstructFile:
        name: str
        comment: str
        defines: list[str]
        delimiters: list[list[str]]
        start_level: int
        strict: bool
        file_content: str | None
        items: list['ini.RootItem']
        current_level: int
        last_comment: str
        errors: list[str]
        @overload
        def __init__(
            self,
            name: str | os.PathLike[str] = "",
            strict: bool = False,
            file_content: str | None = None,
        ) -> None: ...
        @overload
        def __init__(
            self,
            name: str | os.PathLike[str],
            comment: str,
            defines: Sequence[str] = (),
            delimiters: Sequence[Sequence[str]] = (),
            start_level: int = 0,
            strict: bool = False,
            file_content: str | None = None,
        ) -> None: ...
        def construct(self) -> None: ...
        def append(self, item: 'ini.RootItem') -> None: ...
        def __len__(self) -> int: ...
        def __getitem__(self, index: int) -> 'ini.RootItem': ...
        def __setitem__(self, index: int, item: 'ini.RootItem') -> None: ...
        def __iter__(self) -> Iterator['ini.RootItem']: ...
        def print(self) -> str: ...
        def __repr__(self) -> str: ...

    @staticmethod
    def recognize_structure(
        file_path: str | os.PathLike[str],
        file_content: str | None = None,
    ) -> tuple[list[list[str]], int]: ...

    @staticmethod
    def validate_include(
        node: IncludeNode,
        current_file: str | os.PathLike[str],
        virtual_root: str | os.PathLike[str],
    ) -> Path: ...

    @staticmethod
    def load_file(full_path: str | os.PathLike[str]) -> tuple[str, list[list[str]]]: ...

    @staticmethod
    def scan_file_for_errors(file_path: str | os.PathLike[str]) -> list[str]: ...
