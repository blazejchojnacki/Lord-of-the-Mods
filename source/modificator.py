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
from source.shared import MOD_DEF_FILE_NAME

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
DEFINITION_TEMPLATE = {
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


class Mod(dict):
    """ A dictionary-based class with predefined keys and functions that manipulate mods. """

    def __init__(self, initial_dict=None):
        super().__init__()
        for key in DEFINITION_TEMPLATE:
            try:
                self[key] = DEFINITION_TEMPLATE[key].copy()
            except AttributeError:
                self[key] = DEFINITION_TEMPLATE[key]
            if initial_dict is not None:
                if key in initial_dict:
                    self[key] = initial_dict[key]

    def edit(self, **key_args):
        return definition_edit(self, **key_args)

    def retrieve(self):
        try:
            mod_reverse(mod_object=self, transfer=Transfer.REMOVE)
            return True
        except s.InternalError:
            return False

    def attach(self):
        try:
            mod_attach(self)
            return True
        except s.InternalError:
            try:
                mod_attach(mod_directory=f"{core.library}/{self[Property.NAME]}")
                return True
            except s.InternalError:
                # mod_attach(mod_directory=self['path'])
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
            mod_reverse(self, transfer=Transfer.DELETE, check_type='pass')
            mod_attach(self)
        if self[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
            mod_reverse(self, transfer=Transfer.COPY, check_type='pass')
            mod_attach(self)

    def extract(self):
        mod_reverse(mod_object=self, transfer=Transfer.COPY)


def definition_save(definition_object, mod_directory):
    with open(f'{mod_directory}/{MOD_DEF_FILE_NAME}', 'w') as definition_buffer:
        json.dump(definition_object, definition_buffer, indent=4)
        log(f'definition saved in {mod_directory}')


def definition_write(definition_object=None, mod_directory=None, changes_source='directory', **key_args):
    """
    Reads a definition and formats it into text, that can be saved into a text file.
    :param definition_object: (optional) a definition dictionary-like object
    :param mod_directory: (optional) a path to identify a mod and to save the definition to
    :param changes_source: (optional) 'directory' | 'snapshot' | 'comparison' | >the directory to base it upon<
    - passed to initiate_comparison
    :param key_args: (optional) key - arguments pairs for values to change before saving.
    :return: according to the return_type
    """
    if mod_directory is None:
        if definition_object is None:
            mod_directory = askdirectory(title=f'{s.PROGRAM_NAME}: select the directory to define as a mod',
                                         initialdir=core.library)
            if not mod_directory:
                raise s.InternalError('directory not selected')
        elif os.path.isdir(f"{core.library}/{definition_object[Property.NAME]}"):
            mod_directory = f"{core.library}/{definition_object[Property.NAME]}"
    if definition_object is not None:
        mod_name = definition_object[Property.NAME]
    elif mod_directory is not None:
        mod_name = mod_directory.split('/')[-1]
    else:
        mod_name = 'default name'
    if definition_object is None:
        if os.path.isfile(f'{mod_directory}/{MOD_DEF_FILE_NAME}'):
            definition_object = definition_read(mod_path=f'{mod_directory}')
        else:
            definition_object = Mod()
    if Property.TRANSFER_TYPE in key_args:
        definition_object[Property.TRANSFER_TYPE] = key_args[Property.TRANSFER_TYPE]
    else:
        definition_object[Property.TRANSFER_TYPE] = DEFINITION_CLASSES[0]
    try:
        if not definition_object[Property.GAME] and os.path.isdir(mod_directory):
            game_folders = os.listdir(mod_directory)
            for folder in game_folders:
                if os.path.isdir(f'../{folder}'):
                    definition_object[Property.GAME] = folder
                    break
            if not definition_object[Property.GAME]:
                definition_object[Property.GAME] = mod_name.split('-')[0]
    except IndexError:
        pass
    if not definition_object[Property.NAME] and mod_directory:
        definition_object[Property.NAME] = mod_directory.split('/')[-1]
    if Property.OVERRIDES in key_args:
        definition_object[Property.OVERRIDES] = key_args[Property.OVERRIDES]
    if Property.OVERRODE_BY in key_args:
        definition_object[Property.OVERRODE_BY] = key_args[Property.OVERRODE_BY]
    if not definition_object[Property.CHANGES]:
        try:
            definition_object[Property.ACTIVE], definition_object[Property.CHANGES] = initiate_comparison(
                mod_directory, changes_source=changes_source)
        except s.InternalError:
            pass
    return definition_object


def definition_read(mod_path=None):
    """
    Reads the definition of an object and loads it into a dictionary.
    :param mod_path: (optional) a mod path to check if a definition file exists
    :return: a definition dictionary-like class
    """
    if mod_path is not None:
        if mod_path in core.exceptions:
            raise s.InternalError("the provided path is defined as exception")
    if mod_path is None or mod_path == "":
        mod_path = askdirectory(title=f'{s.PROGRAM_NAME}: select the mod directory',
                                initialdir=core.library)
        if mod_path == "":
            raise s.InternalError('directory not selected')
    if os.path.isfile(f'{mod_path}/{MOD_DEF_FILE_NAME}'):
        with open(f'{mod_path}/{MOD_DEF_FILE_NAME}') as definition_buffer:
            return Mod(initial_dict=json.load(definition_buffer))
    else:
        # return Definition()
        raise s.InternalError('no definition under given path')


def definition_edit(definition_object=None, mod_path=None, **key_args):
    """
    Edits parameters of a Definition object
    :param definition_object: (optional) a Definition object to edit
    :param mod_path: (optional) the path to a mod with a definition file.
    :param key_args: key - arguments pairs of parameters to changes.
    :return: the edited Definition object.
    """
    if definition_object is None:
        if mod_path is None:
            mod_path = askdirectory(title=f'{s.PROGRAM_NAME}: select the mod directory',
                                    initialdir=core.library)
        if mod_path:
            definition_object = definition_read(mod_path=mod_path)
        if not definition_object:
            raise s.InternalError('definition missing')
    else:
        if mod_path is None:
            mod_path = f"{core.library}/{definition_object[Property.NAME]}"
    for key in key_args:
        if key in DEFINITION_TEMPLATE:
            if key == Property.NAME:
                list_mods = [_ for _ in os.listdir(core.library) if _ not in core.exceptions]
                for mod_name in list_mods:
                    if key_args[Property.NAME] == mod_name:
                        raise s.InternalError('definition_edit: name already in use')
                for mod_name in list_mods:
                    mod_definition = definition_read(mod_path=f'{core.library}/{mod_name}')
                    if definition_object[Property.NAME] == mod_definition[Property.OVERRIDES]:
                        definition_edit(
                            mod_definition,
                            ancestor=mod_definition[Property.OVERRIDES].replace(
                                definition_object[Property.NAME], key_args[Property.NAME])
                        )
                    if definition_object[Property.NAME] == mod_definition[Property.OVERRODE_BY]:
                        definition_edit(
                            mod_definition,
                            heir=mod_definition[Property.OVERRODE_BY].replace(
                                definition_object[Property.NAME], key_args[Property.NAME])
                        )
                os.rename(
                    src=mod_path, dst=f"{'/'.join(mod_path.split('/')[:-1])}/{key_args[Property.NAME]}")
            definition_object[key] = key_args[key]
        else:
            raise s.InternalWarning(f'key {key} not recognized')
    definition_save(definition_object, mod_path)
    return definition_object


# TODO: check if correct business logic
def mods_detect_new():
    output = ''
    library_folders = [_ for _ in os.listdir(core.library) if _ not in core.exceptions]
    for folder in library_folders:
        if not os.path.isfile(f'{core.library}/{folder}/{MOD_DEF_FILE_NAME}'):
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
            path_to_register = file_or_folder[file_or_folder.index(path_to_omit) + len(path_to_omit) + 1:]
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


def snapshot_take(game_paths=None, add_paths=False):
    """
    Takes a snapshot of a selected directory.
    :param game_paths: directory to take a snapshot of.
    :param add_paths: True | False - when True, asks for new directories until cancel is pressed.
    :return: dict with paths as keys and hash as values.
    """
    if not game_paths:
        add_paths = True
    while add_paths:
        game_full_path = askdirectory(initialdir=f'{s.MAIN_DIRECTORY}',
                                      title=f'{s.PROGRAM_NAME}: select game directory to take a snapshot of')
        if game_full_path:
            if os.path.abspath(core.library).replace('\\', '/') in game_full_path:
                mod_name = game_full_path[len(os.path.abspath(core.library)):].split('/')[1]
                path_to_omit = f'{os.path.abspath(core.library).replace('\\', '/')}/{mod_name}'
            else:
                path_to_omit = core.install_path
            game_path = os.path.relpath(path_to_omit, game_full_path)
            game_paths.append(game_path)
        elif not game_full_path:
            add_paths = False
        elif len(game_paths) == 0:
            raise s.InternalError('directory not selected')

    game_snapshot = {"date": f"{datetime.now()}"}
    for game_path in game_paths:
        if os.path.abspath(core.library).replace('\\', '/') in game_path:
            mod_name = game_path[len(os.path.abspath(core.library)):].split('/')[1]
            path_to_omit = f'{os.path.abspath(core.library).replace('\\', '/')}/{mod_name}'
        else:
            path_to_omit = core.install_path
        game_snapshot.update(hash_directory(game_path, path_to_omit=path_to_omit))
    return game_snapshot


def snapshot_save(game_snapshot, name=None):
    if not game_snapshot:
        game_snapshot = snapshot_take()
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


def initiate_comparison(mod_directory, start_mod='', changes_source='directory'):
    """
    Creates a change list for a mod definition, based on provided data.
    :param mod_directory: path to the mod, whose definition is being created
    :param start_mod: path to the present game folder to base the change on
    :param changes_source: 'directory' | 'comparison' | 'snapshot' -
    If 'directory', bases the changes on a present game folder.
    If 'comparison', bases the changes on a comparison file.
    If 'snapshot', bases the changes on the difference between present files and files in the snapshot.
    :return: tuple(active, changes)
    """
    if not os.path.isdir(mod_directory):
        raise s.InternalError('provided directory is not correct')
    changes = {}
    active = False
    if os.path.isdir(changes_source):
        active = True
        new_snapshot = snapshot_take(game_paths=[changes_source.split('/')[-1]])
        snapshot_save(game_snapshot=new_snapshot, name=changes_source.split('/')[-1])
        current_files = hash_directory(changes_source)
        for new_file in current_files:
            if len(new_file) > 0:
                changes[new_file] = [Change.ADDED, current_files[new_file]]
    elif changes_source == 'directory':
        if not start_mod:
            start_mod = askdirectory(title=f'{s.PROGRAM_NAME}: select the game directory to define the mod',
                                     initialdir=s.MAIN_DIRECTORY)
        new_files_dict = hash_directory(mod_directory, path_to_omit=mod_directory, skip_first_level_files=True)
        if start_mod and new_files_dict:
            active = False
            current_files = hash_directory(
                start_mod, path_to_omit=f'{start_mod[:start_mod.rfind("/")]}')
            for new_file in new_files_dict:
                if new_file in current_files:
                    changes[new_file] = [Change.CHANGED, new_files_dict[new_file], current_files[new_file]]
                else:
                    changes[new_file] = [Change.ADDED, new_files_dict[new_file]]
        elif start_mod and not new_files_dict:
            active = True
            current_files = hash_directory(start_mod, path_to_omit=s.MAIN_DIRECTORY)
            for new_file in current_files:
                changes[new_file] = [Change.ADDED, current_files[new_file]]
        files_to_remove = askopenfilenames(title=f'{s.PROGRAM_NAME}: select files to remove',
                                           initialdir=s.MAIN_DIRECTORY)
        for file_path in files_to_remove:
            changes[file_path] = [Change.REMOVED, hash_file(file_path)]
        new_snapshot = snapshot_take(game_paths=[mod_directory])
        snapshot_save(new_snapshot, name=mod_directory.split('/')[-1])
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
            new_snapshot = snapshot_take(game_paths=game_paths)
            snapshot_save(new_snapshot, name=mod_directory.split('/')[-1])
            comparison_dict = snapshot_compare(selected_snapshot, new_snapshot, return_type='dict')
            active, changes = evaluate_changes(comparison_dict)
        else:
            raise s.InternalError('snapshot not selected')
    log(f'comparison generated for {mod_directory}')
    return active, changes


def evaluate_changes(comparison):
    changes = {}
    if isinstance(comparison, str):
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
            os.makedirs(dst, exist_ok=True)
            copy2(src, dst)
        elif transfer_type == Transfer.MOVE:
            os.makedirs(dst, exist_ok=True)
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


def check_library(mod_object):
    changes = mod_object[Property.CHANGES]
    library_missing = False
    for file in changes:
        if not os.path.isfile(f"{core.library}/{mod_object[Property.NAME]}/{file}"):
            library_missing = True
            break
    return library_missing


def mod_check_relative(mod_object, relation):
    if Property.OVERRODE_BY == relation:
        if mod_object[Property.OVERRODE_BY]:
            if os.path.isfile(f"{core.library}/{mod_object[Property.OVERRODE_BY]}/{MOD_DEF_FILE_NAME}"):
                heir_mod_object = definition_read(f"{core.library}/{mod_object[Property.OVERRODE_BY]}")
                if heir_mod_object[Property.ACTIVE]:
                    return heir_mod_object
    elif Property.OVERRIDES == relation:
        if mod_object[Property.OVERRIDES]:
            ancestor_directory = f"{core.library}/{mod_object[Property.OVERRIDES]}"
            if os.path.isfile(f'{ancestor_directory}/{MOD_DEF_FILE_NAME}'):
                ancestor_mod_object = definition_read(mod_path=ancestor_directory)
                if not ancestor_mod_object[Property.ACTIVE]:
                    return ancestor_mod_object


def mod_reverse(mod_object, transfer: Transfer = Transfer.COPY, check_type='hash, heir'):
    """
    Detaches the mod from the game directory, by retrieving all its files to the LIBRARY.
    :param mod_object: (optional) the dictionary-based Definition object
    :param transfer: 'copy' | 'move' | 'delete' - transfer type.
    :param check_type: 'definition' | 'snapshot' | 'pass' - check if the mod is indeed in the game folder
    If 'pass', does not check, just tries to detach what it can.
    :return: logs about the transfer details.
    """
    global error_sensitivity
    if mod_object is None:
        raise s.InternalError('missing object')
    mod_name = mod_object[Property.NAME]
    comparison_dict = mod_object[Property.CHANGES]
    if not os.path.isdir(f'{core.library}/{mod_name}'):
        os.mkdir(f'{core.library}/{mod_name}')
    if transfer == Transfer.REMOVE:
        if mod_object[Property.ACTIVE] is False and check_type != 'pass':
            raise s.InternalError('deactivation of inactive mod aborted')
        if mod_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]:
            transfer = Transfer.MOVE
        elif mod_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1] and check_library(mod_object):
            transfer = Transfer.MOVE
        elif mod_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
            transfer = Transfer.DELETE
    if not comparison_dict:
        raise s.InternalError('comparison missing')

    error_sensitivity = True
    if Property.OVERRODE_BY in check_type:
        if heir_mod_object := mod_check_relative(mod_object, Property.OVERRODE_BY):
            if not mod_reverse(heir_mod_object, transfer=Transfer.REMOVE):
                raise s.InternalError('heir mod not retrieved')
    elif check_type == 'pass':
        error_sensitivity = False
    try:
        for path_key in comparison_dict:
            file_path_source = f"{core.install_path}/{path_key}"
            file_path_game = f"{core.install_path}/{'/'.join(path_key.split('/')[:-1])}"
            file_path_mod = f"{core.library}/{mod_name}/{'/'.join(path_key.split('/')[0:-1])}"
            file_path_archive = f"{core.archive}/{mod_name}/{path_key}"
            if 'hash' in check_type:
                pass
            if comparison_dict[path_key][0] == Change.UNCHANGED:
                pass
            elif comparison_dict[path_key][0] == Change.CHANGED:
                if transfer in Transfer:
                    transfer_switch(file_path_source, file_path_mod, transfer, error_sensitivity)
                if transfer == Transfer.MOVE or transfer == Transfer.DELETE:
                    transfer_switch(file_path_archive, file_path_game, Transfer.MOVE, error_sensitivity)
            elif comparison_dict[path_key][0] == Change.ADDED:
                transfer_switch(file_path_source, file_path_mod, transfer, error_sensitivity)
            elif comparison_dict[path_key][0] == Change.REMOVED:
                if transfer == Transfer.MOVE or transfer == Transfer.DELETE:
                    transfer_switch(file_path_archive, file_path_game, Transfer.MOVE, error_sensitivity)
                else:
                    pass
    except s.InternalError:
        log(f'mod_reverse {mod_name} CANCELLED\n')
        mod_attach(mod_directory=f'{core.library}/{mod_name}', check_type='pass')
        return False
    if TEST:
        raise s.InternalError('under TEST phase: mod_reverse not applied')
    definition_edit(definition_object=mod_object, active=False)
    log(f'mod_reverse {mod_name}\n')
    return True


def mod_detect_override(mod: Mod):
    """

    :param mod:
    :return:
     - time-optimization might be required -
    """
    new_changes = mod[Property.CHANGES]
    active_mods = mods_select(active=True)
    for active_mod in active_mods:
        if mod[Property.OVERRIDES] == active_mod[Property.NAME]:
            return active_mod
    for active_mod in active_mods:
        if not active_mod[Property.OVERRODE_BY]:
            for active_file in active_mod[Property.CHANGES]:
                if active_file.strip('../') in new_changes:
                    return active_mod
    return False


def mod_attach(mod_object=None, mod_directory=None, check_type='ancestor'):
    """
    Attaches a mod to the game directory.
    :param mod_object: (optional) dictionary-based mod object
    :param mod_directory: (optional) path of the mod to attach
    :param check_type: 'ancestor' | 'snapshot' | 'pass' - check if the mod is indeed in the LIBRARY folder
    If 'pass', does not check, just tries to attach what it can.
    :return: logs about the transfer details.
    """
    global error_sensitivity
    transfer = Transfer.MOVE
    if mod_object is None:
        if mod_directory is None:
            mod_directory = askdirectory(title=f'{s.PROGRAM_NAME}: select mod directory',
                                         initialdir=core.library)
            if not mod_directory:
                raise s.InternalError('mod directory missing')
        if os.path.isfile(f'{mod_directory}/{MOD_DEF_FILE_NAME}'):
            mod_object = definition_read(mod_path=mod_directory)
    error_sensitivity = True
    if ancestor_mod := mod_detect_override(mod_object):
        mod_object = definition_edit(mod_object, ancestor=ancestor_mod[Property.NAME])
        definition_edit(ancestor_mod, heir=mod_object[Property.NAME])
    if Property.OVERRIDES in check_type:
        if os.path.isdir(f"{core.library}/{mod_object[Property.NAME]}"):
            mod_directory = f"{core.library}/{mod_object[Property.NAME]}"
        else:
            raise s.InternalError('path not recognized')
        if mod_object[Property.ACTIVE] is True and check_type != 'pass':
            raise s.InternalError('activation of active mod aborted')
        if mod_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]:
            transfer = Transfer.MOVE
        elif mod_object[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
            transfer = Transfer.COPY
        if ancestor_mod_object := mod_check_relative(mod_object, Property.OVERRIDES):
            if not mod_attach(ancestor_mod_object):
                raise s.InternalError('ancestor mod not attached')
    elif check_type == 'pass':
        error_sensitivity = False
    if mod_object[Property.NAME]:
        mod_name = mod_object[Property.NAME]
    elif mod_directory:
        mod_name = mod_directory.split('/')[-1]
    else:
        raise s.InternalError("unnamed mod")
    if not os.path.isdir(f'{core.archive}/{mod_name}'):
        os.mkdir(f'{core.archive}/{mod_name}')
    comparison_dict = mod_object[Property.CHANGES].copy()
    if not comparison_dict and os.path.isfile(f"{mod_directory}/{COMPARISON_NAME}{mod_name}.json"):
        with open(f"{mod_directory}/{COMPARISON_NAME}{mod_name}.json") as comparison_buffer:
            comparison_dict = json.load(comparison_buffer)
    if comparison_dict:
        # output = ''
        try:
            for path_key in comparison_dict:
                file_path_source = f"{core.install_path}/{path_key}"
                file_path_game = f"{core.install_path}/{'/'.join(path_key.split('/')[:-1])}"
                file_path_archive = f"{core.archive}/{mod_name}/{'/'.join(path_key.split('/')[0:-1])}"
                file_path_mod = f"{core.library}/{mod_name}/{path_key}"
                if comparison_dict[path_key][0] == Change.UNCHANGED:
                    pass
                elif comparison_dict[path_key][0] == Change.CHANGED:
                    transfer_switch(file_path_source, file_path_archive, transfer, error_sensitivity)
                    transfer_switch(file_path_mod, file_path_game, transfer, error_sensitivity)
                elif comparison_dict[path_key][0] == Change.ADDED:
                    transfer_switch(file_path_mod, file_path_game, transfer, error_sensitivity)
                elif comparison_dict[path_key][0] == Change.REMOVED:
                    transfer_switch(file_path_source, file_path_archive, transfer, error_sensitivity)
        except s.InternalError:
            log(f'mod_attach {mod_name} CANCELLED\n')
            mod_reverse(mod_object=mod_object, transfer=Transfer.REMOVE, check_type='pass')
            return False
    else:
        raise s.InternalError('comparison missing')
    if TEST:
        raise s.InternalError('Test phase: mod_attach not applied')
    definition_edit(definition_object=mod_object, active=True)
    log(f'mod_attach {mod_name}\n')
    return True


def mod_new(name: str, changes_source: str = ''):
    if not os.path.isdir(f'{core.library}/{name}'):
        os.mkdir(f'{core.library}/{name}')
    output = f'{name} created. \n'
    mod_directory = f'{core.library}/{name}'
    definition_object = definition_write(mod_directory=mod_directory, changes_source=changes_source)
    definition_save(definition_object, mod_directory)
    return log(output)


# may not be needed
def mod_copy(new_name, template_directory=None, changes_source=None):
    """
    Copies mods files into a new directory.
    :param new_name: the name of the mod to create
    :param template_directory: the path to the mod to copy
    :param changes_source: 'snapshot' | 'comparison' | 'directory' - passes the value to definition_write
    :return: logs about the details of the transfer
    """
    if not template_directory:
        raise s.InternalError('template not selected')
    all_mods_names = [_ for _ in os.listdir(core.library)]
    if new_name in all_mods_names:
        raise s.InternalError('mod_copy error: name already in use')
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
        if file == MOD_DEF_FILE_NAME:
            mod_directory = f'{core.library}/{new_name}'
            definition_object = definition_write(mod_directory=mod_directory, changes_source=changes_source)
            definition_save(definition_object, mod_directory)
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


def mod_detect_changes(mod=None):
    """ Inspects if the files of a mod have been changed and returns a text where the changes are listed. """
    changes_dict = {}
    if mod is None:
        mod_directory = askdirectory(title=f'{s.PROGRAM_NAME}: select a mod directory',
                                     initialdir=core.library)
        if not mod_directory:
            raise s.InternalError('no mod selected')
        mod = definition_read(mod_path=mod_directory)
    if not mod:
        raise s.InternalError('mod not selected')
    for mod_file in mod[Property.CHANGES]:
        if mod[Property.ACTIVE]:
            file_path = f'{s.MAIN_DIRECTORY}/{mod_file}'
        else:
            file_path = f'{core.library}/{mod[Property.NAME]}/{mod_file}'
        if os.path.isfile(file_path):
            file_hash = hash_file(file_path)
            if not mod[Property.CHANGES][mod_file][1] == file_hash:
                if len(mod[Property.CHANGES][mod_file]) == 3:
                    if not mod[Property.CHANGES][mod_file][2] == file_hash:
                        changes_dict[mod_file] = [Change.CHANGED, file_hash]
                else:
                    changes_dict[mod_file] = [Change.CHANGED, file_hash]
        else:
            changes_dict[mod_file] = [Change.REMOVED, '0']
    return changes_dict


def mods_select(**criteria):
    """
    Filters the mods definitions by given criteria
    :param criteria: key - argument pairs, where the keywords are Definition parameters to compare the value against
    :return: Definition objects or mod names, according to the return_type.
    """
    game_mods_list = []
    try:
        mods_names = [_ for _ in os.listdir(core.library) if _ not in core.exceptions]
        for mod_name in mods_names:
            mod_definition = definition_read(mod_path=f'{core.library}/{mod_name}')
            if (mod_definition[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]
                    or mod_definition[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]):
                if criteria:
                    for criteria_key in criteria:
                        if criteria_key in DEFINITION_TEMPLATE:
                            if mod_definition[criteria_key] == criteria[criteria_key]:
                                game_mods_list.append(mod_definition)
                else:
                    game_mods_list.append(mod_definition)
    except s.InternalError:
        if game_mods_list:
            return game_mods_list
        else:
            raise s.InternalError(f'empty list')
    return game_mods_list


def mods_sort(criteria=Property.OVERRIDES, mods=None):
    """
    Sorts the mods into a dictionary of mods names as keys and their parent as value
    :param criteria:
    :param mods:
    :return:
    """
    if mods is None:
        mods = mods_select()
    if criteria == Property.OVERRIDES:
        sorted_dict = {}
        for mod_parent in mods:
            for mod in mods:
                if mod[Property.NAME] == mod_parent[criteria]:
                    sorted_dict[mod_parent[Property.NAME]] = str(mods.index(mod))
                    break
        return sorted_dict
    else:
        raise s.InternalError(message='unrecognized criteria')


TEST = False
# TEST = True
