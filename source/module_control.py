import os
from shutil import copy2, move
from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
from tkinter.simpledialog import askstring
from datetime import datetime
import xxhash
from glob import glob
import json
from enum import StrEnum
from typing import Literal

import source.core as core
import source.shared as s

SNAPSHOT_DIRECTORY = './snapshots'
SNAPSHOT_NAME = 'file_snapshot_'
SNAPSHOT_COMPARISON_DIRECTORY = './snapshot_comparisons'
COMPARISON_NAME = 'comparison_'


class Transfer(StrEnum):
    MOVE = 'move'
    COPY = 'copy'
    DELETE = 'delete'
    REMOVE = 'remove'


class Property(StrEnum):
    TRANSFER_TYPE = "class"
    NAME = "name"
    GAME = "game"
    LAUNCH = "launch"
    ACTIVE = "active"
    OVERRIDES = "ancestor"
    OVERRODE_BY = "heir"
    DESCRIPTION = "description"
    CHANGES = "changes"


DEFINITION_NAME = '_definition.json'
DEFINITION_CLASSES = ['General', 'Clone', 'Foundling', 'Template']
DEFINITION_CLASS_TEMPLATE = {
    Property.TRANSFER_TYPE: '',
    Property.NAME: '',
    Property.GAME: '',
    Property.LAUNCH: "",
    Property.ACTIVE: False,
    Property.OVERRIDES: '',
    Property.OVERRODE_BY: '',
    Property.DESCRIPTION: '',
    Property.CHANGES: {}
}


class Change(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


PRINT_COLORS = {
    'information': '\033[96m',
    'warning': '\033[93m',
    'error': '\033[91m',
    'end': '\033[0m',
}


def log(output):
    """ Saves the given text into the main change log. """
    text = ''
    if TEST:
        for importance_level in PRINT_COLORS[:-1]:
            if importance_level in output:
                text = (output[:output.index(importance_level)] + PRINT_COLORS[importance_level] + importance_level
                        + PRINT_COLORS['end'] + output[output.index(importance_level) + len(importance_level):])
        if text:
            print(text)
        else:
            print(output)
    else:
        date = str(datetime.now()) + '\t'
        if not os.path.isdir(s.LOG_PATH):
            os.mkdir(s.LOG_PATH)
        try:
            with open(f'{s.LOG_PATH}/main_change_log.txt', 'a') as log_buffer:
                log_buffer.write(date + output + '\n')
        except FileNotFoundError:
            with open(f'{s.LOG_PATH}/main_change_log.txt', 'w') as log_buffer:
                log_buffer.write(date + output + '\n')
    return output


class Definition(dict):
    """ A dictionary-based class with predefined keys and functions that manipulate modules. """

    def __init__(self, initial_dict=None):
        super().__init__()
        for key in DEFINITION_CLASS_TEMPLATE:
            try:
                self[key] = DEFINITION_CLASS_TEMPLATE[key].copy()
            except AttributeError:
                self[key] = DEFINITION_CLASS_TEMPLATE[key]
            if initial_dict is not None:
                if key in initial_dict:
                    self[key] = initial_dict[key]

    def edit(self, **key_args):
        return definition_edit(self, **key_args)

    def retrieve(self):
        try:
            module_reverse(module_object=self, transfer=Transfer.REMOVE)
            return True
        except s.InternalError:
            return False

    def attach(self):
        try:
            module_attach(self)
            return True
        except s.InternalError:
            try:
                module_attach(module_directory=f"{core.library}/{self[Property.NAME]}")
                return True
            except s.InternalError:
                # module_attach(module_directory=self['path'])
                return True

    def reload(self):
        if self.retrieve():
            if self.attach():
                return True
            else:
                return False
        else:
            return False

    def reload_after_class_change(self):
        if self[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]:
            module_reverse(self, transfer=Transfer.DELETE, check_type='pass')
            module_attach(self)
        if self[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
            module_reverse(self, transfer=Transfer.COPY, check_type='pass')
            module_attach(self)

    def extract(self):
        module_reverse(module_object=self, transfer=Transfer.COPY)


DEFINITION_EXAMPLE = Definition()


def definition_write(definition_object=None, module_directory=None, return_type='object', changes_source='directory',
                     **key_args):
    """
    Reads a definition and formats it into text, that can be saved into a text file.
    :param definition_object: (optional) a definition dictionary-like object
    :param module_directory: (optional) a path to identify a module and to save the definition to
    :param return_type: 'object' (+) 'save' - if 'object', returns a definition dictionary-like object.
    If 'text save' or 'object save', saves the definition into a file.
    :param changes_source: (optional) 'directory' | 'snapshot' | 'comparison' | >the directory to base it upon<
    - passed to initiate_comparison
    :param key_args: (optional) key - arguments pairs for values to change before saving.
    :return: according to the return_type
    """
    if module_directory is None:
        if definition_object is None:
            module_directory = askdirectory(title=f'{s.PROGRAM_NAME}: select the directory to define as a module',
                                            initialdir=core.library)
            if not module_directory:
                raise s.InternalError('directory not selected')
        elif os.path.isdir(f"{core.library}/{definition_object[Property.NAME]}"):
            module_directory = f"{core.library}/{definition_object[Property.NAME]}"
    if definition_object is not None:
        module_name = definition_object[Property.NAME]
    elif module_directory is not None:
        module_name = module_directory.split('/')[-1]
    else:
        module_name = 'default name'
    if definition_object is None:
        if os.path.isfile(f'{module_directory}/{DEFINITION_NAME}'):
            definition_object = definition_read(module_path=f'{module_directory}')
        else:
            definition_object = Definition()
    if Property.TRANSFER_TYPE in key_args:
        definition_object[Property.TRANSFER_TYPE] = key_args[Property.TRANSFER_TYPE]
    else:
        definition_object[Property.TRANSFER_TYPE] = DEFINITION_CLASSES[0]
    try:
        if not definition_object[Property.GAME] and os.path.isdir(module_directory):
            game_folders = os.listdir(module_directory)
            for folder in game_folders:
                if os.path.isdir(f'../{folder}'):
                    definition_object[Property.GAME] = folder
                    break
            if not definition_object[Property.GAME]:
                definition_object[Property.GAME] = module_name.split('-')[0]
    except IndexError:
        pass
    if not definition_object[Property.NAME] and module_directory:
        definition_object[Property.NAME] = module_directory.split('/')[-1]
    if Property.OVERRIDES in key_args:
        definition_object[Property.OVERRIDES] = key_args[Property.OVERRIDES]
    if Property.OVERRODE_BY in key_args:
        definition_object[Property.OVERRODE_BY] = key_args[Property.OVERRODE_BY]
    if not definition_object[Property.CHANGES]:
        try:
            definition_object[Property.ACTIVE], definition_object[Property.CHANGES] = initiate_comparison(
                module_directory, changes_source=changes_source)
        except s.InternalError:
            pass
    if 'save' in return_type:
        with open(f'{module_directory}/{DEFINITION_NAME}', 'w') as definition_buffer:
            json.dump(definition_object, definition_buffer, indent=4)
            log(f'definition saved in {module_directory}')
    elif 'object' in return_type:
        return definition_object


# note in #lord_of_the_mods definition_write, definition_edit and initiate_comparison have been fused in properties_set
def definition_read(module_path=None):
    """
    Reads the definition of an object and loads it into a dictionary.
    :param module_path: (optional) a module path to check if a definition file exists
    :return: a definition dictionary-like class
    """
    if module_path is not None:
        if module_path in core.exceptions:
            raise s.InternalError("the provided path is defined as exception")
    if module_path is None or module_path == "":
        module_path = askdirectory(title=f'{s.PROGRAM_NAME}: select the module directory',
                                   initialdir=core.library)
        if module_path == "":
            raise s.InternalError('directory not selected')
    if os.path.isfile(f'{module_path}/{DEFINITION_NAME}'):
        with open(f'{module_path}/{DEFINITION_NAME}') as definition_buffer:
            return Definition(initial_dict=json.load(definition_buffer))
    else:
        # return Definition()
        raise s.InternalError('no definition under given path')


def definition_edit(definition_object=None, module_path=None, **key_args):
    """
    Edits parameters of a Definition object
    :param definition_object: (optional) a Definition object to edit
    :param module_path: (optional) the path to a module with a definition file.
    :param key_args: key - arguments pairs of parameters to changes.
    :return: the edited Definition object.
    """
    if definition_object is None:
        if module_path is None:
            module_path = askdirectory(title=f'{s.PROGRAM_NAME}: select the module directory',
                                       initialdir=core.library)
        if module_path:
            definition_object = definition_read(module_path=module_path)
        if not definition_object:
            raise s.InternalError('definition missing')
    else:
        if module_path is None:
            module_path = f"{core.library}/{definition_object[Property.NAME]}"
    for key in key_args:
        if key in DEFINITION_EXAMPLE:
            if key == Property.NAME:
                list_modules = modules_filter(return_type='names')
                for module_name in list_modules:
                    if key_args[Property.NAME] == module_name:
                        raise s.InternalError('definition_edit: name already in use')
                for module_name in list_modules:
                    module_definition = definition_read(module_path=f'{core.library}/{module_name}')
                    if definition_object[Property.NAME] == module_definition[Property.OVERRIDES]:
                        definition_edit(
                            module_definition,
                            ancestor=module_definition[Property.OVERRIDES].replace(
                                definition_object[Property.NAME], key_args[Property.NAME])
                        )
                    if definition_object[Property.NAME] == module_definition[Property.OVERRODE_BY]:
                        definition_edit(
                            module_definition,
                            heir=module_definition[Property.OVERRODE_BY].replace(
                                definition_object[Property.NAME], key_args[Property.NAME])
                        )
                os.rename(
                    src=module_path, dst=f"{'/'.join(module_path.split('/')[:-1])}/{key_args[Property.NAME]}")
            definition_object[key] = key_args[key]
        else:
            raise s.InternalWarning(f'key {key} not recognized')
    return definition_write(definition_object, return_type='object save')


# TODO: check if correct business logic
def detect_new_modules():
    output = ''
    library_folders = [_ for _ in os.listdir(core.library) if _ not in core.exceptions]
    for folder in library_folders:
        if not os.path.isfile(f'{core.library}/{folder}/{DEFINITION_NAME}'):
            output += f'Registering a definition-less folder in the library - {folder}\n'
    return output


def hash_file(file_path):
    """ Returns the hash value of a file. Non-cryptographic 128 hexadecimal hash value. """
    with open(file_path, 'rb') as file_buffer:
        file_content = file_buffer.read()
    return xxhash.xxh128(file_content).hexdigest()


def hash_directory(file_or_folder, path_to_omit='', skip_first_level_files=False):
    """ Composes a dict where every file of a given directory is the key to its hash value. """
    output = {}
    if os.path.isfile(file_or_folder) and not skip_first_level_files:
        if path_to_omit:
            path_to_register = file_or_folder[file_or_folder.index(path_to_omit) + len(path_to_omit):]
        else:
            path_to_register = file_or_folder
        output[path_to_register] = hash_file(file_or_folder)
    elif os.path.isdir(file_or_folder):
        next_directory = os.listdir(file_or_folder)
        for next_folder in next_directory:
            if next_folder in core.games:
                next_directory = [next_folder]
                break
        for next_file_or_folder in next_directory:
            output.update(hash_directory(f'{file_or_folder}/{next_file_or_folder}', path_to_omit=path_to_omit))
    return output


def get_available_name(snapshot_directory, prefix=SNAPSHOT_NAME):
    """ Given a directory, returns the name of the next file to save into. """
    counter = 1
    if not os.path.isdir(snapshot_directory):
        os.mkdir(snapshot_directory)
    elif os.path.exists(f'{snapshot_directory}/{prefix}{counter}.json'):
        snapshot_list = glob(f'{snapshot_directory}/{prefix}*.json')
        try:
            suffix = ''
            while not suffix.isnumeric():
                last_snapshot = max(snapshot_list, key=os.path.getctime)
                snapshot_list.remove(last_snapshot)
                suffix = last_snapshot[last_snapshot.index(prefix) + len(prefix):last_snapshot.index('.json')]
            counter = str(int(suffix) + 1)
        except ValueError:
            counter = askstring(title=f'{s.PROGRAM_NAME}', prompt='Please give a name to the new file')
        except NameError:
            pass
    return f'{snapshot_directory}/{prefix}{counter}.json'


def select_paths(game_paths, add_paths):
    path_to_omit = ''
    if game_paths is None:
        game_paths = ['>no_path<']
    for game_path in game_paths:
        if game_path == '>no_path<':
            game_full_path = askdirectory(initialdir=f'{s.MAIN_DIRECTORY}',
                                          title=f'{s.PROGRAM_NAME}: select game directory to take a snapshot of')
            if game_full_path:
                if os.path.abspath(core.library).replace('\\', '/') in game_full_path:
                    mod_name = game_full_path[len(os.path.abspath(core.library)):].split('/')[1]
                    path_to_omit = f'{os.path.abspath(core.library).replace('\\', '/')}/{mod_name}'
                else:
                    path_to_omit = s.MAIN_DIRECTORY
                game_paths[game_paths.index('>no_path<')] = game_path
                if add_paths:
                    game_paths.append('>no_path<')
            elif len(game_paths) == 0 or game_paths == ['>no_path<']:
                raise s.InternalError('directory not selected')
        if not os.path.isdir(f'{s.MAIN_DIRECTORY}/{game_path}'):
            game_paths.remove(game_path)
    return game_paths, path_to_omit


def snapshot_take(game_paths=None, add_paths=False, return_type='path', name=None):
    """
    Takes a snapshot of a selected directory.
    :param game_paths: directory to take a snapshot of.
    :param add_paths: True | False - when True, asks for new directories until cancel is pressed.
    :param return_type: 'path' | 'dict' (+) 'save' - if 'path',
     returns the path of the file where the snapshot has been saved.
    If 'dict', returns the content.
    :param name:
    :return: according to return-type.
    """

    game_paths, path_to_omit = select_paths(game_paths, add_paths)

    game_snapshot = {"date": f"{datetime.now()}"}
    for game_path in game_paths:
        game_snapshot.update(hash_directory(game_path, path_to_omit=path_to_omit))
    if return_type == 'dict':
        log('snapshot_take successful')
        return game_snapshot
    if not name:
        snapshot_path = get_available_name(SNAPSHOT_DIRECTORY)
    elif os.path.isfile(f'{SNAPSHOT_DIRECTORY}/{SNAPSHOT_NAME}{name}.json'):
        if os.path.isfile(f'{SNAPSHOT_DIRECTORY}/{SNAPSHOT_NAME}{name}-{datetime.now().date()}.json'):
            snapshot_path = f'{SNAPSHOT_DIRECTORY}/{SNAPSHOT_NAME}{name}-{datetime.now()}.json'.replace(":", "_")
        else:
            snapshot_path = f'{SNAPSHOT_DIRECTORY}/{SNAPSHOT_NAME}{name}-{datetime.now().date()}.json'
    else:
        snapshot_path = f'{SNAPSHOT_DIRECTORY}/{SNAPSHOT_NAME}{name}.json'
    with open(snapshot_path, 'w') as snapshot_buffer:
        json.dump(game_snapshot, snapshot_buffer, indent=4)
    log(f'snapshot successfully saved in file {snapshot_path}')
    if 'dict' in return_type:  # # # if 'dict save'
        return game_snapshot
    elif 'path' in return_type:
        return snapshot_path


def snapshot_compare(snap_anterior=None, snap_posterior=None, return_type: Literal['path', 'dict'] = 'path'):
    """
    Compares two snapshots, determining which files are different, unchanged, new or removed.
    :param snap_anterior: first snapshot to compare to
    :param snap_posterior: second snapshot to compare with
    :param return_type: 'path' | 'dict' - If 'path', returns the path of the file, where the comparison has been saved.
    If 'dict', does not save the result into a file, but returns it.
    :return: according to the return_type.
    """
    dict_anterior = {}
    dict_posterior = {}
    if snap_anterior is None:
        snap_anterior = askopenfilename(title=f'{s.PROGRAM_NAME}: choose the base snapshot to compare with',
                                        initialdir=SNAPSHOT_DIRECTORY)
        if not snap_anterior:
            raise s.InternalError('no snapshot selected')
    if isinstance(snap_anterior, dict):
        dict_anterior = snap_anterior.copy()
        snap_anterior = 'unsaved output'
    elif os.path.isfile(snap_anterior):
        with open(snap_anterior) as file_anterior:
            dict_anterior = json.load(file_anterior)
    if snap_posterior is None:
        snap_posterior = askopenfilename(title=f'{s.PROGRAM_NAME}: choose the second snapshot to compare',
                                         initialdir=SNAPSHOT_DIRECTORY)
        if not snap_posterior:
            raise s.InternalError('no snapshot selected')
    if isinstance(snap_posterior, dict):
        dict_posterior = snap_posterior.copy()
        snap_posterior = 'unsaved output'
    elif os.path.isfile(snap_posterior):
        with open(snap_posterior) as file_posterior:
            dict_posterior = json.load(file_posterior)
    dict_output = {}
    for key_name_anterior in dict_anterior:
        if key_name_anterior == 'date':
            dict_output['date_1'] = f"{snap_anterior} {dict_anterior['date']}"
            dict_output['date_2'] = f"{snap_posterior} {dict_posterior['date']}"
            continue
        try:
            if dict_anterior[key_name_anterior] == dict_posterior[key_name_anterior]:
                dict_output[key_name_anterior] = [Change.UNCHANGED, dict_anterior[key_name_anterior]]
            else:
                dict_output[key_name_anterior] = [Change.CHANGED,
                                                  dict_anterior[key_name_anterior],
                                                  dict_posterior[key_name_anterior]]
        except KeyError:
            for key_name_posterior in dict_posterior:
                if key_name_posterior.casefold() == key_name_anterior.casefold():
                    if dict_anterior[key_name_anterior] == dict_posterior[key_name_posterior]:
                        dict_output[key_name_posterior] = [Change.UNCHANGED, dict_anterior[key_name_anterior]]
                    else:
                        dict_output[key_name_posterior] = [
                            Change.CHANGED, dict_anterior[key_name_anterior], dict_posterior[key_name_posterior]]
                    break
            else:
                dict_output[key_name_anterior] = [Change.REMOVED, dict_anterior[key_name_anterior]]
    for key_name_posterior in dict_posterior:
        if key_name_posterior not in dict_anterior and key_name_posterior not in dict_output:
            dict_output[key_name_posterior] = [Change.ADDED, dict_posterior[key_name_posterior]]
    if return_type == 'dict':
        return dict_output
    else:
        comparison_path = get_available_name(SNAPSHOT_COMPARISON_DIRECTORY, COMPARISON_NAME)
        with open(comparison_path, 'w') as last_comparison:
            json.dump(dict_output, last_comparison, indent=4)
        log(f'snapshot comparison saved to {comparison_path}')
        return comparison_path


def initiate_comparison(module_directory, start_module='', changes_source='directory'):
    """
    Creates a change list for a module definition, based on provided data.
    :param module_directory: path to the module, whose definition is being created
    :param start_module: path to the present game folder to base the change on
    :param changes_source: 'directory' | 'comparison' | 'snapshot' -
    If 'directory', bases the changes on a present game folder.
    If 'comparison', bases the changes on a comparison file.
    If 'snapshot', bases the changes on the difference between present files and files in the snapshot.
    :return: tuple(active, changes)
    """
    if not os.path.isdir(module_directory):
        raise s.InternalError('provided directory is not correct')
    changes = {}
    active = False
    if os.path.isdir(changes_source):
        active = True
        snapshot_take(
            game_paths=[changes_source.split('/')[-1]], return_type='path', name=changes_source.split('/')[-1])
        current_files = hash_directory(changes_source)
        for new_file in current_files:
            if len(new_file) > 0:
                changes[new_file] = [Change.ADDED, current_files[new_file]]
    elif changes_source == 'directory':
        if not start_module:
            start_module = askdirectory(title=f'{s.PROGRAM_NAME}: select the game directory to define the mod',
                                        initialdir=s.MAIN_DIRECTORY)
        new_files_dict = hash_directory(module_directory, path_to_omit=module_directory, skip_first_level_files=True)
        if start_module and new_files_dict:
            active = False
            current_files = hash_directory(
                start_module, path_to_omit=f'{start_module[:start_module.rfind("/")]}')
            for new_file in new_files_dict:
                if new_file in current_files:
                    changes[new_file] = [Change.CHANGED, new_files_dict[new_file], current_files[new_file]]
                else:
                    changes[new_file] = [Change.ADDED, new_files_dict[new_file]]
        elif start_module and not new_files_dict:
            active = True
            current_files = hash_directory(start_module, path_to_omit=s.MAIN_DIRECTORY)
            for new_file in current_files:
                changes[new_file] = [Change.ADDED, current_files[new_file]]
        files_to_remove = askopenfilenames(title=f'{s.PROGRAM_NAME}: select files to remove',
                                           initialdir=s.MAIN_DIRECTORY)
        for file_path in files_to_remove:
            changes[file_path] = [Change.REMOVED, hash_file(file_path)]
        snapshot_take(
            game_paths=[module_directory], name=module_directory.split('/')[-1])
    elif changes_source == 'comparison':
        selected_comparison = askopenfilename(
            title=f'{s.PROGRAM_NAME}: select the snapshot comparison to define the mod',
            initialdir=f'./{SNAPSHOT_COMPARISON_DIRECTORY}')
        if os.path.isfile(selected_comparison):
            active, changes = evaluate_changes(selected_comparison)
        else:
            raise s.InternalError('comparison not selected')
    elif changes_source == 'snapshot':
        selected_snapshot = askopenfilename(
            title=f'{s.PROGRAM_NAME}: select the snapshot taken before the changes',
            initialdir=f'./{SNAPSHOT_DIRECTORY}')
        if os.path.isfile(selected_snapshot):
            with open(selected_snapshot) as snapshot_buffer:
                snapshot_dict = json.load(snapshot_buffer)
            game_paths = []
            for path_key in snapshot_dict:
                if 'date' == path_key:
                    continue
                elif path_key.replace('\\', '/').split('/')[1] not in game_paths:
                    game_paths.append(path_key.replace('\\', '/').split('/')[1])
            new_snapshot = snapshot_take(
                game_paths=game_paths, return_type='dict save', name=module_directory.split('/')[-1])
            comparison_dict = snapshot_compare(selected_snapshot, new_snapshot, return_type='dict')
            active, changes = evaluate_changes(comparison_dict)
        else:
            raise s.InternalError('snapshot not selected')
    log(f'comparison generated for {module_directory}')
    return active, changes


def evaluate_changes(comparison):
    changes = {}
    if os.path.isfile(comparison):
        with open(comparison) as comparison_buffer:
            comparison_dict = json.load(comparison_buffer)
    elif isinstance(comparison, dict):
        comparison_dict = comparison
    else:
        raise s.InternalError('no comparison')
    for path_key in comparison_dict:
        if comparison_dict[path_key][0] != Change.UNCHANGED and path_key != 'date_1' and path_key != 'date_2':
            changes[path_key] = comparison_dict[path_key]
    active = True
    return active, changes


test_previous_src = ''
test_previous_dst = ''
test_previous_type = ''
error_sensitivity = True


def transfer_switch(src, dst='', transfer_type: Transfer = Transfer.COPY, error_sensitive=True):
    if TEST:
        simulate_transfer(src, dst, transfer_type)
    else:
        make_transfer(src, dst, transfer_type, error_sensitive)


def simulate_transfer(src, dst='', transfer_type: Transfer = Transfer.COPY):
    global test_previous_src, test_previous_dst, test_previous_type
    output = ''
    if os.path.exists(src):
        if transfer_type == Transfer.DELETE:
            output += log(f'for deletion: {src}')
            if not os.path.isfile(f"{dst}/{src.split('/')[-1]}"):
                output += log(f"warning: original absent {dst}/{src.split('/')[-1]}")
        else:
            output += log(f'source: {src}')
    else:
        output += log(f'error: source absent {src}')
    if dst and transfer_type != Transfer.DELETE:
        if os.path.exists(dst):
            if os.path.isfile(f"{dst}/{src.split('/')[-1]}") and test_previous_src == f"{dst}/{src.split('/')[-1]}":
                if test_previous_type == Transfer.DELETE:
                    output += log(f'information: destination {test_previous_src} deleted')
                elif test_previous_type == Transfer.MOVE:
                    output += log(f'destination: {dst} (correct)')
                else:
                    output += log(f"warning: destination present {dst}/{src.split('/')[-1]}")
            else:
                output += log(f'destination: {dst}')
        else:
            output += log(f'error: destination absent {dst}')
    test_previous_src, test_previous_dst, test_previous_type = src, dst, transfer_type
    return output


def make_transfer(src, dst='', transfer_type: Transfer = Transfer.COPY, error_sensitive=True):
    """
    Tries to transfer the file from source to destination.
    :param src: path of the file to transfer
    :param dst: path of the directory to transfer to
    :param transfer_type: 'copy' | 'move' | 'delete' - transfer type.
    :param error_sensitive: if True, stops if an error is detected.
    :return: text gathering the report of the transfer.
    """
    global error_sensitivity
    try:
        if transfer_type == Transfer.COPY:
            ensure_path_exists(src, dst)
            copy2(src, dst)
        elif transfer_type == Transfer.MOVE:
            ensure_path_exists(src, dst)
            move(src, dst)
        elif transfer_type == Transfer.DELETE:
            os.remove(src)
    except OSError as err:
        if src.endswith('.bak'):
            new_src = src.replace('.bak', '')
            return make_transfer(new_src, dst, transfer_type, error_sensitive)
        elif src.endswith('.disabled'):
            new_src = src.replace('.disabled', '.big')
            return make_transfer(new_src, dst, transfer_type, error_sensitive)
        elif src.endswith('.big'):
            if os.path.isfile(f'{src}.bak'):
                return make_transfer(f'{src}.bak', dst, transfer_type, error_sensitive)
            elif os.path.isfile(f'{src.replace('.big', '.disabled')}'):
                return make_transfer(f'{src.replace('.big', '.disabled')}', dst, transfer_type, error_sensitive)
        if error_sensitive:
            if err.strerror:
                error_message = err.strerror
            elif err.args[0]:
                error_message = err.args[0]
            else:
                error_message = ' - '
            do_proceed = s.invoke_choice(
                title='file transfer error',
                text=f'Error with {src}\n{error_message}\n'
                     ' Do you wish to continue displaying each error,\n'
                     ' continue skipping errors or revert the mod transfer?',
                buttons=(
                    {s.KEY_LABEL: 'continue', s.KEY_RETURN: True, s.KEY_INFO: ''},
                    {s.KEY_LABEL: 'skip', s.KEY_RETURN: False, s.KEY_INFO: ''},
                    {s.KEY_LABEL: 'revert', s.KEY_RETURN: None, s.KEY_INFO: ''})
            )
            if do_proceed is True:
                pass
            elif do_proceed is False:
                error_sensitivity = False
            elif do_proceed is None:
                raise s.InternalError(err.strerror)


def ensure_path_exists(file_path, check_path='..'):
    """ Creates the directories in the ARCHIVE and LIBRARY folders where the files will be transferred. """
    # # # 'if' added for case of transfer_switch - copy.
    if core.library in file_path:
        check_path = '/'.join(file_path.split('/')[:core.library.count('/') + 2])
        file_path = file_path[file_path.index(check_path) + len(check_path) + 1:]
    # note: changed in #lord_of_the_mods
    if not os.path.exists(check_path):
        os.makedirs(check_path, exist_ok=True)
    path_folders = file_path.split('/')
    file_path_part = ''
    for file_folder in path_folders[1:-1]:
        file_path_part += f'/{file_folder}'
        if not os.path.exists(f'{check_path}{file_path_part}'):
            os.mkdir(f'{check_path}{file_path_part}')


def check_library(module_object):
    changes = module_object[Property.CHANGES]
    library_missing = False
    for file in changes:
        if not os.path.isfile(f"{core.library}/{module_object[Property.NAME]}/{file}"):
            library_missing = True
            break
    return library_missing


def check_relative(module_object, relation):
    if Property.OVERRODE_BY == relation:
        if module_object[Property.OVERRODE_BY]:
            if os.path.isfile(f"{core.library}/{module_object[Property.OVERRODE_BY]}/{DEFINITION_NAME}"):
                heir_module_object = definition_read(f"{core.library}/{module_object[Property.OVERRODE_BY]}")
                if heir_module_object[Property.ACTIVE]:
                    return heir_module_object
    elif Property.OVERRIDES == relation:
        if module_object[Property.OVERRIDES]:
            ancestor_directory = f"{core.library}/{module_object[Property.OVERRIDES]}"
            if os.path.isfile(f'{ancestor_directory}/{DEFINITION_NAME}'):
                ancestor_module_object = definition_read(module_path=ancestor_directory)
                if not ancestor_module_object[Property.ACTIVE]:
                    return ancestor_module_object


def module_reverse(module_object, transfer: Transfer = Transfer.COPY, check_type='hash, heir'):
    """
    Detaches the module from the game directory, by retrieving all its files to the LIBRARY.
    :param module_object: (optional) the dictionary-based Definition object
    :param transfer: 'copy' | 'move' | 'delete' - transfer type.
    :param check_type: 'definition' | 'snapshot' | 'pass' - check if the module is indeed in the game folder
    If 'pass', does not check, just tries to detach what it can.
    :return: logs about the transfer details.
    """
    global error_sensitivity
    if module_object is None:
        raise s.InternalError('missing object')
    module_name = module_object[Property.NAME]
    comparison_dict = module_object[Property.CHANGES]
    if not os.path.isdir(f'{core.library}/{module_name}'):
        os.mkdir(f'{core.library}/{module_name}')
    if transfer == Transfer.REMOVE:
        if module_object[Property.ACTIVE] is False and check_type != 'pass':
            raise s.InternalError('deactivation of inactive module aborted')
        if module_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]:
            transfer = Transfer.MOVE
        elif module_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1] and check_library(module_object):
            transfer = Transfer.MOVE
        elif module_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
            transfer = Transfer.DELETE
    if not comparison_dict:
        raise s.InternalError('comparison missing')

    error_sensitivity = True
    if Property.OVERRODE_BY in check_type:
        if heir_module_object := check_relative(module_object, Property.OVERRODE_BY):
            if not module_reverse(heir_module_object, transfer=Transfer.REMOVE):
                raise s.InternalError('heir module not retrieved')
    elif check_type == 'pass':
        error_sensitivity = False
    output = ''
    try:
        for path_key in comparison_dict:
            file_path_source = f"{s.MAIN_DIRECTORY}/{path_key}"
            file_path_game = f"{s.MAIN_DIRECTORY}/{'/'.join(path_key.split('/')[:-1])}"
            file_path_module = (f"{core.library}/{module_name}/"
                                f"{'/'.join(path_key.split('/')[0:-1])}")
            file_path_archive = f"{core.archive}/{module_name}/{path_key}"
            if 'hash' in check_type:
                pass
            if comparison_dict[path_key][0] == Change.UNCHANGED:
                pass
            elif comparison_dict[path_key][0] == Change.CHANGED:
                if transfer in Transfer:
                    output += transfer_switch(file_path_source, file_path_module, transfer, error_sensitivity)
                if transfer == Transfer.MOVE or transfer == Transfer.DELETE:
                    output += transfer_switch(file_path_archive, file_path_game, Transfer.MOVE, error_sensitivity)
            elif comparison_dict[path_key][0] == Change.ADDED:
                output += transfer_switch(file_path_source, file_path_module, transfer, error_sensitivity)
            elif comparison_dict[path_key][0] == Change.REMOVED:
                if transfer == Transfer.MOVE or transfer == Transfer.DELETE:
                    output += transfer_switch(file_path_archive, file_path_game, Transfer.MOVE, error_sensitivity)
                else:
                    pass
    except s.InternalError:
        log(f'module_reverse {module_name} CANCELLED\n{output}')
        module_attach(module_directory=f'{core.library}/{module_name}', check_type='pass')
        return False
    if TEST:
        raise s.InternalError('under TEST phase: module_reverse not applied')
    definition_edit(definition_object=module_object, active=False)
    log(f'module_reverse {module_name}\n{output}')
    return True


def module_detect_override(module: Definition):
    """

    :param module:
    :return:
     - time-optimization might be required -
    """
    new_changes = module[Property.CHANGES]
    active_modules = modules_filter(active=True)
    for active_module in active_modules:
        if module[Property.OVERRIDES] == active_module[Property.NAME]:
            return active_module
    for active_module in active_modules:
        if not active_module[Property.OVERRODE_BY]:
            for active_file in active_module[Property.CHANGES]:
                if active_file.strip('../') in new_changes:
                    return active_module
    return False


def module_attach(module_object=None, module_directory=None, check_type='ancestor'):
    """
    Attaches a module to the game directory.
    :param module_object: (optional) dictionary-based module object
    :param module_directory: (optional) path of the module to attach
    :param check_type: 'ancestor' | 'snapshot' | 'pass' - check if the module is indeed in the LIBRARY folder
    If 'pass', does not check, just tries to attach what it can.
    :return: logs about the transfer details.
    """
    global error_sensitivity
    transfer = Transfer.MOVE
    if module_object is None:
        if module_directory is None:
            module_directory = askdirectory(title=f'{s.PROGRAM_NAME}: select module directory',
                                            initialdir=core.library)
            if not module_directory:
                raise s.InternalError('module directory missing')
        if os.path.isfile(f'{module_directory}/{DEFINITION_NAME}'):
            module_object = definition_read(module_path=module_directory)
    error_sensitivity = True
    if ancestor_module := module_detect_override(module_object):
        module_object = definition_edit(module_object, ancestor=ancestor_module[Property.NAME])
        definition_edit(ancestor_module, heir=module_object[Property.NAME])
    if Property.OVERRIDES in check_type:
        if os.path.isdir(f"{core.library}/{module_object[Property.NAME]}"):
            module_directory = f"{core.library}/{module_object[Property.NAME]}"
        else:
            raise s.InternalError('path not recognized')
        if module_object[Property.ACTIVE] is True and check_type != 'pass':
            raise s.InternalError('activation of active module aborted')
        if module_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]:
            transfer = Transfer.MOVE
        elif module_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
            transfer = Transfer.COPY
        if ancestor_module_object := check_relative(module_object, Property.OVERRIDES):
            if not module_attach(ancestor_module_object):
                raise s.InternalError('ancestor module not attached')
    elif check_type == 'pass':
        error_sensitivity = False
    module_name = module_directory.split('/')[-1]
    if not os.path.isdir(f'{core.archive}/{module_name}'):
        os.mkdir(f'{core.archive}/{module_name}')
    comparison_dict = module_object[Property.CHANGES].copy
    if not comparison_dict and os.path.isfile(f"{module_directory}/{COMPARISON_NAME}{module_name}.json"):
        with open(f"{module_directory}/{COMPARISON_NAME}{module_name}.json") as comparison_buffer:
            comparison_dict = json.load(comparison_buffer)
    if comparison_dict:
        output = ''
        try:
            for path_key in comparison_dict:
                file_path_source = f"{s.MAIN_DIRECTORY}{path_key}"
                file_path_game = f"{s.MAIN_DIRECTORY}{'/'.join(path_key.split('/')[:-1])}"
                file_path_archive = f"{core.archive}/{module_name}/{'/'.join(path_key.split('/')[0:-1])}"
                file_path_module = f"{core.library}/{module_name}/{path_key}"
                if comparison_dict[path_key][0] == Change.UNCHANGED:
                    pass
                elif comparison_dict[path_key][0] == Change.CHANGED:
                    output += transfer_switch(file_path_source, file_path_archive, transfer, error_sensitivity)
                    output += transfer_switch(file_path_module, file_path_game, transfer, error_sensitivity)
                elif comparison_dict[path_key][0] == Change.ADDED:
                    output += transfer_switch(file_path_module, file_path_game, transfer, error_sensitivity)
                elif comparison_dict[path_key][0] == Change.REMOVED:
                    output += transfer_switch(file_path_source, file_path_archive, transfer, error_sensitivity)
        except s.InternalError:
            log(f'module_attach {module_name} CANCELLED\n{output}')
            module_reverse(module_object=module_object, transfer=Transfer.REMOVE, check_type='pass')
            return False
    else:
        raise s.InternalError('comparison missing')
    if TEST:
        raise s.InternalError('Test phase: module_attach not applied')
    definition_edit(definition_object=module_object, active=True)
    log(f'module_attach {module_name}\n{output}')
    return True


def module_new(name: str, changes_source: str = ''):
    if not os.path.isdir(f'{core.library}/{name}'):
        os.mkdir(f'{core.library}/{name}')
    output = f'{name} created. \n'
    definition_write(module_directory=f'{core.library}/{name}', return_type='save',
                     changes_source=changes_source)
    return log(output)


# may not be needed
def module_copy(new_name, template_directory=None, changes_source=None):
    """
    Copies modules files into a new directory.
    :param new_name: the name of the module to create
    :param template_directory: the path to the module to copy
    :param changes_source: 'snapshot' | 'comparison' | 'directory' - passes the value to definition_write
    :return: logs about the details of the transfer
    """
    if not template_directory:
        raise s.InternalError('template not selected')
    all_modules_names = [_ for _ in os.listdir(core.library)]
    if new_name in all_modules_names:
        raise s.InternalError('module_copy error: name already in use')
    os.mkdir(f'{core.library}/{new_name}')
    output = f'{new_name} created. \n'
    folders = []
    files = []
    items_list = os.listdir(template_directory)
    for item in items_list:
        if os.path.isdir(f'{template_directory}/{item}'):
            folders.append(f'{core.library}/{new_name}/{item}')
            for next_item in os.listdir(f'{template_directory}/{item}'):
                items_list.append(f'{item}/{next_item}')
                if os.path.isdir(f'{template_directory}/{item}/{next_item}'):
                    folders.append(f'{core.library}/{new_name}/{item}/{next_item}')
        elif os.path.isfile(f'{template_directory}/{item}'):
            files.append(item)
        else:
            output += f'warning: item {item} is neither a file nor folder \n'
    if not folders and not files:
        pass
    for folder in folders:
        if not os.path.isdir(folder):
            os.makedirs(folder)
            output += folder + '\n'
    for file in files:
        if file == DEFINITION_NAME:
            definition_write(module_directory=f'{core.library}/{new_name}', return_type='save',
                             changes_source=changes_source)
            continue
        copied_file = f'{template_directory}/{file}'
        try:
            transfer_switch(copied_file, f'{core.library}/{new_name}/{file}', Transfer.COPY)
            output += f'{core.library}/{new_name}/{file}\n'
        except FileNotFoundError:
            output += f'warning: {file} permission denied'
        except FileExistsError:
            output += f'warning: {file} FileNotFoundError'
    return log(output)


def module_detect_changes(module=None):
    """ Inspects if the files of a module have been changed and returns a text where the changes are listed. """
    changes_dict = {}
    if module is None:
        module_directory = askdirectory(title=f'{s.PROGRAM_NAME}: select a module directory',
                                        initialdir=core.library)
        if not module_directory:
            raise s.InternalError('no module selected')
        module = definition_read(module_path=module_directory)
    if not module:
        raise s.InternalError('module not selected')
    for module_file in module[Property.CHANGES]:
        if module[Property.ACTIVE]:
            file_path = f'{s.MAIN_DIRECTORY}/{module_file}'
        else:
            file_path = f'{core.library}/{module[Property.NAME]}/{module_file}'
        if os.path.isfile(file_path):
            file_hash = hash_file(file_path)
            if not module[Property.CHANGES][module_file][1] == file_hash:
                if len(module[Property.CHANGES][module_file]) == 3:
                    if not module[Property.CHANGES][module_file][2] == file_hash:
                        changes_dict[module_file] = [Change.CHANGED, file_hash]
                else:
                    changes_dict[module_file] = [Change.CHANGED, file_hash]
        else:
            changes_dict[module_file] = [Change.REMOVED, '0']
    return changes_dict


def modules_filter(**criteria):
    """
    Filters the modules definitions by given criteria
    :param criteria: key - argument pairs, where the keywords are Definition parameters to compare the value against
    :return: Definition objects or module names, according to the return_type.
    """
    game_modules_list = []
    try:
        modules_names = [_ for _ in os.listdir(core.library) if _ not in core.exceptions]
        for module_name in modules_names:
            module_definition = definition_read(module_path=f'{core.library}/{module_name}')
            if (module_definition[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]
                    or module_definition[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]):
                if criteria:
                    for criteria_key in criteria:
                        if criteria_key in DEFINITION_EXAMPLE:
                            if module_definition[criteria_key] == criteria[criteria_key]:
                                game_modules_list.append(module_definition)
                else:
                    game_modules_list.append(module_definition)
    except s.InternalError:
        if game_modules_list:
            return game_modules_list
        else:
            raise s.InternalError(f'empty list')
    return game_modules_list


def modules_sort(criteria=Property.OVERRIDES, modules=None):
    """
    Sorts the modules into a dictionary of modules names as keys and their parent as value
    :param criteria:
    :param modules:
    :return:
    """
    if modules is None:
        modules = modules_filter()
    if criteria == Property.OVERRIDES:
        sorted_dict = {}
        for module in modules:
            for mod in modules:
                if mod[Property.NAME] == module[criteria]:
                    sorted_dict[module[Property.NAME]] = str(modules.index(mod))
                    break
        return sorted_dict
    else:
        raise s.InternalError(message='unrecognized criteria')


TEST = False
# TEST = True
