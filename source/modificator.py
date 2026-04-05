import os
from shutil import copy2, move
from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
from tkinter.simpledialog import askstring
from datetime import datetime
import xxhash
from glob import glob
import json
from typing import Literal

from source.messaging import log, InternalError
import source.core as core
import source.shared as s
from source.constants import SNAPSHOT_NAME, SNAPSHOT_DIRECTORY, SNAPSHOT_COMPARISON_DIRECTORY, COMPARISON_NAME, \
    Change, Transfer, MOD_DEF_FILE_NAME, PROGRAM_NAME, MAIN_DIRECTORY


# TODO: check if correct business logic
def mods_detect_new():
    output = ''
    library_folders = [_ for _ in os.listdir(core.state.library) if _ not in core.state.exceptions]
    for folder in library_folders:
        if not os.path.isfile(f'{core.state.library}/{folder}/{MOD_DEF_FILE_NAME}'):
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
            if next_folder in core.state.games:
                next_directory = [next_folder]
                break
        for next_file_or_folder in next_directory:
            output.update(hash_directory(f'{file_or_folder}/{next_file_or_folder}', path_to_omit=path_to_omit))
    return output


def get_available_name(snapshot_directory, prefix=SNAPSHOT_NAME):
    """ Given a directory, returns the name of the next file to save into. """
    counter = '1'
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
            raise InternalError('snapshot prefix index error')
        except NameError:
            pass
    return f'{snapshot_directory}/{prefix}{counter}.json'


def snapshot_take(game_paths=None):
    """
    Takes a snapshot of a selected directory.
    :param game_paths: directory to take a snapshot of.
    :return: dict with paths as keys and hash as values.
    """
    if not game_paths:
        raise InternalError('directory not selected')

    game_snapshot = {"date": f"{datetime.now()}"}
    for game_path in game_paths:
        if core.state.library in game_path:
            mod_name = game_path[len(core.state.library):].split('/')[1]
            path_to_omit = f'{core.state.library}/{mod_name}'
        else:
            path_to_omit = core.state.install_path
        # game_path = game_path.replace(path_to_omit + '/', '')
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
    log.info(f'snapshot successfully saved in file {snapshot_path}')
    return snapshot_path


def snapshot_compare(snap_anterior, snap_posterior, return_type: Literal['path', 'dict'] = 'path'):
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
    if not snap_anterior:
        raise InternalError('no snapshot selected')
    if isinstance(snap_anterior, dict):
        dict_anterior = snap_anterior.copy()
        snap_anterior = 'unsaved output'
    elif os.path.isfile(snap_anterior):
        with open(snap_anterior) as file_anterior:
            dict_anterior = json.load(file_anterior)
    if not snap_posterior:
        raise InternalError('no snapshot selected')
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
        log.info(f'snapshot comparison saved to {comparison_path}')
        return comparison_path


def initiate_comparison(mod_directory, start_mod='', changes_source='directory', files_to_remove=None, selected_comparison=None, selected_snapshot=None):
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
        raise InternalError('provided directory is not correct')
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
            raise InternalError('start_mod not provided')
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
            current_files = hash_directory(start_mod, path_to_omit=MAIN_DIRECTORY)
            for new_file in current_files:
                changes[new_file] = [Change.ADDED, current_files[new_file]]
        if files_to_remove:
            for file_path in files_to_remove:
                changes[file_path] = [Change.REMOVED, hash_file(file_path)]
        new_snapshot = snapshot_take(game_paths=[mod_directory])
        snapshot_save(new_snapshot, name=mod_directory.split('/')[-1])
    elif changes_source == 'comparison':
        if selected_comparison and os.path.isfile(selected_comparison):
            active, changes = evaluate_changes(selected_comparison)
        else:
            raise InternalError('comparison not selected')
    elif changes_source == 'snapshot':
        if selected_snapshot and os.path.isfile(selected_snapshot):
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
            raise InternalError('snapshot not selected')
    log.info(f'comparison generated for {mod_directory}')
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
        raise InternalError('no comparison')
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
            output += log.info(f'for deletion: {src}')
            if not os.path.isfile(f"{dst}/{src.split('/')[-1]}"):
                output += log.warning(f"original absent {dst}/{src.split('/')[-1]}")
        else:
            output += log.info(f'source: {src}')
    else:
        output += log.error(f'source absent {src}')
    if dst and transfer_type != Transfer.DELETE:
        if os.path.exists(dst):
            if os.path.isfile(f"{dst}/{src.split('/')[-1]}") and test_previous_src == f"{dst}/{src.split('/')[-1]}":
                if test_previous_type == Transfer.DELETE:
                    output += log.info(f'destination {test_previous_src} deleted')
                elif test_previous_type == Transfer.MOVE:
                    output += log.info(f'destination: {dst} (correct)')
                else:
                    output += log.warning(f"destination present {dst}/{src.split('/')[-1]}")
            else:
                output += log.info(f'destination: {dst}')
        else:
            output += log.error(f'destination absent {dst}')
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
            raise InternalError(error_message)


TEST = False
# TEST = True


# ==========================================
#               UI LAYER WRAPPERS
# ==========================================

def get_available_name_ui(snapshot_directory, prefix=SNAPSHOT_NAME):
    try:
        return get_available_name(snapshot_directory, prefix)
    except InternalError:
        counter = askstring(title=f'{PROGRAM_NAME}', prompt='Please give a name to the new file')
        if counter:
            return f'{snapshot_directory}/{prefix}{counter}.json'
        raise InternalError('snapshot prefix index error')


def snapshot_take_ui(game_paths=None, add_paths=False):
    if not game_paths:
        add_paths = True
        game_paths = []
    while add_paths:
        game_full_path = askdirectory(initialdir=f'{core.state.install_path}',
                                      title=f'{PROGRAM_NAME}: select game directory to take a snapshot of')
        if game_full_path:
            game_paths.append(game_full_path)
        elif not game_full_path:
            add_paths = False
        elif len(game_paths) == 0:
            raise InternalError('directory not selected')
    return snapshot_take(game_paths)


def snapshot_compare_ui(snap_anterior=None, snap_posterior=None, return_type: Literal['path', 'dict'] = 'path'):
    if snap_anterior is None:
        snap_anterior = askopenfilename(title=f'{PROGRAM_NAME}: choose the base snapshot to compare with',
                                        initialdir=SNAPSHOT_DIRECTORY)
    if snap_posterior is None:
        snap_posterior = askopenfilename(title=f'{PROGRAM_NAME}: choose the second snapshot to compare',
                                         initialdir=SNAPSHOT_DIRECTORY)
    return snapshot_compare(snap_anterior, snap_posterior, return_type)


def initiate_comparison_ui(mod_directory, start_mod='', changes_source='directory'):
    files_to_remove = None
    selected_comparison = None
    selected_snapshot = None
    if changes_source == 'directory':
        if not start_mod:
            start_mod = askdirectory(title=f'{PROGRAM_NAME}: select the game directory to define the mod',
                                     initialdir=MAIN_DIRECTORY)
        if start_mod:
            files_to_remove = askopenfilenames(title=f'{PROGRAM_NAME}: select files to remove',
                                               initialdir=MAIN_DIRECTORY)
    elif changes_source == 'comparison':
        selected_comparison = askopenfilename(
            title=f'{PROGRAM_NAME}: select the snapshot comparison to define the mod',
            initialdir=f'./{SNAPSHOT_COMPARISON_DIRECTORY}')
    elif changes_source == 'snapshot':
        selected_snapshot = askopenfilename(
            title=f'{PROGRAM_NAME}: select the snapshot taken before the changes',
            initialdir=f'./{SNAPSHOT_DIRECTORY}')
    return initiate_comparison(mod_directory, start_mod, changes_source, files_to_remove, selected_comparison, selected_snapshot)
