"""
@file src/lotm/ini/parser.py
@brief Structural parser for SAGE engine .ini, .inc, and .str configuration files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import os
import json
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Tuple

class IniParseError(ValueError):
    """Domain-specific exception for parsing errors."""
    pass

LEVEL_INDENT = ' ' * 4
INI_ENDS = ['End', 'END', 'EndScript']
THIS_DIR = Path(__file__).parent.resolve()

INI_DELIMITERS = []
STR_DELIMITERS = []


def load_delimiters():
    global INI_DELIMITERS, STR_DELIMITERS
    if INI_DELIMITERS and STR_DELIMITERS:
        return

    ini_path = THIS_DIR / '_delimiters_ini.json'
    str_path = THIS_DIR / '_delimiters_str.json'

    for delimiter_path in (ini_path, str_path):
        if delimiter_path.is_file():
            with open(delimiter_path, 'r', encoding='utf-8') as delimiters_buffer:
                if '_ini' in delimiter_path.name:
                    INI_DELIMITERS = json.load(delimiters_buffer)
                elif '_str' in delimiter_path.name:
                    STR_DELIMITERS = json.load(delimiters_buffer)
        else:
            raise IniParseError(f"delimiters file not found: {delimiter_path}")


def _read_file_lines(file_path: str) -> List[str]:
    """Reads file contents into memory with an encoding fallback for legacy SAGE files."""
    path = Path(file_path)
    try:
        return path.read_text(encoding='utf-8').splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding='windows-1252').splitlines()


def recognize_structure(file_path: str) -> Tuple[List, int]:
    load_delimiters()
    if file_path.endswith('.str'):
        delimiters = copy.deepcopy(STR_DELIMITERS)
        delimiters.append([])
        return delimiters, 0
    elif file_path.endswith('.ini') or file_path.endswith('.inc'):
        lines = _read_file_lines(file_path)
        for file_line in lines:
            words = file_line.split()
            if len(words) > 0:
                for items_levels in INI_DELIMITERS:
                    for item_level in items_levels:
                        if file_path.endswith('.ini') and items_levels.index(item_level) > 0:
                            break
                        elif words[0] in item_level:
                            delims = copy.deepcopy(items_levels)
                            delims.append([])
                            return delims, items_levels.index(item_level)
    return [], 0


@dataclass
class ConstructShared:
    items: List[Any] = field(default_factory=list, init=False)

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def append(self, item):
        self.items.append(item)

    def add(self, level):
        self.items.append(level)
        self.items[-1].is_open = True
        return self.items[-1]

    def assign(self, index=None, **key_args):
        filtered_dict = {key: key_args[key] for key in key_args if key_args[key]}
        if index is None:
            self.items.append(filtered_dict)
        else:
            self.items[index].update(filtered_dict)

    def last(self):
        for item_index in range(1, len(self.items) + 1):
            last_child = self.items[-item_index]
            if isinstance(last_child, ConstructLevel):
                if getattr(last_child, 'is_open', False):
                    return last_child.last()
        return self


@dataclass
class ConstructLevel(ConstructShared):
    _class: str = ""
    is_open: bool = False

    def __post_init__(self):
        if self._class:
            self.items.append({'class': self._class})

    def print(self, level: int = 0, file_type: str = '.ini') -> str:
        output = ''
        for item in self.items:
            if type(item) is dict:
                values_order = []
                for key in item:
                    if 'comment' == key and 'class' in item:
                        output += f"{LEVEL_INDENT * level}{item['comment']}\n"
                    else:
                        values_order.append(item[key])
                if 'end' in item:
                    level -= 1
                line = f'{LEVEL_INDENT * level}'
                for value in values_order:
                    if line.strip():
                        line += f"{' ' if file_type in ['.ini', '.inc'] else ':'}{value}"
                    else:
                        line += value
                if line.count('\n') > 1:
                    new_line = ''
                    for _ in line.split('\n'):
                        new_line += f'{"\n" if new_line else ""}{LEVEL_INDENT * level}{_.lstrip()}'
                    line = new_line

                if line and line[-1] != '\n':
                    line += '\n'
                output += line
                if 'class' in item:
                    level += 1
            elif isinstance(item, ConstructLevel):
                output += item.print(level=level, file_type=file_type)
            else:
                output += str(item)
        return output

    def construct(self):
        pass


@dataclass
class ConstructFile(ConstructShared):
    name: str = ""
    comment: str = ""
    defines: List[str] = field(default_factory=list)
    delimiters: List[List[str]] = field(default_factory=list)
    start_level: int = 0

    current_level: int = field(default=0, init=False)
    last_comment: str = field(default='', init=False)

    def __post_init__(self):
        if self.name:
            self.construct()

    def construct(self):
        self.delimiters, self.start_level = recognize_structure(self.name)
        self.current_level = self.start_level
        self.last_comment = ''

        if not (os.path.isfile(self.name) and self.name.endswith(('.ini', '.inc', '.str'))):
            raise IniParseError(f'file {self.name} invalid.')

        lines = _read_file_lines(self.name)
        for raw_line in lines:
            self._parse_line(raw_line)

    def _parse_line(self, raw_line: str):
        words, words_signs = self._extract_comments(raw_line)

        if not words:
            self._handle_empty_line(raw_line)
            return

        if self._handle_block_start(words):
            return

        if self._handle_block_end(words):
            return

        if self._handle_directives(words, words_signs):
            return

        self._handle_statement(words_signs)

    def _extract_comments(self, raw_line: str) -> Tuple[list, list]:
        comment_index = -1
        if ';' in raw_line and '//' in raw_line:
            comment_index = min(raw_line.index(';'), raw_line.index('//'))
        elif ';' in raw_line:
            comment_index = raw_line.index(';')
        elif '//' in raw_line:
            comment_index = raw_line.index('//')

        if comment_index >= 0:
            words_signs = raw_line[:comment_index].split()
            words = raw_line[:comment_index].replace('=', ' ').replace(':', ' ').split()
            comment_text = ' '.join(raw_line[comment_index:].split())
            self.last_comment += ('\n' if self.last_comment else '') + comment_text
        else:
            words_signs = raw_line.split()
            words = raw_line.replace('=', ' ').replace(':', ' ').split()

        return words, words_signs

    def _handle_empty_line(self, raw_line: str):
        if self.last_comment and raw_line.strip() == '':
            self.last().append({'comment': self.last_comment})
            self.last_comment = ''

    def _handle_block_start(self, words: list) -> bool:
        if self.current_level < len(self.delimiters) and words[0] in self.delimiters[self.current_level]:
            new_item = self.last().add(ConstructLevel(_class=words[0]))

            if len(words) == 3 and self.name.endswith('.ini'):
                new_item.assign(index=0, name=words[1], identifier=words[2], comment=self.last_comment)
            else:
                new_item.assign(index=0, name=' '.join(words[1:]), comment=self.last_comment)

            self.last_comment = ''
            self.current_level += 1
            return True
        return False

    def _handle_block_end(self, words: list) -> bool:
        if words[0] in INI_ENDS:
            self.current_level -= 1
            last = self.last()

            if self.last_comment:
                last.append({'comment': self.last_comment})
                self.last_comment = ''

            last.append({'end': ' '.join(words)})
            last.is_open = False
            return True
        return False

    def _handle_directives(self, words: list, words_signs: list) -> bool:
        if words[0] == '#define':
            self.defines.append(' '.join(words_signs))
            return True
        if words[0] == '#include':
            self.last().assign(include=' '.join(words_signs))
            return True
        return False

    def _handle_statement(self, words_signs: list):
        self.last().assign(statement=' '.join(words_signs))

    def print(self) -> str:
        output = ''
        if self.defines:
            for line in self.defines:
                output += f'{line}\n'

        for item in self.items:
            if isinstance(item, ConstructLevel):
                output += item.print(self.start_level, self.name[-4:])
            elif isinstance(item, dict):
                line = LEVEL_INDENT * self.start_level
                for key in item:
                    if line.strip():
                        line += item[key]
                    else:
                        line += f' {item[key]}'
            output += '\n'
        return output


def load_file(full_path: str) -> Tuple[str, List[List[str]]]:
    if not full_path:
        raise IniParseError('empty path.')
    if not os.path.isfile(full_path):
        raise IniParseError(f'wrong path: {full_path}')

    if full_path.endswith(('.ini', '.str', '.inc')):
        return _load_structured_file(full_path)
    elif full_path.endswith('.txt'):
        return _load_raw_text(full_path)
    else:
        raise IniParseError(f'wrong path or unsupported file type: {full_path}')


def _load_structured_file(full_path: str) -> Tuple[str, List[List[str]]]:
    try:
        file_object = ConstructFile(name=full_path)
        file_content = file_object.print()

        if not file_content:
            return _load_raw_text(full_path)

        return file_content, file_object.delimiters

    except (IniParseError, IndexError):
        return _load_raw_text(full_path)


def _load_raw_text(full_path: str) -> Tuple[str, List[List[str]]]:
    path = Path(full_path)
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = path.read_text(encoding='windows-1252')
    return content, []
