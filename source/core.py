""" This module contains the application state and configuration logic. """
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

from source.shared import SETTINGS_FILE_PATH, _SETTINGS_FORMAT, Setting, InternalError

DEFAULT_INSTALL_PATH = str(Path(__file__).parent.parent.parent.resolve()).replace('\\', '/').strip('/')


@dataclass
class AppConfig:
    """ Centralized configuration and state manager. """
    install_path: str = DEFAULT_INSTALL_PATH
    library: str = ""
    archive: str = ""
    games: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    raw_settings: Dict[str, Any] = field(default_factory=dict)

    def complete_paths(self, paths_dict: dict) -> List[str]:
        return_paths = []
        if Setting.LIBRARY in paths_dict and paths_dict[Setting.LIBRARY]:
            return_paths.append(f"{self.install_path}/{paths_dict[Setting.LIBRARY]}")
        else:
            raise InternalError("empty library path")
        if Setting.ARCHIVE in paths_dict and paths_dict[Setting.ARCHIVE]:
            return_paths.append(f"{self.install_path}/{paths_dict[Setting.ARCHIVE]}")
        else:
            raise InternalError("empty archive path")
        if Setting.GAMES in paths_dict:
            return_paths.extend([f"{self.install_path}/{_}" for _ in paths_dict[Setting.GAMES]])
        if Setting.EXCEPTIONS in paths_dict:
            return_paths.extend([f"{self.install_path}/{_}" for _ in paths_dict[Setting.EXCEPTIONS]])
        return return_paths

    def propagate(self):
        """ Updates the active state properties based on the loaded raw_settings. """
        self.install_path = self.raw_settings.get("install_path", DEFAULT_INSTALL_PATH)
        self.library = f'{self.install_path}/{self.raw_settings[Setting.LIBRARY]}'
        self.archive = f'{self.install_path}/{self.raw_settings[Setting.ARCHIVE]}'
        self.games = [f'{self.install_path}/{_}' for _ in self.raw_settings[Setting.GAMES]]
        self.exceptions = [_.split('/')[-1] for _ in self.raw_settings[Setting.EXCEPTIONS]]

    def load(self) -> bool:
        """ Loads settings from disk and populates the application state. """
        if os.path.isfile(SETTINGS_FILE_PATH):
            with open(SETTINGS_FILE_PATH) as file_stream:
                self.raw_settings = json.load(file_stream)
            self.propagate()
            return True
        else:
            self.raw_settings = _SETTINGS_FORMAT.copy()
            return False

    def check_format(self):
        for key in _SETTINGS_FORMAT:
            if key not in self.raw_settings:
                raise InternalError(f"{key} missing")
        for key in self.raw_settings:
            if key not in _SETTINGS_FORMAT:
                raise InternalError(f"{key} not recognized")

    def check_paths(self, new_settings_dict: dict) -> bool:
        settings_result = self.raw_settings.copy()
        settings_result.update(new_settings_dict)
        try:
            completed_paths = self.complete_paths(settings_result)
            for path in completed_paths:
                if not os.path.isdir(path):
                    return False
        except InternalError:
            return False
        return True

    def save(self, key: str, value: Any):
        self.raw_settings[key] = value
        self.propagate()

        with open(SETTINGS_FILE_PATH, 'w') as file_stream:
            json.dump(self.raw_settings, file_stream, indent=4)


# Initialize the state
os.chdir(Path(__file__).parent.parent.resolve())
state = AppConfig()

if state.load():
    print("settings loaded")
