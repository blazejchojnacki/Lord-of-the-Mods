'''
@file src/lotm/_core.pyi
@brief Type stubs for the private C++ native extension core.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
'''

from typing import Callable
import os

class big:
    class BigArchiveError(RuntimeError): ...
    class BigFormatError(BigArchiveError): ...
    class BigSecurityError(BigArchiveError): ...

    class BigArchive:
        def __init__(self, file_path: str | os.PathLike[str]) -> None: ...
        def extract_all(
            self, 
            output_dir: str | os.PathLike[str], 
            progress_callback: Callable[[str], None] | None = None
        ) -> None: ...
        def get_entries(self) -> list['big.BigEntry']: ...

    class BigEntry:
        def __init__(self, *args: object, **kwargs: object) -> None: ...
        @property
        def name(self) -> str: ...
        @property
        def offset(self) -> int: ...
        @property
        def size(self) -> int: ...
        def __repr__(self) -> str: ...

    class BigPacker:
        def __init__(self, *args: object, **kwargs: object) -> None: ...
        @staticmethod
        def pack_from_directory(
            source_dir: str | os.PathLike[str], 
            output_file: str | os.PathLike[str], 
            progress_callback: Callable[[str], None] | None = None
        ) -> None: ...
