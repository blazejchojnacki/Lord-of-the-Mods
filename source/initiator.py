import os.path
import shutil
import tkinter
import winreg
import json
from tkinter.filedialog import askdirectory
from tkinter.messagebox import askyesnocancel, showerror, showwarning

import source.shared
from source.module_control import definition_write, SNAPSHOT_DIRECTORY, SNAPSHOT_COMPARISON_DIRECTORY

default_folders_dict = {
    'library': './_LIBRARY',
    'archive': './_ARCHIVE',
}

if os.path.isfile('./initial/_games.json'):
    with open('./initial/_games.json') as games_buffer:
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
                title=f"{source.shared.PROGRAM_NAME}: please select {game_key['Name']} directory (or create one)",
                initialdir='../')
            if provided_directory:
                game_directories.append(provided_directory)
            else:
                cancel_initiation()
    for game_index in range(len(game_directories)):
        if os.path.isdir(game_directories[game_index]):
            game_directories[game_index] = os.path.relpath(game_directories[game_index]).replace('\\', '/')
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
                            f"./initial/{game_key['Roaming'].split('/')[-1]}/{roaming_file}", roaming_path)
            except FileNotFoundError:
                pass
    except NameError:
        pass


def cancel_initiation():
    """ Triggered when the directories are not provided to terminate the window. """
    showerror(
        title=f'{source.shared.PROGRAM_NAME} initiator: Error',
        message='The program cannot function properly without the appropriate settings\n Please try again'
    )
    exit()


def initiate():
    """ Initiates the application settings by asking for directories needed by the application. """
    initiator = tkinter.Tk()
    initiator.iconbitmap('aesthetic/icon.ico')
    initiator.title(f'{source.shared.PROGRAM_NAME} initiator')
    initiator.minsize(width=500, height=200)
    initiator_label = tkinter.Label(master=initiator, text='Looking for game paths. Please wait...')
    initiator_label.pack()
    initiator.update()
    if not os.path.isfile(source.shared.SETTINGS_PATH):
        try:
            game_paths_list = get_game_directory()
        except NameError:
            game_paths_list = []
        directories_dict = {}
        initiator_label.configure(text='Initiating functional directories.')
        initiator.update()
        use_default_paths = askyesnocancel(
            title=f'{source.shared.PROGRAM_NAME} initiator:',
            message=f'Use default functional folder names? If not, you can choose your own.'
        )
        if use_default_paths is True:
            for key in default_folders_dict:
                directories_dict[key] = default_folders_dict[key]
        if use_default_paths is False:
            for key in default_folders_dict:
                evaluated_string = askdirectory(
                    title=f'{source.shared.PROGRAM_NAME} initiator: Please select the module {key} directory\n',
                    initialdir='./'
                )
                if os.path.isdir(evaluated_string):
                    directories_dict[key] = os.path.relpath(evaluated_string).replace('\\', '/')
                else:
                    showwarning(
                        title=f'{source.shared.PROGRAM_NAME} initiator: ',
                        message=f'The provided name is empty.\n'
                                f' The default value will be applied'
                    )
                    directories_dict[key] = default_folders_dict[key]
        elif use_default_paths is None:
            cancel_initiation()
        source.shared.settings_set(
            do_initiate=True,
            settings_dict={
                source.shared.KEY_LIBRARY: directories_dict['library'],
                source.shared.KEY_ARCHIVE: directories_dict['archive'],
                source.shared.KEY_GAMES: game_paths_list,
            }
        )
        initiator_label.configure(text='Creating initial modules. Please wait ...')
        initiator.update()
        if not os.path.isdir(SNAPSHOT_DIRECTORY):
            os.mkdir(SNAPSHOT_DIRECTORY)
        if not os.path.isdir(SNAPSHOT_COMPARISON_DIRECTORY):
            os.mkdir(SNAPSHOT_COMPARISON_DIRECTORY)
        for game_path in game_paths_list:
            try:
                if not os.path.isdir(f"{directories_dict['library']}/{game_path.split('/')[-1]}"):
                    os.mkdir(f"{directories_dict['library']}/{game_path.split('/')[-1]}")
                definition_write(module_directory=f"{directories_dict['library']}/{game_path.split('/')[-1]}",
                                 return_type='object save', changes_source=game_path,
                                 description=f"Initial {game_path.split('/')[-1]} - created automatically")
            except source.shared.InternalError:
                pass
    else:
        source.shared.settings_get('initiate')
    ensure_game_options()
    initiator.destroy()
