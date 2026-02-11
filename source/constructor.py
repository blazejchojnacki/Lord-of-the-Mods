import os

import source.shared


class ConstructShared(list):
    def __init__(self):
        super().__init__()

    def add(self, level):
        self.append(level)
        self[-1].is_open = True
        return self[-1]

    def assign(self, index=None, **key_args):
        filtered_dict = {key: key_args[key] for key in key_args if key_args[key]}
        if index is None:
            self.append(filtered_dict)
        else:
            self[index].update(filtered_dict)

    def last(self):
        for item_index in range(len(self)):
            last_child = self[-item_index]
            if isinstance(last_child, ConstructLevel):
                if last_child.is_open:
                    return last_child.last()
        else:
            return self


class ConstructLevel(ConstructShared):

    def __init__(self, _class):
        super().__init__()
        self.is_open = False
        self.append({'class': _class})

    def print(self, level: int = 0, file_type: str = '.ini'):
        output = ''
        for item in self:
            if type(item) is dict:
                values_order = []
                for key in item:
                    if 'comment' == key and 'class' in item:
                        output += f"{source.shared.LEVEL_INDENT * level}{item['comment']}\n"
                    else:
                        values_order.append(item[key])
                if 'end' in item:
                    level -= 1
                line = f'{source.shared.LEVEL_INDENT * level}'
                for value in values_order:
                    if line.strip():
                        line += f"{' ' if file_type in ['.ini', '.inc'] else ':'}{value}"
                    else:
                        line += value
                if line.count('\n') > 1:
                    new_line = ''
                    for _ in line.split('\n'):
                        new_line += f'{"\n" if new_line else ""}{source.shared.LEVEL_INDENT * level}{_.lstrip()}'
                    line = new_line

                if line[-1] != '\n':
                    line += '\n'
                output += line
                if 'class' in item:
                    level += 1
                # output += f'{line}\n'
            elif isinstance(item, ConstructLevel):
                output += item.print(level=level)
            else:
                output += item
        return output

    def construct(self):
        pass


class ConstructFile(ConstructShared):

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.comment = ''
        self.defines = []
        self.delimiters = []
        self.start_level = 0
        if name:
            self.construct()

    def recognize_structure(self) -> None:
        if source.shared.MOD_DEF_FILE_NAME in self.name:
            raise source.shared.InternalError('functional file')
        if self.name.endswith('.str'):
            delimiters = source.shared.STR_DELIMITERS.copy()
            delimiters.append([])
            self.delimiters, self.start_level = delimiters, 0
            return
        elif self.name.endswith('.ini') or self.name.endswith('.inc'):
            with open(self.name) as loaded_file:
                for file_line in loaded_file.readlines():
                    words = file_line.split()
                    if len(words) > 0:
                        for items_levels in source.shared.INI_DELIMITERS:
                            for item_level in items_levels:
                                if self.name.endswith('.ini') and items_levels.index(item_level) > 0:
                                    break
                                elif words[0] in item_level:
                                    items_levels.append([])
                                    self.delimiters, self.start_level = items_levels, items_levels.index(item_level)
                                    return

    def construct(self):
        self.recognize_structure()
        current_level = self.start_level
        if (os.path.isfile(self.name) and
                (self.name.endswith('.ini') or self.name.endswith('.inc') or self.name.endswith('.str'))):
            with open(self.name) as file_pointer:
                raw_lines = file_pointer.readlines()
        else:
            raise source.shared.InternalError(f'file {self.name} invalid.')
        last_comment = ''
        for raw_line in raw_lines:
            words = words_signs = []
            comment_index = -1
            if ';' in raw_line and '//' in raw_line:
                comment_index = min(raw_line.index(';'), raw_line.index('//'))
            elif ';' in raw_line:
                comment_index = raw_line.index(';')
            elif '//' in raw_line:
                comment_index = raw_line.index('//')
            else:
                words_signs = raw_line.split()
                words = raw_line.replace('=', ' ').replace(':', ' ').split()
            if comment_index >= 0:
                words_signs = raw_line[:comment_index].split()
                words = raw_line[:comment_index].replace('=', ' ').replace(':', ' ').split()
                if last_comment:
                    last_comment += '\n' + ' '.join(raw_line[comment_index:].split())
                else:
                    last_comment += ' '.join(raw_line[comment_index:].split())
            if not words:
                if last_comment and raw_line.strip() == '':
                    self.last().append({'comment': last_comment})
                    last_comment = ''
                continue
            if words[0] in self.delimiters[current_level]:
                new_item = self.last().add(ConstructLevel(_class=words[0]))
                if len(words) == 3 and self.name.endswith('.ini'):
                    new_item.assign(index=0, name=words[1], identifier=words[2], comment=last_comment)
                else:
                    new_item.assign(index=0, name=' '.join(words[1:]), comment=last_comment)
                last_comment = ''
                current_level += 1
            elif words[0] in source.shared.INI_ENDS:
                current_level -= 1
                last = self.last()
                if last_comment:
                    last.append({'comment': last_comment})
                    last_comment = ''
                last.append({'end': ' '.join(words)})
                last.is_open = False
            elif '#define' == words[0]:
                self.defines.append(' '.join(words_signs))
            elif '#include' == words[0]:
                self.last().assign(include=' '.join(words_signs))
            else:
                self.last().assign(statement=' '.join(words_signs))

    def print(self):
        output = ''
        if self.defines:
            for line in self.defines:
                output += f'{line}\n'
        for item in self:
            if isinstance(item, ConstructLevel):
                output += item.print(self.start_level, self.name[-4:])
            elif isinstance(item, dict):
                line = source.shared.LEVEL_INDENT * self.start_level
                for key in item:
                    if line.strip():
                        line += item[key]
                    else:
                        line += f' {item[key]}'
            output += '\n'
        return output


def load_file(full_path):
    """

    :param full_path: absolute path of the file to load into the text editor
    :return: the file content
    """
    if not os.path.isfile(full_path):
        raise source.shared.InternalError(f'wrong path: {full_path}')
    elif full_path.endswith('.ini') or full_path.endswith('.str') or full_path.endswith('.inc'):
        try:
            file_object = ConstructFile(name=full_path)
            file_content = file_object.print()
            try:
                file_levels = file_object.delimiters
            except source.shared.InternalError as error:
                return error.message, []
        except IndexError:
            file_content = ''
            file_levels = []
        if not file_content:
            with open(full_path) as loaded_file:
                file_content = loaded_file.read()
                return file_content, []
        else:
            return file_content, file_levels
    elif full_path.endswith('.txt'):
        with open(full_path) as loaded_file:
            file_content = loaded_file.read()
            return file_content, []
    # OPTIMIZE: Enable reading and extracting .BIGs
    # elif full_path.endswith('.big'):
    #     file_content = ''
    #     with open(full_path) as loaded_file:
    #         for line in loaded_file:
    #             file_content += loaded_file.readline()
    elif not full_path:
        raise source.shared.InternalError(f'empty path.')
    else:
        raise source.shared.InternalError(f'wrong path or unsupported file type: {full_path}')


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
        raise s.InternalError(error.strerror)
    for item in items:
        if os.path.isdir(f'{full_path}/{item}'):
            output_folders.append(f'{(full_path + "/") * mode}{item}')
            if mode == 1:
                add_folders, add_files = load_directories(output_folders[-1], mode=1)
                if add_folders:
                    output_folders.append(add_folders)
                if add_files:
                    output_files.append(add_files)
        elif os.path.isfile(f'{full_path}/{item}'):
            output_files.append(f'{(full_path + "/") * mode}{item}')
    return output_folders, output_files
