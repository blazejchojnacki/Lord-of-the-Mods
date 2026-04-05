import os.path
import shutil
import tkinter
import winreg
import json
from pathlib import Path
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror, showwarning

from source.messaging import InternalError
import source.core as core
from source.constants import PROGRAM_NAME, MAIN_DIRECTORY, SETTINGS_FILE_PATH, Setting
import source.shared
from source.shared import ICON_PATH, KEY_LABEL, KEY_RETURN, KEY_INFO, invoke_choice
from models.mod import Mod
from source.modificator import SNAPSHOT_DIRECTORY, SNAPSHOT_COMPARISON_DIRECTORY


default_folders_dict = {
    'library': f'{MAIN_DIRECTORY}/_LIBRARY',
    'archive': f'{MAIN_DIRECTORY}/_ARCHIVE',
}  # TODO: don't ask if those already exist

if os.path.isfile(f'{MAIN_DIRECTORY}/initial/_games.json'):
    with open(f'{MAIN_DIRECTORY}/initial/_games.json') as games_buffer:
        game_list = json.load(games_buffer)
else:
    game_list = [
        {
            "Name": "The Battle for Middle-earth II",
            "Registry": "SOFTWARE\\WOW6432Node\\Electronic Arts",
            "Roaming": "/AppData/Roaming/My Battle for Middle-earth(tm) II Files",
            "RoamingFiles": [
                "/Options.ini",
                "/Worldbuilder.ini"
            ],
            "EXE": "lotrbfme2.exe"
        },
        {
            "Name": "The Lord of the Rings, The Rise of the Witch-king",
            "Registry": "SOFTWARE\\WOW6432Node\\Electronic Arts",
            "Roaming": "/AppData/Roaming/My The Lord of the Rings, The Rise of the Witch-king Files",
            "RoamingFiles": [
                "/Options.ini",
                "/Worldbuilder.ini"
            ],
            "EXE": "lotrbfme2ep1.exe"
        }
    ]


def search_reg(master_key_name, game_name):
    """ Looks for the game installation paths in the Windows Registry. """
    registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    output = ''
    try:
        master_key = winreg.OpenKey(registry, master_key_name)
        for reg_key_index in range(winreg.QueryInfoKey(master_key)[0]):
            child_key_name = winreg.EnumKey(master_key, reg_key_index)
            new_master = f'{master_key_name}\\{child_key_name}'
            if child_key_name == game_name:
                child_key = winreg.OpenKey(master_key, child_key_name)
                try:
                    install_directory = winreg.QueryValueEx(child_key, 'InstallPath')[0]
                    if install_directory.endswith('\\'):
                        install_directory = install_directory[:-1]
                    output += install_directory.replace('\\', '/')
                except FileNotFoundError:
                    continue
            else:
                output += f'{search_reg(new_master, game_name)}'
    except PermissionError:
        pass
    return output


def get_game_directory():
    """ Pure UI: Gathers absolute game paths using Registry OR File Dialogs. """
    game_directories = []
    for game_key in game_list:
        # Step 1: Try Registry (Logic call)
        path = search_reg(game_key['Registry'], game_key['Name'])

        # Step 2: If not found, prompt the User (UI call)
        if not path:
            path = askdirectory(
                title=f"{PROGRAM_NAME}: please select {game_key['Name']} directory (or create one)",
                initialdir='../'
            )
            if not path:
                cancel_initiation()

        game_directories.append(path.replace('\\', '/'))

    return game_directories


def ensure_game_options():
    """ Copies files necessary to run the game. """
    try:
        for game_key in game_list:
            try:
                roaming_path = os.path.expanduser(f"~{game_key['Roaming']}")
                if not os.path.isdir(roaming_path):
                    os.mkdir(roaming_path)
                for roaming_file in game_key['RoamingFiles']:
                    if not os.path.isfile(f'{roaming_path}/{roaming_file}'):
                        shutil.copy(
                            f"{MAIN_DIRECTORY}/initial/{game_key['Roaming'].split('/')[-1]}/{roaming_file}",
                            roaming_path)
            except FileNotFoundError:
                pass
    except NameError:
        pass


def cancel_initiation():
    """ Triggered when the directories are not provided to terminate the window. """
    showerror(
        title=f'{PROGRAM_NAME} initiator: Error',
        message='The program cannot function properly without the appropriate settings\n Please try again'
    )
    exit()


def set_directories(directories_dict, game_paths_list):
    for key in directories_dict:
        directories_dict[key] = os.path.relpath(directories_dict[key], core.state.install_path).replace('\\', '/')
    core.state.save(
        settings_dict={
            Setting.INSTALL: core.state.install_path,
            Setting.LIBRARY: directories_dict['library'],
            Setting.ARCHIVE: directories_dict['archive'],
            Setting.GAMES: game_paths_list,
        }
    )


def execute_initiation(absolute_game_paths: list, absolute_directories_dict: dict):
    """
    Pure Logic: The core function that calculates relative paths,
    saves settings, builds standard folders, and creates base mods.
    """
    # 1. Determine the install_path dynamically from the first absolute game path
    new_install_path = Path(absolute_game_paths[0]).parent.resolve()
    core.state.install_path = str(new_install_path).replace('\\', '/').strip('/')

    # 2. Make game paths relative to the install_path
    relative_game_paths = []
    for game_path in absolute_game_paths:
        rel_path = game_path.replace(core.state.install_path, '').strip('/')
        relative_game_paths.append(rel_path)

    set_directories(absolute_directories_dict, relative_game_paths)

    # 5. Create core directories
    if not os.path.isdir(SNAPSHOT_DIRECTORY):
        os.mkdir(SNAPSHOT_DIRECTORY)
    if not os.path.isdir(SNAPSHOT_COMPARISON_DIRECTORY):
        os.mkdir(SNAPSHOT_COMPARISON_DIRECTORY)

    # 6. Create initial mod definitions
    for game_path in relative_game_paths:
        try:
            mod_name = game_path.split('/')[-1]
            Mod.create(
                name=mod_name, changes_source=game_path,
                description=f"Initial {mod_name} - created automatically"
            )
        except InternalError:
            pass
    ensure_game_options()


def get_directories():
    """ Prompts the user for Library and Archive locations. """
    use_default_paths = invoke_choice(
        title=f'{PROGRAM_NAME} initiator:',
        text='Use default functional folder names?',
        buttons=({KEY_LABEL: 'Use default', KEY_RETURN: True, KEY_INFO: ''},
                 {KEY_LABEL: 'Choose own', KEY_RETURN: False, KEY_INFO: ''},
                 {KEY_LABEL: 'Cancel', KEY_RETURN: None, KEY_INFO: ''})
    )
    if use_default_paths is None:
        cancel_initiation()
    directories_dict = {}
    if use_default_paths is True:
        directories_dict = default_folders_dict.copy()
    elif use_default_paths is False:
        for key in default_folders_dict:
            evaluated_string = askdirectory(
                title=f'{PROGRAM_NAME} initiator: Please select the mod {key} directory\n',
                initialdir=f'{MAIN_DIRECTORY}'
            )
            if os.path.isdir(evaluated_string):
                directories_dict[key] = evaluated_string
            else:
                showwarning(
                    title=f'{PROGRAM_NAME} initiator: ',
                    message=f'The provided name is empty.\n'
                            f' The default value will be applied'
                )
                directories_dict[key] = default_folders_dict[key]
    return directories_dict


def initiate():
    """ The Main Orchestrator. Handles the Tkinter window and calls the core logic. """
    initiator = tkinter.Tk()
    initiator.iconbitmap(ICON_PATH)
    initiator.title(f'{PROGRAM_NAME} initiator')
    initiator.minsize(width=500, height=200)
    source.shared.main_window = initiator
    source.shared.current_info = tkinter.Toplevel(master=initiator)
    source.shared.current_info.destroy()
    initiator_label = tkinter.Label(master=initiator, text='Looking for game paths. Please wait...')
    initiator_label.pack()
    initiator.update()
    if not os.path.isfile(SETTINGS_FILE_PATH):
        game_paths_list = get_game_directory()
        initiator_label.configure(text='Initiating functional directories.')
        initiator.update()
        directories_dict = get_directories()

        initiator_label.configure(text='Creating initial mods. Please wait ...')
        initiator.update()
        execute_initiation(game_paths_list, directories_dict)
    else:
        # Setup already complete, just load settings
        core.state.load()
        ensure_game_options()
    initiator.destroy()


if __name__ == "__main__":
    initiate()
