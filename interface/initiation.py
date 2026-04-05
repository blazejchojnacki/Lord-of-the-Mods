import tkinter
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror, showwarning
import os

from source.constants import PROGRAM_NAME, MAIN_DIRECTORY, SETTINGS_FILE_PATH
import source.core as core
from source.shared import ICON_PATH, KEY_LABEL, KEY_RETURN, KEY_INFO, invoke_choice
from source.initiator import game_list, search_reg, default_folders_dict, execute_initiation, ensure_game_options


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


def cancel_initiation():
    """ Triggered when the directories are not provided to terminate the window. """
    showerror(
        title=f'{PROGRAM_NAME} initiator: Error',
        message='The program cannot function properly without the appropriate settings\n Please try again'
    )
    exit()


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
