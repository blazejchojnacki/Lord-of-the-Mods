""" This module contains variables that are global for all the modules. """
import json
import os.path
from pathlib import Path

from source.shared import SETTINGS_FILE_PATH, _SETTINGS_FORMAT, Setting, MAIN_DIRECTORY, \
    InternalError

install_path = os.path.abspath('../..').strip('\\').replace('\\', '/')

library = f'{MAIN_DIRECTORY}/_LIBRARY'
archive = f'{MAIN_DIRECTORY}/_ARCHIVE'
games = []
exceptions = []


class Settings(dict):
    def __init__(self):
        super().__init__()

    def create_directories(self, settings_dict):
        for key in settings_dict:
            if key not in _SETTINGS_FORMAT:
                pass
            elif settings_dict[key]:
                paths = []
                if isinstance(settings_dict[key], list):
                    paths = settings_dict[key]
                elif isinstance(settings_dict[key], str):
                    paths = [settings_dict[key]]
                for path in paths:
                    os.makedirs(path, exist_ok=True)

    def propagate(self):
        global library, archive, games, exceptions
        library = self[Setting.LIBRARY]
        archive = self[Setting.ARCHIVE]
        games = self[Setting.GAMES]
        exceptions = self[Setting.EXCEPTIONS]

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
        for key in _SETTINGS_FORMAT:
            if settings_result[key] and key not in [Setting.TITLE, Setting.VERSION]:
                paths = []
                # if isinstance(settings_result[key], list):
                if key == Setting.GAMES:
                    paths = [f'{install_path}/{_}' for _ in settings_result[key]]
                elif key == Setting.EXCEPTIONS:
                    paths = [f'{library}/{_}' for _ in settings_result[key]]
                elif isinstance(settings_result[key], str):
                    paths = [f'{install_path}/{settings_result[key]}']
                for path in paths:
                    if not os.path.isdir(path):
                        # raise g.InternalError(f"{path} not found")
                        return False
            elif key == Setting.LIBRARY or key == Setting.ARCHIVE:
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
