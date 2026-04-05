from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
from tkinter.simpledialog import askstring
from typing import Literal

from source.messaging import InternalError
import source.core as core
from source.constants import SNAPSHOT_NAME, SNAPSHOT_DIRECTORY, SNAPSHOT_COMPARISON_DIRECTORY, \
    PROGRAM_NAME, MAIN_DIRECTORY
from source.modificator import get_available_name, snapshot_take, snapshot_compare, initiate_comparison


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
    return initiate_comparison(
        mod_directory, start_mod, changes_source, files_to_remove, selected_comparison, selected_snapshot)
