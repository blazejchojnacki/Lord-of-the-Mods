from datetime import datetime
import os
import shutil
import re
from collections import defaultdict

from source.messaging import log, InternalError, InternalWarning, internal_message, get_custom_logger
from source.constants import INI_COMMENTS, INI_DELIMITERS, STR_DELIMITERS
import source.constructor as c

# FUTURE: automated proposition of #include creation or child adopting


def reformat_string(string, direction='automatic'):
    """
    converts the \n \t \r characters for reading or for finding the string in a file
    :param string: str to convert
    :param direction: 'automatic', 'process', 'display'
    :return: converted string
    """
    to_convert = {
        '\n': '\\n',
        '\t': '\\t',
        '\r': '\\r',
        ' ': '·'
    }
    for key in to_convert:
        if direction == 'process' or to_convert[key] in string and direction != 'display':
            for character in to_convert:
                string = string.replace(to_convert[character], character)
            return string
        elif key in string or direction == 'display':
            for character in to_convert:
                string = string.replace(character, to_convert[character])
            return string
        else:
            return string


def text_find_multiple(find_list: list, scope='', exceptions=None, not_used=None, output_file='output.txt'):
    """
     finds multiple given strings in a given file or folder of files
     :param find_list: list of strings to find
     :param scope: path to file or folder where to look for the strings
     :param exceptions: list of files to omit
     :param not_used: recursive value placeholder
     :param output_file:
     """
    if exceptions is None:
        exceptions = []
    if not_used is None:
        not_used = set(find_list)
    output = ''
    output_log = get_custom_logger("find_multiple", output_file)
    for exception in exceptions:
        if scope.replace('\\', '/') == exception.replace('\\', '/'):
            return not_used
    if os.path.isfile(scope):
        try:
            with open(scope) as file_buffer:
                file_content = file_buffer.read()
            output += f'In {scope}\n'
            for find in find_list:
                find_count = file_content.count(find)
                if find_count > 0:
                    find_dict = {}
                    index_line = 1
                    content_index_prev = 0
                    for content_part in file_content.split(find)[:-1]:
                        index_line += content_part.count('\n')
                        content_index = (
                                file_content.index(content_part, content_index_prev) + len(content_part) + len(find))
                        if file_content[content_index] in [' ', '\n', '\t', ';', '/']:
                            content_index_prev = content_index
                            if find in not_used:
                                not_used.remove(find)
                            text_line = file_content.split('\n')[index_line - 1]
                            find_dict[index_line] = text_line
                        else:
                            find_count -= 1
                    if find_dict:
                        output += f'\tref: {find} found {find_count}:\n'
                        for key in find_dict:
                            output += f'\t\tin line {key} "{find_dict[key]}"\n'
            if output and output_file:
                output_log.info(output)
        except UnicodeDecodeError:
            raise InternalWarning(f'file {scope} unreadable')
    elif os.path.isdir(scope):
        file_paths = os.listdir(scope)
        for file_path in file_paths:
            not_used = not_used.intersection(
                text_find_multiple(find_list, f'{scope}/{file_path}', exceptions, not_used, output_file))
            continue
    return not_used


def find_objects_in_str_file(file, scope, exceptions, used_file='reference_RotWK_lotr_str.txt',
                             unused_file='reference_RotWK_lotr_str_unused.txt'):
    output_log = get_custom_logger("find_objects_in_str_file", unused_file)
    items = c.ConstructFile(file)
    if file.endswith('.str'):
        titles_list = []
        for item in items:
            titles_list.append(f"{item[1]['class']}:{item[1]['name']}")
        output_set = text_find_multiple(titles_list, scope=scope, exceptions=exceptions, output_file=used_file)
        output_ordered = list(output_set)
        output_ordered.sort()
        output = 'Unused references:\n'
        for not_used_ref in output_ordered:
            output += f'{not_used_ref}\n'
        output_log.info(output)
    elif file.endswith('.ini'):
        pass


def text_find_replace(find, replace_with=None, scope='', exceptions=None, mode='initiate'):
    """ replaces a given string by another in a given file or folder of files """
    output = ''
    if not find:
        return internal_message('aborted - empty string to find')
    if 'initiate' in mode:
        output += f'{datetime.now()}'
        if replace_with is not None:
            output += f' command: replace "{reformat_string(find, direction="display")}"\n'
            output += f'\twith "{reformat_string(replace_with, direction="display")}"\n\tin {scope}.\n'
        else:
            output += f' command: find "{reformat_string(find, direction="display")}"\n'
            output += f' in {scope}. \n'
        if exceptions:
            output += f'\texcept in {str(exceptions).strip("[]")}\n'
        output += 'result: '
    find = reformat_string(find, direction='process')
    if replace_with is not None:
        replace_with = reformat_string(replace_with, direction='process')
    if ', ' in scope and 'initiate' in mode:
        for scope_element in scope.split(', '):
            output += text_find_replace(find, replace_with, scope_element, exceptions, mode='part')
        return output
    if exceptions:
        for exception in exceptions:
            if scope.replace('\\', '/') == exception.replace('\\', '/'):
                return output
    if os.path.isfile(scope):
        try:
            # file_content = c.load_file(scope)  # faster to read without reformatting
            with open(scope) as file_buffer:
                file_content = file_buffer.read()
            if file_content.casefold().count(find.casefold()) > 0:
                if 'include' in mode:
                    output = file_content[
                             file_content.rfind('#include', 0, file_content.casefold().find(find.casefold())):
                             file_content.find('\n', file_content.casefold().find(find.casefold()))]
                elif replace_with is not None:
                    # new_file_content = ''
                    output += f'\t{file_content.casefold().count(find.casefold())} replaced in {scope}\n'
                    index_line = 1
                    content_parts = file_content.casefold().split(find.casefold())
                    for content_part in content_parts:
                        index_line += content_part.count('\n')
                        text_line = file_content.split('\n')[index_line - 1]
                        if content_part != content_parts[-1]:
                            output += f'\t\tin line {index_line} "{text_line}"\n'
                        # new_file_content += '\n'.join(file_content.split('\n')[:index_line - 1])
                        # new_file_content += text_line.replace(find, replace_with)
                    new_file_content = file_content.replace(find, replace_with)
                    with open(scope, 'w') as file:
                        file.write(new_file_content)
                else:
                    output += f'\tin {scope} found {file_content.casefold().count(find.casefold())}:\n'
                    index_line = 1
                    for content_part in file_content.casefold().split(find.casefold())[:-1]:
                        index_line += content_part.count('\n')
                        text_line = file_content.split('\n')[index_line - 1]
                        output += f'\t\tin line {index_line} "{text_line}"\n'
            elif 'initiate' in mode:
                output += f'\tfound none\n'
        except UnicodeDecodeError:
            raise InternalWarning(f"file {scope} unreadable")
    elif os.path.isdir(scope):
        file_paths = os.listdir(scope)
        for file_path in file_paths:
            output += text_find_replace(find, replace_with, f'{scope}/{file_path}', exceptions, mode='part')
    if 'initiate' in mode:
        log.info(output)
    return output


def update_links_to_inc(new_path, in_file_or_folder, inc_file=None, overwrite=True):
    """
    internal function triggered when a .inc file is moved.
     needs to be a separate function to call itself without triggering the rest of the move function
    :param new_path:
    :param in_file_or_folder:
    :param inc_file:
    :param overwrite:
    :return: logs of updated #include paths
    """
    file_exceptions = [r"O:\Lord of the Mods\_LIBRARY\AotR-override\AOTR8\aotr\data\ini\eva.ini",
                       r"O:\Lord of the Mods\_LIBRARY\AotR-override\AOTR8\aotr\data\ini\gamelodpresets.ini"]
    folder_exceptions = ["default", "obsolete"]
    output = ''
    line_include = ''
    old_path = ''
    if os.path.isdir(in_file_or_folder):
        folders_paths = os.listdir(in_file_or_folder)
        for folder_path in folders_paths:
            if folder_path in folder_exceptions:
                continue
            output += update_links_to_inc(
                new_path=new_path, in_file_or_folder=f'{in_file_or_folder}/{folder_path}', inc_file=inc_file)
    elif os.path.isfile(in_file_or_folder) and in_file_or_folder.endswith('.ini'):
        if in_file_or_folder in [_.replace('\\', '/') for _ in file_exceptions]:
            return ''
        line_include += text_find_replace(find=new_path.split('/')[-1], scope=in_file_or_folder, mode='include')
        if line_include:
            old_path = in_file_or_folder
    if old_path:
        output += f'in file {in_file_or_folder}:\n'
        with open(in_file_or_folder) as file_stream:
            lines = file_stream.readlines()
        new_content = ''
        line_counter = 0
        for line in lines:
            line_counter += 1
            if "#include" in line and line.strip()[0] not in INI_COMMENTS and inc_file.casefold() in line.casefold():
                path_old_include, path_new_include = '', ''
                if line_include in line:
                    path_old_include = line_include.strip()[len('#include "'):line_include.strip().rfind('"')]
                    path_absolute_include = new_path
                    path_new_include = os.path.relpath(path_absolute_include, '/'.join(old_path.split('/')[:-1]))
                elif line_include not in line:
                    path_old_include = line.strip()[len('#include "'):line.strip().rfind('"')]
                    path_absolute_include = os.path.normpath(os.path.join(os.path.dirname(old_path), path_old_include))
                    path_new_include = os.path.relpath(path_absolute_include, '/'.join(old_path.split('/')[:-1]))
                if path_old_include != path_new_include:
                    new_content += line.replace(path_old_include, path_new_include)
                    output += (f'\tin line {line_counter} updated #include "{path_old_include}"'
                               f'\n\t\tto #include "{path_new_include}"\n')
                else:
                    new_content += line
                    output += f'\tin line {line_counter} #include "{path_old_include}" left unchanged.\n'
            else:
                new_content += line
        if ''.join(lines) != new_content and overwrite is True:
            with open(in_file_or_folder, 'w') as file_overwritten:
                file_overwritten.write(new_content)
    log.info(output)
    return output


def update_links_in_ini(old_path, new_path, mode=0):
    """
    Internal function triggered when a .ini file is moved
    :param old_path:
    :param new_path:
    :param mode: 0 | 1
    :return:
    """
    file_to_open = ''
    if mode == 1:
        file_to_open = old_path
    output = f'in file {file_to_open or new_path}:\n'
    with open(file_to_open or new_path) as file_checked:
        lines = file_checked.readlines()
    new_content = ''
    line_counter = 0
    for line in lines:
        line_counter += 1
        if "#include" in line and line.strip()[0] not in INI_COMMENTS:
            path_old_include = line.strip()[len('#include "'):line.strip().rfind('"')]
            path_absolute_include = os.path.normpath(os.path.join(os.path.dirname(old_path), path_old_include))
            path_new_include = os.path.relpath(path_absolute_include, '/'.join(new_path.split('/')[:-1]))
            if path_old_include != path_new_include:
                new_content += line.replace(path_old_include, path_new_include)
                output += (f'\tin line {line_counter} updated #include "{path_old_include}"'
                           f'\n\t\tto "{path_new_include}"\n')
            else:
                new_content += line
                output += f'\tin line {line_counter} #include "{path_old_include}" left unchanged.\n'
        else:
            new_content += line
    if ''.join(lines) != new_content and mode == 0:
        with open(new_path, 'w') as file_overwritten:
            file_overwritten.write(new_content)
    return output


def move_file(full_path, to_folder, mode=0):
    """moves a given file to a given folder and updates the references to or in this file."""
    output = ''
    file_name = full_path.replace('\\', '/').split('/')[-1]
    to_folder = to_folder.replace('\\', '/')
    try:
        if mode == 0:
            output += f'{datetime.now()}'
            output += f' command: move {full_path}\n\tto {to_folder}\n'
            shutil.move(full_path, f'{to_folder}/{file_name}')
        if file_name.endswith('.inc'):
            ini_folder = to_folder[:to_folder.find('/data/ini') + len('/data/ini')]
            output += update_links_to_inc(
                new_path=f'{to_folder}/{file_name}', in_file_or_folder=ini_folder, inc_file=file_name)
        elif file_name.endswith('.ini'):
            output += update_links_in_ini(old_path=full_path, new_path=f'{to_folder}/{file_name}', mode=mode)
    except shutil.Error:
        raise InternalError('erroneous path')
    log.info(output)
    return output


def duplicates_find(of_object_or_file, in_file_or_directory=None):
    """
    Finds the duplicates in a given file or directory. Is recurrent.
    :param of_object_or_file: the object or file of objects to look for duplicates
    :param in_file_or_directory: string path of the file to load
    :return: logs of the values commented out
    """
    if in_file_or_directory is None:
        in_file_or_directory = of_object_or_file
    space = ' '
    output = f'{datetime.now()}'
    output += f' command: find duplicates from {of_object_or_file} in {in_file_or_directory}:\n'
    if os.path.isfile(in_file_or_directory):
        with open(in_file_or_directory) as file_buffer:
            file_lines = file_buffer.readlines()
    elif os.path.isdir(in_file_or_directory):
        for file_or_directory in os.listdir(in_file_or_directory):
            output += duplicates_find(of_object_or_file, file_or_directory)
    if isinstance(of_object_or_file, c.ConstructLevel):
        items_to_look_for = of_object_or_file
    elif isinstance(of_object_or_file, c.ConstructFile):
        items_to_look_for = of_object_or_file
    elif os.path.isfile(of_object_or_file):
        items_to_look_for = c.ConstructFile(of_object_or_file)
        if of_object_or_file.endswith('.str'):
            space = ':'
    else:
        raise InternalError(f"wrong input type {of_object_or_file}")
    items_number = len(items_to_look_for)
    for item_index in range(1, items_number):
        is_duplicated = False
        if isinstance(items_to_look_for[item_index], dict):
            continue
        item_title = items_to_look_for[item_index][0].copy()
        item_phrase = (
            rf"{item_title['class']}\s?{space}\s?{item_title['name'].replace('?', r'\?')}\s"
            .replace('+', r'\+')
        )
        if find_result := re.findall(item_phrase, '\n'.join(file_lines)):
            if of_object_or_file == in_file_or_directory and len(find_result) > 1:
                is_duplicated = True
            elif of_object_or_file != in_file_or_directory:
                is_duplicated = True
            else:
                is_duplicated = False
        if is_duplicated:
            title = f"{items_to_look_for[item_index][0]['class']}:{items_to_look_for[item_index][0]['name']}\n"
            line_numbers = []
            for line_index in range(len(file_lines)):
                if title.casefold() in file_lines[line_index].casefold() and '//' not in file_lines[line_index]:
                    line_numbers.append(str(line_index + 1))
            output_line = ('\tline ' + ', '.join(line_numbers) + ' ' + title)
            if len(line_numbers) > 1 and output_line not in output:
                output += output_line
    return output


def spot_duplicates_in_file(file_path: str) -> str:
    # 1. Flatten delimiters into an O(1) lookup set.
    # This grabs all valid block starters (like 'Object', 'Weapon', 'StringKey')
    delimiters, start_level = c.recognize_structure(file_path)
    if file_path.endswith('.ini') or file_path.endswith('.str') or file_path.endswith('.inc'):
        valid_starters = {word for word in delimiters[start_level]}
    else:
        raise InternalError("invalid input")

    # 2. defaultdict automatically creates a list for new keys.
    # We will map: "Object FakeUnit" -> ["10", "45"]
    tracker = defaultdict(list)

    with open(file_path, 'r') as file_stream:
        # Iterating directly over the stream is faster and saves memory
        for line_index, raw_line in enumerate(file_stream):

            # Efficiently find the earliest comment sign and slice the string
            comment_idx = min([raw_line.find(com) for com in INI_COMMENTS if com in raw_line] + [len(raw_line)])
            clean_line = raw_line[:comment_idx].strip()

            if not clean_line:
                continue

            # Treat '=' and ':' as spaces to match how constructor.py isolates words
            words = clean_line.replace('=', ' ').replace(':', ' ').split()
            if not words:
                continue

            first_word = words[0]

            # 3. Only track lines that declare a recognized block!
            if first_word in valid_starters:
                # Reconstruct a perfectly clean title (fixes weird spacing issues)
                if file_path.endswith('.str') and len(words) >= 2:
                    normalized_title = f"{words[0]}:{words[1]}"
                else:
                    normalized_title = ' '.join(words[:2])

                    # Append the 1-based line number to this title's list
                tracker[normalized_title].append(str(line_index + 1))

    # 4. Build the final output string only for duplicates
    output = ""
    for title, line_numbers in tracker.items():
        if len(line_numbers) > 1:
            output += f"\t{title} -- line {', '.join(line_numbers)};\n"

    if output:
        return f"{datetime.now()} command: find duplicates in {file_path}:\n{output}"

    return ""


def spot_duplicates_from_file_in_file(src_file_path: str, dst_file_path: str) -> str:
    # 1. Flatten delimiters into an O(1) lookup set.
    # This grabs all valid block starters (like 'Object', 'Weapon', 'StringKey')
    delimiters, start_level = c.recognize_structure(src_file_path)
    if src_file_path.endswith('.ini') or src_file_path.endswith('.str') or src_file_path.endswith('.inc'):
        valid_starters = {word for word in delimiters[start_level]}
    else:
        raise InternalError("invalid input")

    # 2. defaultdict automatically creates a list for new keys.
    # We will map: "Object FakeUnit" -> ["10", "45"]
    tracker = defaultdict(list)

    with open(src_file_path, 'r') as file_stream:
        # Iterating directly over the stream is faster and saves memory
        for line_index, raw_line in enumerate(file_stream):

            # Efficiently find the earliest comment sign and slice the string
            comment_idx = min([raw_line.find(com) for com in INI_COMMENTS if com in raw_line] + [len(raw_line)])
            clean_line = raw_line[:comment_idx].strip()

            if not clean_line:
                continue

            # Treat '=' and ':' as spaces to match how constructor.py isolates words
            words = clean_line.replace('=', ' ').replace(':', ' ').split()
            if not words:
                continue

            first_word = words[0]

            # 3. Only track lines that declare a recognized block!
            if first_word in valid_starters:
                # Reconstruct a perfectly clean title (fixes weird spacing issues)
                if src_file_path.endswith('.str') and len(words) >= 2:
                    normalized_title = f"{words[0]}:{words[1]}"
                else:
                    normalized_title = ' '.join(words[:2])

                    # Append the 1-based line number to this title's list
                tracker[normalized_title].append(str(line_index + 1))

    # 4. Build the final output string only for duplicates
    output = ""
    for title, line_numbers in tracker.items():
        if len(line_numbers) > 1:
            output += f"\t{title} -- line {', '.join(line_numbers)};\n"

    if output:
        return f"{datetime.now()} command: find duplicates from {src_file_path} in {dst_file_path}:\n{output}"

    return ""


def spot_duplicates_in_directory(file: str, directory: str) -> str:
    if not os.path.isfile(file) or not os.path.isdir(directory):
        raise InternalError("wrong input")
    output = ''
    for item in os.listdir(directory):
        next_path = f"{directory}/{item}"
        if os.path.isfile(next_path):
            output += spot_duplicates_from_file_in_file(file, next_path)
        elif os.path.isdir(next_path):
            output += spot_duplicates_in_directory(file, next_path)
    if output:
        return f"{datetime.now()} command: find duplicates in {directory}:\n{output}"
    return "nothing found"


no_reference_params = ['KindOf']
no_reference_values = ['Yes', 'No', 'None', 'NONE', 'ALL']
reference_value_dict = {
    'OBJECT:': '/data/lotr.str'
}


def link_check(construct):
    if isinstance(construct, str):
        if os.path.isfile(construct):
            construct = c.ConstructFile(construct)
            link_check(construct)
        else:
            raise InternalError(f"invalid path {construct}")
    for element in construct:
        if isinstance(element, c.ConstructLevel):
            link_check(element)
        elif isinstance(element, dict):
            if 'statement' in element:
                if ' = ' in element['statement'].strip():
                    param, value = element['statement'].strip().split(' = ')
                    if value.isnumeric() or value in no_reference_values:
                        pass
                    elif param in no_reference_params:
                        pass
                    else:
                        for ref_value_key in reference_value_dict:
                            if value.startswith(ref_value_key):
                                reference = value[len(ref_value_key):]
                                print(f'ref: {reference}')
                                break
                else:
                    print(f'line : {element['statement'].strip()}')
        else:
            print(element)


if __name__ == "__main__":
    link_check(
        r"O:\Lord of the Mods\_LIBRARY\BfME2-clean\!BfME2\data\ini\object\neutral\barrowwight.ini"
    )
