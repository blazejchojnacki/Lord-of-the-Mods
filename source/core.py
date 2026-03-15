""" This module contains variables that are global for all the modules. """
import json
import os.path
from pathlib import Path

from source.shared import SETTINGS_FILE_PATH, _SETTINGS_FORMAT, Setting, MAIN_DIRECTORY, \
    InternalError

install_path = str(Path(__file__).parent.parent.parent.resolve()).replace('\\', '/').strip('/')

library = f'{MAIN_DIRECTORY}/_LIBRARY'
archive = f'{MAIN_DIRECTORY}/_ARCHIVE'
games = []
exceptions = []


def complete_paths(paths_dict):
    return_paths = []
    if Setting.LIBRARY in paths_dict:
        if paths_dict[Setting.LIBRARY]:
            library_path = f"{install_path}/{paths_dict[Setting.LIBRARY]}"
            return_paths.append(library_path)
        else:
            raise InternalError("empty path")
    if Setting.ARCHIVE in paths_dict:
        if paths_dict[Setting.ARCHIVE]:
            return_paths.append(f"{install_path}/{paths_dict[Setting.ARCHIVE]}")
        else:
            raise InternalError("empty path")
    if Setting.GAMES in paths_dict:
        return_paths.extend([f"{install_path}/{_}" for _ in paths_dict[Setting.GAMES]])
    if Setting.EXCEPTIONS in paths_dict:
        return_paths.extend([f"{install_path}/{_}" for _ in paths_dict[Setting.EXCEPTIONS]])
    return return_paths


class Settings(dict):
    def __init__(self):
        super().__init__()

    def create_directories(self, settings_dict):
        for path in complete_paths(settings_dict):
            os.makedirs(path, exist_ok=True)

    def propagate(self):
        global library, archive, games, exceptions
        library = f'{install_path}/{self[Setting.LIBRARY]}'
        archive = f'{install_path}/{self[Setting.ARCHIVE]}'
        games = [f'{install_path}/{_}' for _ in self[Setting.GAMES]]
        exceptions = [f'{install_path}/{_}' for _ in self[Setting.EXCEPTIONS]]

    def load(self):
        if os.path.isfile(SETTINGS_FILE_PATH):
            with open(SETTINGS_FILE_PATH) as file_stream:
                settings_dict = json.load(file_stream)
            for key in settings_dict:
                self[key] = settings_dict[key]
            self.propagate()
            return True
        else:
            # raise g.InternalError(f"{g.SETTINGS_FILE_PATH} not found")
            self.update(_SETTINGS_FORMAT)
            return False

    def check_format(self):
        for key in _SETTINGS_FORMAT:
            if key not in self:
                raise InternalError(f"{key} missing")
        for key in self:
            if key not in _SETTINGS_FORMAT:
                raise InternalError(f"{key} not recognized")

    def check_paths(self, new_settings_dict):
        settings_result = self.copy()
        settings_result.update(new_settings_dict)
        try:
            completed_paths = complete_paths(settings_result)
            for path in completed_paths:
                if not os.path.isdir(path):
                    return False
        except InternalError:
            return False
        return True

    def save(self, settings_dict):
        if self.check_paths(settings_dict):
            self.update(settings_dict)
            self.check_format()
            with open(SETTINGS_FILE_PATH, 'x') as file_stream:
                file_stream.write(json.dumps(self, indent=4))
            self.propagate()
        else:
            raise InternalError(f"invalid path")


os.chdir(Path(__file__).parent.parent.resolve())

settings = Settings()
loaded = settings.load()

if loaded:
    print("settings loaded")
