import os.path
import shutil
import tkinter
import winreg
import json
from pathlib import Path
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror, showwarning

import source.core as core
import source.shared
from source.shared import PROGRAM_NAME, MAIN_DIRECTORY, ICON_PATH, SETTINGS_FILE_PATH, Setting, InternalError, \
    invoke_choice, KEY_LABEL, KEY_RETURN, KEY_INFO
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
    """ Returns a list of game paths. """
    game_directories = []
    for game_key in game_list:
        try:
            game_directories.append(search_reg(game_key['Registry'], game_key['Name']))
        except FileNotFoundError:
            provided_directory = askdirectory(
                title=f"{PROGRAM_NAME}: please select {game_key['Name']} directory (or create one)",
                initialdir='../')
            if provided_directory:
                game_directories.append(provided_directory)
            else:
                cancel_initiation()
    for game_index in range(len(game_directories)):
        if os.path.isdir(game_directories[game_index]):
            # TODO: handling of cases where the game is not directly in the install path
            core.install_path = Path(game_directories[game_index]).parent.resolve()
            game_directories[game_index] = game_directories[game_index].replace(
                str(core.install_path).replace('\\', '/'), '').strip('/')
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
        directories_dict[key] = os.path.relpath(directories_dict[key], core.install_path).replace('\\', '/')
    core.settings.save(
        settings_dict={
            Setting.LIBRARY: directories_dict['library'],
            Setting.ARCHIVE: directories_dict['archive'],
            Setting.GAMES: game_paths_list,
        }
    )
    if not os.path.isdir(SNAPSHOT_DIRECTORY):
        os.mkdir(SNAPSHOT_DIRECTORY)
    if not os.path.isdir(SNAPSHOT_COMPARISON_DIRECTORY):
        os.mkdir(SNAPSHOT_COMPARISON_DIRECTORY)
    for game_path in game_paths_list:
        try:
            mod_name = game_path.split('/')[-1]
            definition_object = Mod.create(
                name=mod_name, changes_source=game_path,
                description=f"Initial {game_path.split('/')[-1]} - created automatically")
            definition_object.save()
        except InternalError:
            pass


def get_directories():
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
        for key in default_folders_dict:
            directories_dict[key] = default_folders_dict[key]
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
    """ Initiates the application settings by asking for directories needed by the application. """
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
        try:
            game_paths_list = get_game_directory()
        except NameError:
            game_paths_list = []
        initiator_label.configure(text='Initiating functional directories.')
        initiator.update()
        directories_dict = get_directories()

        initiator_label.configure(text='Creating initial mods. Please wait ...')
        initiator.update()
        set_directories(directories_dict, game_paths_list)
    else:
        core.settings.load()
    ensure_game_options()
    initiator.destroy()


if __name__ == "__main__":
    initiate()
