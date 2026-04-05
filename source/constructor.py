import os
from dataclasses import dataclass, field
from typing import List, Any

from source.messaging import InternalError
from source.constants import LEVEL_INDENT, MOD_DEF_FILE_NAME, INI_DELIMITERS, STR_DELIMITERS, INI_ENDS


def recognize_structure(file_path) -> (List, int):
    if MOD_DEF_FILE_NAME in file_path:
        raise InternalError('functional file')
    if file_path.endswith('.str'):
        delimiters = STR_DELIMITERS.copy()
        delimiters.append([])
        return delimiters, 0
    elif file_path.endswith('.ini') or file_path.endswith('.inc'):
        with open(file_path) as loaded_file:
            for file_line in loaded_file.readlines():
                words = file_line.split()
                if len(words) > 0:
                    for items_levels in INI_DELIMITERS:
                        for item_level in items_levels:
                            if file_path.endswith('.ini') and items_levels.index(item_level) > 0:
                                break
                            elif words[0] in item_level:
                                items_levels.append([])
                                return items_levels, items_levels.index(item_level)


@dataclass
class ConstructShared:
    """ Base dataclass acting as a container for parsed file elements. """

    # ADDED init=False: This prevents 'items' from hijacking the first positional argument!
    items: List[Any] = field(default_factory=list, init=False)

    # --- Dunder methods to maintain compatibility with external files (like editor.py) ---
    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]

    # --- Class Capabilities ---
    def append(self, item):
        """ Replaces the built-in list.append() """
        self.items.append(item)

    def add(self, level):
        """ Appends a new level and automatically sets it to open. """
        self.items.append(level)
        self.items[-1].is_open = True
        return self.items[-1]

    def assign(self, index=None, **key_args):
        """ Assigns properties to the current or specified index dictionary. """
        filtered_dict = {key: key_args[key] for key in key_args if key_args[key]}
        if index is None:
            self.items.append(filtered_dict)
        else:
            self.items[index].update(filtered_dict)

    def last(self):
        """ Recursively finds the deepest open ConstructLevel. """
        for item_index in range(1, len(self.items) + 1):
            last_child = self.items[-item_index]
            if isinstance(last_child, ConstructLevel):
                if getattr(last_child, 'is_open', False):
                    return last_child.last()
        return self


@dataclass
class ConstructLevel(ConstructShared):
    """ Represents an inner block or object within a parsed file. """

    _class: str = ""
    is_open: bool = False

    def __post_init__(self):
        """ Automatically executes right after the dataclass initializes. """
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

                if line[-1] != '\n':
                    line += '\n'
                output += line
                if 'class' in item:
                    level += 1
            elif isinstance(item, ConstructLevel):
                output += item.print(level=level)
            else:
                output += item
        return output

    def construct(self):
        pass


@dataclass
class ConstructFile(ConstructShared):
    """ The Root representation of a fully parsed ini/inc/str file. """

    name: str = ""
    comment: str = ""
    defines: List[str] = field(default_factory=list)
    delimiters: List[List[str]] = field(default_factory=list)
    start_level: int = 0

    # Transient parser state variables
    current_level: int = field(default=0, init=False)
    last_comment: str = field(default='', init=False)

    def __post_init__(self):
        if self.name:
            self.construct()

    def construct(self):
        """ The Main Loop: Now strictly a router, delegating all logic to helpers. """
        self.delimiters, self.start_level = recognize_structure(self.name)
        self.current_level = self.start_level
        self.last_comment = ''

        if not (os.path.isfile(self.name) and self.name.endswith(('.ini', '.inc', '.str'))):
            raise InternalError(f'file {self.name} invalid.')

        with open(self.name, 'r') as file_pointer:
            for raw_line in file_pointer:
                self._parse_line(raw_line)

    def _parse_line(self, raw_line: str):
        """ Tokenizes the line and routes it to the correct handler. """
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

    # --- SYNTAX HANDLERS ---

    def _extract_comments(self, raw_line: str) -> tuple[list, list]:
        """ Separates the code from inline comments and updates the running comment buffer. """
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
        """ Appends floating comments when an empty line acts as a separator. """
        if self.last_comment and raw_line.strip() == '':
            self.last().append({'comment': self.last_comment})
            self.last_comment = ''

    def _handle_block_start(self, words: list) -> bool:
        """ Detects and opens a new ConstructLevel if the word matches a delimiter. """
        if words[0] in self.delimiters[self.current_level]:
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
        """ Detects closing keywords (e.g. 'End') and finalizes the active level. """
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
        """ Handles Preprocessor directives like #define and #include. """
        if words[0] == '#define':
            self.defines.append(' '.join(words_signs))
            return True
        if words[0] == '#include':
            self.last().assign(include=' '.join(words_signs))
            return True
        return False

    def _handle_statement(self, words_signs: list):
        """ If it's not a block, end, or directive, it's a standard property assignment. """
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


def load_file(full_path):
    """ Loads a file for the text editor, parsing it structurally if supported. """
    if not full_path:
        raise InternalError('empty path.')
    if not os.path.isfile(full_path):
        raise InternalError(f'wrong path: {full_path}')

    if full_path.endswith(('.ini', '.str', '.inc')):
        return _load_structured_file(full_path)
    elif full_path.endswith('.txt'):
        return _load_raw_text(full_path)
    else:
        raise InternalError(f'wrong path or unsupported file type: {full_path}')


def _load_structured_file(full_path) -> tuple:
    """ Helper: Attempts to construct the file tree, falling back to raw text on syntax errors. """
    try:
        file_object = ConstructFile(name=full_path)
        file_content = file_object.print()

        if not file_content:  # If parsing yielded nothing, fallback to raw
            return _load_raw_text(full_path)

        return file_content, file_object.delimiters

    except (InternalError, IndexError):
        # Fallback to plain text if structure recognition or parsing fails
        return _load_raw_text(full_path)


def _load_raw_text(full_path) -> tuple:
    """ Helper: Simply reads the raw text from the file without parsing. """
    with open(full_path, 'r') as loaded_file:
        return loaded_file.read(), []


def load_directories(full_path, mode=0):
    """

    :param full_path:
    :param mode: mode=0 makes the function omit the full path,
     mode=1 makes the function provide the full path of each item
    :return: a tuple of two lists of folders and files contained in the given directory
    """
    output_folders = []
    output_files = []
    try:
        items = os.listdir(full_path)
    except PermissionError as error:
        raise InternalError(error.strerror)
    for item in items:
        if os.path.isdir(f'{full_path}/{item}'):
            output_folders.append(f'{(full_path + "/") * mode}{item}')
            if mode == 1:
                add_folders, add_files = load_directories(output_folders[-1], mode=1)
                if add_folders:
                    output_folders.extend(add_folders)
                if add_files:
                    output_files.extend(add_files)
        elif os.path.isfile(f'{full_path}/{item}'):
            output_files.append(f'{(full_path + "/") * mode}{item}')
    return output_folders, output_files
