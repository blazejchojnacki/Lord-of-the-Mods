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
from typing import List, Tuple, Union

class IniParseError(ValueError):
    """Domain-specific exception for parsing errors."""
    pass

LEVEL_INDENT = ' ' * 4
INI_ENDS = ['End', 'END', 'EndScript']
THIS_DIR = Path(__file__).parent.resolve()

INI_DELIMITERS = []
STR_DELIMITERS = []


@dataclass
class CommentNode:
    """Represents a standalone or block-internal comment."""
    text: str


@dataclass
class StatementNode:
    """Represents a standard property assignment or value line."""
    text: str


@dataclass
class IncludeNode:
    """Represents a #include preprocessor directive."""
    text: str


AstNode = Union[CommentNode, StatementNode, IncludeNode, 'ConstructLevel']


def _format_indented_text(text: str, level: int) -> str:
    """Formats single-line or multi-line node text with consistent level indentation."""
    indent = LEVEL_INDENT * level
    if text.count('\n') > 0:
        lines = [f"{indent}{line.lstrip()}" for line in text.split('\n')]
        return '\n'.join(lines) + '\n'
    return f"{indent}{text}\n"


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


def _find_matching_delimiter(line_tokens: List[str], delimiter_list: List[str]) -> str | None:
    """
    Matches the start of a tokenized line against a delimiter list, normalizing whitespace
    and respecting '=' tokens. Longer and more specific delimiters are evaluated first.
    """
    for delim in sorted(delimiter_list, key=lambda d: len(d.replace('=', ' = ').split()), reverse=True):
        delim_tokens = delim.replace('=', ' = ').split()
        k = len(delim_tokens)
        if k > 0 and len(line_tokens) >= k and line_tokens[:k] == delim_tokens:
            return delim
    return None


def recognize_structure(file_path: str) -> Tuple[List, int]:
    load_delimiters()
    if file_path.endswith('.str'):
        delimiters = [copy.deepcopy(STR_DELIMITERS), []]
        return delimiters, 0
    elif file_path.endswith('.ini') or file_path.endswith('.inc'):
        lines = _read_file_lines(file_path)
        for file_line in lines:
            comment_index = -1
            if ';' in file_line and '//' in file_line:
                comment_index = min(file_line.index(';'), file_line.index('//'))
            elif ';' in file_line:
                comment_index = file_line.index(';')
            elif '//' in file_line:
                comment_index = file_line.index('//')

            code_line = file_line[:comment_index] if comment_index >= 0 else file_line
            line_tokens = code_line.replace('=', ' = ').split()
            if not line_tokens:
                continue

            for items_levels in INI_DELIMITERS:
                for item_level in items_levels:
                    if file_path.endswith('.ini') and items_levels.index(item_level) > 0:
                        break
                    matched = _find_matching_delimiter(line_tokens, item_level)
                    if matched is not None:
                        delims = copy.deepcopy(items_levels)
                        delims.append([])
                        return delims, items_levels.index(item_level)
    return [], 0


@dataclass
class ConstructShared:
    items: List[AstNode] = field(default_factory=list, init=False)

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def append(self, item: AstNode):
        self.items.append(item)


@dataclass
class ConstructLevel(ConstructShared):
    _class: str = ""
    name: str = ""
    identifier: str = ""
    comment: str = ""
    end_token: str = ""

    def print(self, level: int = 0, file_type: str = '.ini') -> str:
        output = ''
        if self.comment:
            output += f"{LEVEL_INDENT * level}{self.comment}\n"

        sep = ' ' if file_type in ['.ini', '.inc'] else ':'
        header_parts = [part for part in (self._class, self.name, self.identifier) if part]
        if header_parts:
            header_line = f"{LEVEL_INDENT * level}{sep.join(header_parts)}"
            output += _format_indented_text(header_line.lstrip(), level)

        inner_level = level + 1
        for item in self.items:
            if isinstance(item, ConstructLevel):
                output += item.print(level=inner_level, file_type=file_type)
            elif isinstance(item, (CommentNode, StatementNode, IncludeNode)):
                output += _format_indented_text(item.text, inner_level)

        if self.end_token:
            output += f"{LEVEL_INDENT * level}{self.end_token}\n"

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
    strict: bool = False

    current_level: int = field(default=0, init=False)
    last_comment: str = field(default='', init=False)
    errors: List[str] = field(default_factory=list, init=False)
    context_stack: List[ConstructShared] = field(default_factory=list, init=False)

    def __post_init__(self):
        if self.name:
            self.construct()

    def construct(self):
        self.delimiters, self.start_level = recognize_structure(self.name)
        self.current_level = self.start_level
        self.last_comment = ''
        self.errors = []
        self.context_stack = [self]

        if not (os.path.isfile(self.name) and self.name.endswith(('.ini', '.inc', '.str'))):
            raise IniParseError(f'file {self.name} invalid.')

        lines = _read_file_lines(self.name)
        for line_num, raw_line in enumerate(lines, start=1):
            self._parse_line(raw_line, line_num)

    def _get_lookup_level(self) -> int:
        """Calculates schema depth, shifting by 1 when inside a transparent ReplaceModule wrapper."""
        shift = sum(
            1 for node in self.context_stack
            if isinstance(node, ConstructLevel) and node._class == 'ReplaceModule'
        )
        return max(0, self.current_level - shift)

    def _parse_line(self, raw_line: str, line_num: int = 0):
        words, words_signs, line_tokens = self._extract_comments(raw_line)

        if not words:
            self._handle_empty_line(raw_line)
            return

        if self._handle_block_start(words, line_tokens):
            return

        if self._handle_block_end(words, line_num, raw_line):
            return

        if self._handle_directives(words, words_signs):
            return

        # If we are at the base level and didn't match a block start, end, or directive,
        # it might be a new block from a different schema group. Scan for it.
        if self.current_level == self.start_level and not self.name.endswith('.str'):
            for items_levels in INI_DELIMITERS:
                if len(items_levels) > 0:
                    matched = _find_matching_delimiter(line_tokens, items_levels[0])
                    if matched is not None:
                        self.delimiters = copy.deepcopy(items_levels)
                        self.delimiters.append([])
                        # We found a new schema group, process it immediately as a block start
                        if self._handle_block_start(words, line_tokens):
                            return

        self._handle_statement(words_signs)

    def _extract_comments(self, raw_line: str) -> Tuple[list, list, list]:
        comment_index = -1
        if ';' in raw_line and '//' in raw_line:
            comment_index = min(raw_line.index(';'), raw_line.index('//'))
        elif ';' in raw_line:
            comment_index = raw_line.index(';')
        elif '//' in raw_line:
            comment_index = raw_line.index('//')

        if comment_index >= 0:
            code_part = raw_line[:comment_index]
            comment_text = ' '.join(raw_line[comment_index:].split())
            self.last_comment += ('\n' if self.last_comment else '') + comment_text
        else:
            code_part = raw_line

        words_signs = code_part.split()
        words = code_part.replace('=', ' ').replace(':', ' ').split()

        # Tokenize both '=' and ':' with whitespace so delimiters like 'CONTROLBAR:' match cleanly
        line_tokens = code_part.replace('=', ' = ').replace(':', ' : ').split()

        return words, words_signs, line_tokens

    def _handle_empty_line(self, raw_line: str):
        if self.last_comment and raw_line.strip() == '':
            self.context_stack[-1].append(CommentNode(text=self.last_comment))
            self.last_comment = ''

    def _handle_block_start(self, words: list, line_tokens: list) -> bool:
        lookup_level = self._get_lookup_level()
        if lookup_level < len(self.delimiters):
            matched_delim = _find_matching_delimiter(line_tokens, self.delimiters[lookup_level])
            if matched_delim is not None:
                delim_words = matched_delim.replace('=', ' ').replace(':', ' ').split()
                remaining_words = words[len(delim_words):]

                block_name = ""
                block_identifier = ""
                if len(remaining_words) == 2 and self.name.endswith('.ini'):
                    block_name = remaining_words[0]
                    block_identifier = remaining_words[1]
                elif remaining_words:
                    block_name = ' '.join(remaining_words)

                new_block = ConstructLevel(
                    _class=matched_delim,
                    name=block_name,
                    identifier=block_identifier,
                    comment=self.last_comment,
                )
                self.context_stack[-1].append(new_block)
                self.context_stack.append(new_block)

                self.last_comment = ''
                self.current_level += 1
                return True
        return False

    def _handle_block_end(self, words: list, line_num: int = 0, raw_line: str = "") -> bool:
        if words[0] in INI_ENDS:
            self.current_level -= 1
            if self.current_level < 0:
                err_msg = (
                    f"Delimiter mismatch: negative level reached at {self.name}:{line_num} "
                    f"on closing keyword '{words[0]}': {raw_line.strip()}"
                )
                self.errors.append(err_msg)
                if self.strict:
                    raise IniParseError(err_msg)
                self.current_level = 0

            active_container = self.context_stack[-1]

            if self.last_comment:
                active_container.append(CommentNode(text=self.last_comment))
                self.last_comment = ''

            end_str = ' '.join(words)
            if len(self.context_stack) > 1 and isinstance(active_container, ConstructLevel):
                active_container.end_token = end_str
                self.context_stack.pop()
            else:
                active_container.append(StatementNode(text=end_str))
            return True
        return False

    def _handle_directives(self, words: list, words_signs: list) -> bool:
        if words[0] == '#define':
            self.defines.append(' '.join(words_signs))
            return True
        if words[0] == '#include':
            self.context_stack[-1].append(IncludeNode(text=' '.join(words_signs)))
            return True
        return False

    def _handle_statement(self, words_signs: list):
        self.context_stack[-1].append(StatementNode(text=' '.join(words_signs)))

    def print(self) -> str:
        output = ''
        if self.defines:
            for line in self.defines:
                output += f'{line}\n'

        for item in self.items:
            if isinstance(item, ConstructLevel):
                output += item.print(self.start_level, self.name[-4:])
            elif isinstance(item, (CommentNode, StatementNode, IncludeNode)):
                output += _format_indented_text(item.text, self.start_level)
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
        file_object = ConstructFile(name=full_path, strict=False)
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


def scan_file_for_errors(file_path: str) -> List[str]:
    """Parses a file in non-crashing mode and returns any delimiter or level mismatch errors."""
    try:
        file_object = ConstructFile(name=file_path, strict=False)
        return file_object.errors
    except Exception as exc:
        return [f"Fatal error while processing {file_path}: {exc}"]
