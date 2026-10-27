"""
@file src/lotm/big.pyi
@brief stub for type checks and hints in Python IDE.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from typing import Callable
import os
import lotm.big


class BigArchive:
    """
    Parser and extractor for BIG4 archives
    """

    def __init__(self, file_path: str | os.PathLike[str]) -> None:
        ...

    def extract_all(
        self, 
        output_dir: str | os.PathLike[str], 
        progress_callback: Callable[[str], None] | None = None
    ) -> None:
        ...

    def get_entries(self) -> list[lotm.big.BigEntry]:
        ...


class BigEntry:
    """
    Metadata record for an entry inside a BIG4 archive
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """
        Initialize self.  See help(type(self)) for accurate signature.
        """
        ...

    @property
    def name(self) -> str:
        ...

    @property
    def offset(self) -> int:
        ...

    @property
    def size(self) -> int:
        ...

    def __repr__(self) -> str:
        ...


class BigPacker:
    """
    Packing engine for BIG4 archives
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """
        Initialize self.  See help(type(self)) for accurate signature.
        """
        ...

    @staticmethod
    def pack_from_directory(
        source_dir: str | os.PathLike[str], 
        output_file: str | os.PathLike[str], 
        progress_callback: Callable[[str], None] | None = None
    ) -> None:
        ...
