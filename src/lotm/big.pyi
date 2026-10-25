'''
@file src/lotm/big.pyi
@brief stub for type checks and hints in Python IDE.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.

This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <https://www.gnu.org/licenses/>.

SPDX-License-Identifier: GPL-3.0-or-later
'''

from typing import Any, Optional, overload, Typing, Sequence, Iterable, Union, Callable
from enum import Enum
import lotm.big

class BigArchive:
    """
    None
    """

    def __init__(self, file_path: str | os.PathLike) -> None:
        ...
    
    def extract_all(self, output_dir: str | os.PathLike) -> None:
        ...
    
    def get_entries(self) -> list[lotm.big.BigEntry]:
        ...
    
    def read_header(self) -> None:
        ...
    
class BigEntry:
    """
    None
    """

    def __init__(*args, **kwargs):
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
    
class BigPacker:
    """
    None
    """

    def __init__(*args, **kwargs):
        """
        Initialize self.  See help(type(self)) for accurate signature.
        """
        ...
    
    def pack_from_directory(source_dir: str | os.PathLike, output_file: str | os.PathLike) -> None:
        ...
    
