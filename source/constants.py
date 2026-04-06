import os
import json
from enum import StrEnum
from pathlib import Path

from source.messaging import InternalError

PROGRAM_NAME = 'Lord of the Mods'
# THIS_PATH = Path(__file__).parent.resolve()
MAIN_DIRECTORY = str(Path(__file__).parent.parent.resolve()).replace('\\', '/').strip('/')
MOD_DEF_FILE_NAME = '_definition.json'
# LOG_PATH = f'{MAIN_DIRECTORY}/change_logs'
LEVEL_INDENT = ' ' * 4
INI_COMMENTS = [';', '/']
INI_ENDS = ['End', 'END', 'EndScript']
INI_DELIMITERS = []
STR_DELIMITERS = []


def load_delimiters():
    global INI_DELIMITERS, STR_DELIMITERS
    for delimiter_path in [f'{MAIN_DIRECTORY}/_delimiters_ini.json', f'{MAIN_DIRECTORY}/_delimiters_str.json']:
        if os.path.isfile(delimiter_path):
            with open(delimiter_path) as delimiters_buffer:
                if '_ini' in delimiter_path:
                    INI_DELIMITERS = json.load(delimiters_buffer)
                elif '_str' in delimiter_path:
                    STR_DELIMITERS = json.load(delimiters_buffer)
        else:
            raise InternalError("delimiters files not found")


load_delimiters()


class Setting(StrEnum):
    TITLE = "title"
    VERSION = "version"
    INSTALL = "InstallPath"
    LIBRARY = "LibraryDirectory"
    ARCHIVE = "ArchiveDirectory"
    GAMES = "GamesDirectories"
    EXCEPTIONS = "LibraryExceptions"


SETTINGS_FILE_PATH = f'{MAIN_DIRECTORY}/_settings.json'
_SETTINGS_FORMAT = {
    Setting.TITLE: "Lord of the Mods Settings",
    Setting.VERSION: "",
    Setting.INSTALL: "",
    Setting.LIBRARY: "",
    Setting.ARCHIVE: "",
    Setting.GAMES: [],
    Setting.EXCEPTIONS: []
}

SNAPSHOT_DIRECTORY = './snapshots'
SNAPSHOT_NAME = 'file_snapshot_'
SNAPSHOT_COMPARISON_DIRECTORY = './snapshot_comparisons'
COMPARISON_NAME = 'comparison_'


class Transfer(StrEnum):
    MOVE = 'move'
    COPY = 'copy'
    DELETE = 'delete'
    REMOVE = 'remove'


class Property(StrEnum):
    TRANSFER_TYPE = "class"
    NAME = "name"
    GAME = "game"
    LAUNCH = "launch"
    ACTIVE = "active"
    OVERRIDES = "ancestor"
    OVERRODE_BY = "heir"
    DESCRIPTION = "description"
    CHANGES = "changes"


DEFINITION_NAME = '_definition.json'
DEFINITION_CLASSES = ['General', 'Clone', 'Foundling', 'Template']
DEFINITION_TEMPLATE = {
    Property.TRANSFER_TYPE: '',
    Property.NAME: '',
    Property.GAME: '',
    Property.LAUNCH: "",
    Property.ACTIVE: False,
    Property.OVERRIDES: '',
    Property.OVERRODE_BY: '',
    Property.DESCRIPTION: '',
    Property.CHANGES: {}
}


class Change(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
