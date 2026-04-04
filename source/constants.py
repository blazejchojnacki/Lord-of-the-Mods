import os
from datetime import datetime
from enum import StrEnum

from source.shared import LOG_PATH

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


PRINT_COLORS = {
    'information': '\033[96m',
    'warning': '\033[93m',
    'error': '\033[91m',
    'end': '\033[0m',
}


TEST = False


def log(output):
    """ Saves the given text into the main change log. """
    text = ''
    if TEST:
        for importance_level in PRINT_COLORS[:-1]:
            if importance_level in output:
                text = (output[:output.index(importance_level)] + PRINT_COLORS[importance_level] + importance_level
                        + PRINT_COLORS['end'] + output[output.index(importance_level) + len(importance_level):])
        if text:
            print(text)
        else:
            print(output)
    else:
        date = str(datetime.now()) + '\t'
        if not os.path.isdir(LOG_PATH):
            os.mkdir(LOG_PATH)
        try:
            with open(f'{LOG_PATH}/main_change_log.txt', 'a') as log_buffer:
                log_buffer.write(date + output + '\n')
        except FileNotFoundError:
            with open(f'{LOG_PATH}/main_change_log.txt', 'w') as log_buffer:
                log_buffer.write(date + output + '\n')
    return output
