"""
@file _prototype/ini/parser.py
@brief Structural parser for SAGE engine .ini, .inc, and .str configuration files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import os
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Union, cast

class IniParseError(ValueError):
    """Domain-specific exception for parsing errors."""
    pass

LEVEL_INDENT = ' ' * 4
INI_ENDS = ('End', 'END', 'EndScript')
THIS_DIR = Path(__file__).parent.resolve()


@dataclass(frozen=True)
class DelimiterRule:
    """Pre-tokenized delimiter rule isomorphic to a C++ constexpr table entry."""
    raw: str
    match_tokens: Tuple[str, ...]
    word_count: int


@dataclass
class LexedLine:
    """Tokenized representation of a single line from the shared lexer."""
    words: List[str]
    words_signs: List[str]
    line_tokens: List[str]
    comment: str


@dataclass
class CommentNode:
    """Represents a standalone or block-internal comment."""
    text: str


@dataclass
class StatementNode:
    """Represents a standard property assignment or value line."""
    text: str
    comment: str = ""


@dataclass
class IncludeNode:
    """Represents a #include preprocessor directive."""
    text: str
    comment: str = ""


AstNode = Union[CommentNode, StatementNode, IncludeNode, 'ConstructLevel']

INI_DELIMITERS: List[List[List[str]]] = []
STR_DELIMITERS: List[str] = []
INI_DELIMITER_RULES: List[List[List[DelimiterRule]]] = []
STR_DELIMITER_RULES: List[DelimiterRule] = []


def _compile_delimiter_rules(delimiter_list: List[str]) -> List[DelimiterRule]:
    """Pre-sorts and pre-tokenizes delimiter strings to avoid per-line allocations."""
    sorted_delims = sorted(
        delimiter_list,
        key=lambda d: len(d.replace('=', ' = ').replace(':', ' : ').split()),
        reverse=True,
    )
    rules: List[DelimiterRule] = []
    for delim in sorted_delims:
        match_tokens = tuple(delim.replace('=', ' = ').replace(':', ' : ').split())
        word_count = len(delim.replace('=', ' ').replace(':', ' ').split())
        if match_tokens:
            rules.append(DelimiterRule(raw=delim, match_tokens=match_tokens, word_count=word_count))
    return rules


def _format_indented_text(text: str, level: int) -> str:
    """Formats single-line or multi-line node text with consistent level indentation."""
    indent = LEVEL_INDENT * level
    if text.count('\n') > 0:
        lines = [f"{indent}{line.lstrip()}" for line in text.split('\n')]
        return '\n'.join(lines) + '\n'
    return f"{indent}{text}\n"


def _combine_text_and_comment(text: str, comment: str) -> str:
    """Combines a node's code text and optional inline comment onto a single line."""
    if text and comment:
        return f"{text} {comment}"
    return text or comment


def load_delimiters() -> None:
    global INI_DELIMITERS, STR_DELIMITERS, INI_DELIMITER_RULES, STR_DELIMITER_RULES
    if INI_DELIMITER_RULES and STR_DELIMITER_RULES:
        return

    ini_path = THIS_DIR / '_delimiters_ini.json'
    str_path = THIS_DIR / '_delimiters_str.json'

    for delimiter_path in (ini_path, str_path):
        if delimiter_path.is_file():
            with open(delimiter_path, 'r', encoding='utf-8') as delimiters_buffer:
                if '_ini' in delimiter_path.name:
                    INI_DELIMITERS = cast(List[List[List[str]]], json.load(delimiters_buffer))
                elif '_str' in delimiter_path.name:
                    STR_DELIMITERS = cast(List[str], json.load(delimiters_buffer))
        else:
            raise IniParseError(f"delimiters file not found: {delimiter_path}")

    INI_DELIMITER_RULES = [
        [_compile_delimiter_rules(level_list) for level_list in group]
        for group in INI_DELIMITERS
    ]
    STR_DELIMITER_RULES = _compile_delimiter_rules(STR_DELIMITERS)


def _read_file_lines(file_path: str, file_content: str | None = None) -> List[str]:
    """Reads file contents into memory with an encoding fallback for legacy SAGE files."""
    if file_content is not None:
        return file_content.splitlines()
    path = Path(file_path)
    try:
        return path.read_text(encoding='utf-8').splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding='windows-1252').splitlines()


def lex_line(raw_line: str) -> LexedLine:
    """Shared lexer routine extracting comments and tokenizing code segments."""
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
    else:
        code_part = raw_line
        comment_text = ''

    words_signs = code_part.split()
    words = code_part.replace('=', ' ').replace(':', ' ').split()

    # Tokenize both '=' and ':' with whitespace so delimiters like 'CONTROLBAR:' match cleanly
    line_tokens = code_part.replace('=', ' = ').replace(':', ' : ').split()

    return LexedLine(
        words=words,
        words_signs=words_signs,
        line_tokens=line_tokens,
        comment=comment_text,
    )


def _match_delimiter_rule(line_tokens: List[str], rules: List[DelimiterRule]) -> DelimiterRule | None:
    """Matches a tokenized line against pre-compiled delimiter rules without allocation."""
    token_count = len(line_tokens)
    for rule in rules:
        k = len(rule.match_tokens)
        if token_count >= k and tuple(line_tokens[:k]) == rule.match_tokens:
            return rule
    return None


def recognize_structure(file_path: str, file_content: str | None = None) -> Tuple[List[List[str]], int]:
    load_delimiters()
    if file_path.endswith('.str'):
        empty_tail: List[str] = []
        return [list(STR_DELIMITERS), empty_tail], 0
    elif file_path.endswith('.ini') or file_path.endswith('.inc'):
        lines = _read_file_lines(file_path, file_content=file_content)
        for file_line in lines:
            lexed = lex_line(file_line)
            if not lexed.line_tokens:
                continue

            for group_idx, group_rules in enumerate(INI_DELIMITER_RULES):
                for level_idx, level_rules in enumerate(group_rules):
                    if file_path.endswith('.ini') and level_idx > 0:
                        break
                    if _match_delimiter_rule(lexed.line_tokens, level_rules) is not None:
                        delims = [list(level) for level in INI_DELIMITERS[group_idx]]
                        empty_level: List[str] = []
                        delims.append(empty_level)
                        return delims, level_idx
    return [], 0


@dataclass
class StrEntry:
    """Represents a single localized string entry inside a SAGE .str file."""
    category: str
    identifier: str
    comment: str = ""
    header_comment: str = ""
    end_token: str = "End"
    end_comment: str = ""
    items: List[Union[CommentNode, StatementNode]] = field(default_factory=list)

    def print(self) -> str:
        output = ''
        if self.comment:
            output += _format_indented_text(self.comment, 0)

        header = f"{self.category}:{self.identifier}" if self.identifier else self.category
        header = _combine_text_and_comment(header, self.header_comment)
        output += f"{header}\n"

        for item in self.items:
            if isinstance(item, StatementNode):
                output += _format_indented_text(_combine_text_and_comment(item.text, item.comment), 1)
            else:
                output += _format_indented_text(item.text, 1)

        if self.end_token:
            end_line = _combine_text_and_comment(self.end_token, self.end_comment)
            output += f"{end_line}\n"
        return output


@dataclass
class StrDocument:
    """Flat AST representation for SAGE .str localization files."""
    name: str
    entries: List[Union[StrEntry, CommentNode, StatementNode]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def print(self) -> str:
        output = ''
        for entry in self.entries:
            if isinstance(entry, StrEntry):
                output += entry.print()
            elif isinstance(entry, StatementNode):
                output += _format_indented_text(_combine_text_and_comment(entry.text, entry.comment), 0)
            elif isinstance(entry, CommentNode):
                output += _format_indented_text(entry.text, 0)
            output += '\n'
        return output


class StrParser:
    """Dedicated single-level parser for SAGE .str localization files."""

    @staticmethod
    def parse_file(file_path: str, strict: bool = False, file_content: str | None = None) -> StrDocument:
        load_delimiters()
        if not file_path.endswith('.str') or (file_content is None and not os.path.isfile(file_path)):
            raise IniParseError(f'file {file_path} invalid.')

        doc = StrDocument(name=file_path)
        active_entry: StrEntry | None = None
        last_comment = ''

        lines = _read_file_lines(file_path, file_content=file_content)
        for line_num, raw_line in enumerate(lines, start=1):
            lexed = lex_line(raw_line)

            if not lexed.words:
                if lexed.comment:
                    last_comment += ('\n' if last_comment else '') + lexed.comment
                if last_comment and raw_line.strip() == '':
                    if active_entry is not None:
                        active_entry.items.append(CommentNode(text=last_comment))
                    else:
                        doc.entries.append(CommentNode(text=last_comment))
                    last_comment = ''
                continue

            if active_entry is None:
                matched_rule = _match_delimiter_rule(lexed.line_tokens, STR_DELIMITER_RULES)
                if matched_rule is not None:
                    remaining = lexed.words[matched_rule.word_count:]
                    active_entry = StrEntry(
                        category=matched_rule.raw,
                        identifier=' '.join(remaining),
                        comment=last_comment,
                        header_comment=lexed.comment,
                    )
                    last_comment = ''
                    continue

            if last_comment:
                if active_entry is not None:
                    active_entry.items.append(CommentNode(text=last_comment))
                else:
                    doc.entries.append(CommentNode(text=last_comment))
                last_comment = ''

            if lexed.words[0] in INI_ENDS:
                if active_entry is None:
                    err_msg = (
                        f"Delimiter mismatch: negative level reached at {file_path}:{line_num} "
                        f"on closing keyword '{lexed.words[0]}': {raw_line.strip()}"
                    )
                    doc.errors.append(err_msg)
                    if strict:
                        raise IniParseError(err_msg)
                    doc.entries.append(StatementNode(text=' '.join(lexed.words), comment=lexed.comment))
                else:
                    active_entry.end_token = ' '.join(lexed.words)
                    active_entry.end_comment = lexed.comment
                    doc.entries.append(active_entry)
                    active_entry = None
                continue

            stmt = StatementNode(text=' '.join(lexed.words_signs), comment=lexed.comment)
            if active_entry is not None:
                active_entry.items.append(stmt)
            else:
                doc.entries.append(stmt)

        if last_comment:
            if active_entry is not None:
                active_entry.items.append(CommentNode(text=last_comment))
            else:
                doc.entries.append(CommentNode(text=last_comment))
            last_comment = ''

        if active_entry is not None:
            doc.entries.append(active_entry)

        return doc


@dataclass
class ConstructLevel:
    """Represents an inner block or defined object within a parsed SAGE configuration file."""
    _class: str = ""
    name: str = ""
    identifier: str = ""
    comment: str = ""
    header_comment: str = ""
    end_token: str = ""
    end_comment: str = ""
    items: List[AstNode] = field(default_factory=list, init=False)

    def __iter__(self) -> Iterator[AstNode]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> AstNode:
        return self.items[index]

    def append(self, item: AstNode) -> None:
        self.items.append(item)

    def print(self, level: int = 0, file_type: str = '.ini') -> str:
        output = ''
        if self.comment:
            output += _format_indented_text(self.comment, level)

        sep = ' ' if file_type in ['.ini', '.inc'] else ':'
        header_parts = [part for part in (self._class, self.name, self.identifier) if part]
        if header_parts:
            header_line = _combine_text_and_comment(sep.join(header_parts), self.header_comment)
            output += _format_indented_text(header_line.lstrip(), level)

        inner_level = level + 1
        for item in self.items:
            if isinstance(item, ConstructLevel):
                output += item.print(level=inner_level, file_type=file_type)
            elif isinstance(item, (StatementNode, IncludeNode)):
                output += _format_indented_text(_combine_text_and_comment(item.text, item.comment), inner_level)
            elif isinstance(item, CommentNode):
                output += _format_indented_text(item.text, inner_level)

        if self.end_token:
            end_line = _combine_text_and_comment(self.end_token, self.end_comment)
            output += f"{LEVEL_INDENT * level}{end_line}\n"

        return output


@dataclass
class ConstructFile:
    """The Root representation of a fully parsed SAGE ini/inc/str configuration document."""
    name: str = ""
    comment: str = ""
    defines: List[str] = field(default_factory=list)
    delimiters: List[List[str]] = field(default_factory=list)
    start_level: int = 0
    strict: bool = False
    file_content: str | None = None

    items: List[Union[AstNode, StrEntry]] = field(default_factory=list, init=False)
    current_level: int = field(default=0, init=False)
    last_comment: str = field(default='', init=False)
    errors: List[str] = field(default_factory=list, init=False)
    active_rules: List[List[DelimiterRule]] = field(default_factory=list, init=False)
    context_stack: List[Union['ConstructFile', ConstructLevel]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.name:
            self.construct()

    def __iter__(self) -> Iterator[Union[AstNode, StrEntry]]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> Union[AstNode, StrEntry]:
        return self.items[index]

    def append(self, item: Union[AstNode, StrEntry]) -> None:
        self.items.append(item)

    def construct(self) -> None:
        if not self.name.endswith(('.ini', '.inc', '.str')) or (
            self.file_content is None and not os.path.isfile(self.name)
        ):
            raise IniParseError(f'file {self.name} invalid.')

        self.items = []
        self.defines = []
        self.errors = []
        self.last_comment = ''
        self.context_stack = [self]

        if self.name.endswith('.str'):
            load_delimiters()
            str_doc = StrParser.parse_file(
                self.name,
                strict=self.strict,
                file_content=self.file_content,
            )
            empty_tail: List[str] = []
            self.delimiters = [list(STR_DELIMITERS), empty_tail]
            self.start_level = 0
            self.items = cast(List[Union[AstNode, StrEntry]], list(str_doc.entries))
            self.errors = list(str_doc.errors)
            return

        self.delimiters, self.start_level = recognize_structure(
            self.name,
            file_content=self.file_content,
        )
        self.active_rules = [_compile_delimiter_rules(level) for level in self.delimiters]
        self.current_level = self.start_level

        lines = _read_file_lines(self.name, file_content=self.file_content)
        for line_num, raw_line in enumerate(lines, start=1):
            self._parse_line(raw_line, line_num)

        if self.last_comment:
            self.context_stack[-1].append(CommentNode(text=self.last_comment))
            self.last_comment = ''

    def _get_lookup_level(self) -> int:
        """Calculates schema depth, shifting by 1 when inside a transparent ReplaceModule wrapper."""
        shift = sum(
            1 for node in self.context_stack
            if isinstance(node, ConstructLevel) and node._class in ('ReplaceModule', 'ReplaceModule =')
        )
        return max(0, self.current_level - shift)

    def _parse_line(self, raw_line: str, line_num: int = 0) -> None:
        lexed = lex_line(raw_line)

        if not lexed.words:
            if lexed.comment:
                self.last_comment += ('\n' if self.last_comment else '') + lexed.comment
            self._handle_empty_line(raw_line)
            return

        if self._handle_block_start(lexed.words, lexed.line_tokens, lexed.comment):
            return

        # If we are at the base level and didn't match a block start in the current schema group,
        # it might be a new block from a different schema group. Scan for it before flushing last_comment.
        if self.current_level == self.start_level and lexed.words[0] not in INI_ENDS and not lexed.words[0].startswith('#'):
            for group_idx, group_rules in enumerate(INI_DELIMITER_RULES):
                if len(group_rules) > 0:
                    if _match_delimiter_rule(lexed.line_tokens, group_rules[0]) is not None:
                        delims = [list(level) for level in INI_DELIMITERS[group_idx]]
                        empty_level: List[str] = []
                        delims.append(empty_level)
                        self.delimiters = delims
                        empty_rule_list: List[DelimiterRule] = []
                        self.active_rules = list(group_rules) + [empty_rule_list]
                        # We found a new schema group, process it immediately as a block start
                        if self._handle_block_start(lexed.words, lexed.line_tokens, lexed.comment):
                            return

        if self.last_comment:
            self.context_stack[-1].append(CommentNode(text=self.last_comment))
            self.last_comment = ''

        if self._handle_block_end(lexed.words, line_num, raw_line, lexed.comment):
            return

        if self._handle_directives(lexed.words, lexed.words_signs, lexed.comment):
            return

        self._handle_statement(lexed.words_signs, lexed.comment)

    def _handle_empty_line(self, raw_line: str) -> None:
        if self.last_comment and raw_line.strip() == '':
            self.context_stack[-1].append(CommentNode(text=self.last_comment))
            self.last_comment = ''

    def _handle_block_start(self, words: List[str], line_tokens: List[str], inline_comment: str = "") -> bool:
        lookup_level = self._get_lookup_level()
        if lookup_level < len(self.active_rules):
            matched_rule = _match_delimiter_rule(line_tokens, self.active_rules[lookup_level])
            if matched_rule is not None:
                remaining_words = words[matched_rule.word_count:]

                block_name = ""
                block_identifier = ""
                if len(remaining_words) == 2 and self.name.endswith(('.ini', '.inc')):
                    block_name = remaining_words[0]
                    block_identifier = remaining_words[1]
                elif remaining_words:
                    block_name = ' '.join(remaining_words)

                class_token = matched_rule.raw
                next_idx = len(matched_rule.match_tokens)
                if next_idx < len(line_tokens) and line_tokens[next_idx] == '=' and not class_token.endswith('='):
                    class_token += ' ='

                new_block = ConstructLevel(
                    _class=class_token,
                    name=block_name,
                    identifier=block_identifier,
                    comment=self.last_comment,
                    header_comment=inline_comment,
                )
                self.context_stack[-1].append(new_block)
                self.context_stack.append(new_block)

                self.last_comment = ''
                self.current_level += 1
                return True
        return False

    def _handle_block_end(
        self,
        words: List[str],
        line_num: int = 0,
        raw_line: str = "",
        inline_comment: str = "",
    ) -> bool:
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

            end_str = ' '.join(words)
            if len(self.context_stack) > 1 and isinstance(active_container, ConstructLevel):
                active_container.end_token = end_str
                active_container.end_comment = inline_comment
                self.context_stack.pop()
            else:
                active_container.append(StatementNode(text=end_str, comment=inline_comment))
            return True
        return False

    def _handle_directives(self, words: List[str], words_signs: List[str], inline_comment: str = "") -> bool:
        if words[0] == '#define':
            self.defines.append(_combine_text_and_comment(' '.join(words_signs), inline_comment))
            return True
        if words[0] == '#include':
            self.context_stack[-1].append(IncludeNode(text=' '.join(words_signs), comment=inline_comment))
            return True
        return False

    def _handle_statement(self, words_signs: List[str], inline_comment: str = "") -> None:
        self.context_stack[-1].append(StatementNode(text=' '.join(words_signs), comment=inline_comment))

    def print(self) -> str:
        output = ''
        if self.defines:
            for line in self.defines:
                output += f'{line}\n'

        for item in self.items:
            if isinstance(item, StrEntry):
                output += item.print()
            elif isinstance(item, ConstructLevel):
                output += item.print(self.start_level, self.name[-4:])
            elif isinstance(item, (StatementNode, IncludeNode)):
                output += _format_indented_text(_combine_text_and_comment(item.text, item.comment), self.start_level)
            elif isinstance(item, CommentNode):
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
    empty_delims: List[List[str]] = []
    return content, empty_delims


def scan_file_for_errors(file_path: str) -> List[str]:
    """Parses a file in non-crashing mode and returns any delimiter or level mismatch errors."""
    try:
        file_object = ConstructFile(name=file_path, strict=False)
        return file_object.errors
    except Exception as exc:
        return [f"Fatal error while processing {file_path}: {exc}"]
