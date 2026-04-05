import os.path
import shutil
import winreg
import json
from pathlib import Path

from source.messaging import InternalError
import source.core as core
from source.constants import MAIN_DIRECTORY, Setting
from models.mod import Mod
from source.modificator import SNAPSHOT_DIRECTORY, SNAPSHOT_COMPARISON_DIRECTORY


default_folders_dict = {
    'library': f'{MAIN_DIRECTORY}/_LIBRARY',
    'archive': f'{MAIN_DIRECTORY}/_ARCHIVE',
}

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


def set_directories(directories_dict, game_paths_list):
    for key in directories_dict:
        directories_dict[key] = os.path.relpath(directories_dict[key], core.state.install_path).replace('\\', '/')
    core.state.save({
        Setting.INSTALL: core.state.install_path,
        Setting.LIBRARY: directories_dict['library'],
        Setting.ARCHIVE: directories_dict['archive'],
        Setting.GAMES: game_paths_list,
    })


def execute_initiation(absolute_game_paths: list, absolute_directories_dict: dict):
    """
    The core function that calculates relative paths,
    saves settings, builds standard folders, and creates base mods.
    """
    # Determine the install_path dynamically from the first absolute game path
    new_install_path = Path(absolute_game_paths[0]).parent.resolve()
    core.state.install_path = str(new_install_path).replace('\\', '/').strip('/')

    # Make game paths relative to the install_path
    relative_game_paths = []
    for game_path in absolute_game_paths:
        rel_path = game_path.replace(core.state.install_path, '').strip('/')
        relative_game_paths.append(rel_path)

    set_directories(absolute_directories_dict, relative_game_paths)

    # Create core directories
    if not os.path.isdir(SNAPSHOT_DIRECTORY):
        os.mkdir(SNAPSHOT_DIRECTORY)
    if not os.path.isdir(SNAPSHOT_COMPARISON_DIRECTORY):
        os.mkdir(SNAPSHOT_COMPARISON_DIRECTORY)

    # Create initial mod definitions
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


if __name__ == "__main__":
    execute_initiation([], default_folders_dict)
