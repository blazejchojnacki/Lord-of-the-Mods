import os.path
import json
import inspect


PROGRAM_NAME = 'Lord of the Mods'
MAIN_DIRECTORY = os.path.abspath('..').replace('\\', '/')
LOG_PATH = './change_logs'
INI_PATH_PART = '/data/ini'
LEVEL_INDENT = ' ' * 4
INI_COMMENTS = [';', '/']
INI_ENDS = ['End', 'END', 'EndScript']
INI_DELIMITERS = []
STR_DELIMITERS = []

SETTINGS_PATH = './_settings.json'
LIBRARY: str
ARCHIVE: str
current: dict
KEY_TITLE = "title"
KEY_VERSION = "version"
KEY_LIBRARY = "LibraryDirectory"
KEY_ARCHIVE = "ArchiveDirectory"
KEY_GAMES = "GamesDirectories"
KEY_EXCEPTIONS = "LibraryExceptions"
_SETTINGS_FORMAT = {
    KEY_TITLE: "Lord of the Mods Settings",
    KEY_VERSION: "",
    KEY_LIBRARY: "",
    KEY_ARCHIVE: "",
    KEY_GAMES: [],
    KEY_EXCEPTIONS: []
}


def this_module():
    module_name_full = str(inspect.getmodule(inspect.currentframe().f_back.f_back))
    return module_name_full[module_name_full.rfind('\\') + len('\\'):module_name_full.rfind('.')]


def this_object(steps: int = 1):
    frame = inspect.currentframe()
    for step_back in range(steps):
        frame = frame.f_back
    return frame.f_code.co_qualname


class InternalError(Exception):
    """
    The Error internal to this program - called when a behavior has to be blocked
    :param: message (optional) - details conveyed after the module name and function name that called it
    """
    def __init__(self, message: str = ''):
        self.message = f'{this_module()}.{this_object(2)} error: {message}'
        super().__init__(message)


class InternalWarning(Warning):
    """
    The warning internal to this program - called when a behavior has to be pointed out
    :param: message (optional) - details conveyed after the module name and function name that called it
    """
    def __init__(self, message: str = ''):
        self.message = f'{this_module()}.{this_object(2)} warning: {message}'
        super().__init__(self.message)


# # # load delimiters
for delimiter_path in ['./_delimiters_ini.json', './_delimiters_str.json']:
    if os.path.isfile(delimiter_path or f".{delimiter_path}"):
        if os.path.isfile(f".{delimiter_path}"):
            delimiter_path = f".{delimiter_path}"
        with open(delimiter_path) as delimiters_buffer:
            if '_ini' in delimiter_path:
                INI_DELIMITERS = json.load(delimiters_buffer)
            elif '_str' in delimiter_path:
                STR_DELIMITERS = json.load(delimiters_buffer)
    else:
        raise InternalError("delimiters files not found")


def settings_get(mode: str = 'dict', settings_dict: dict = None):
    """
    Checks if the parameters of the settings file respect the hardcoded form. Checks if all given paths exist.
     The non-existing ones raise an InternalError if mode=='check' or are created if mode=='initiate'.
    :param settings_dict: initial dictionary of settings
    :param mode: 'dict' (default) | 'initiate' | 'check'
    :return: if mode=='dict': a JSON-compatible dict with hardcoded keys - valueless if the file is not found
    """
    global LIBRARY, ARCHIVE, current
    if not settings_dict and os.path.isfile(SETTINGS_PATH):
        with open(SETTINGS_PATH) as settings_buffer:
            settings_dict = json.load(settings_buffer)
    if not settings_dict:
        if mode == 'dict':
            return _SETTINGS_FORMAT
    else:
        for key in settings_dict:
            if key == KEY_TITLE or key == KEY_VERSION or key == KEY_EXCEPTIONS:
                pass
            elif settings_dict[key]:
                if isinstance(settings_dict[key], list):
                    for path in settings_dict[key]:
                        if path and not os.path.isdir(path):
                            if mode == 'check':
                                raise InternalError(f'{path} not recognized')
                            elif mode == 'initiate':
                                os.makedirs(path)
                elif isinstance(settings_dict[key], str):
                    if not os.path.isdir(settings_dict[key]):
                        if mode == 'check':
                            raise InternalError(f'{settings_dict[key]} not recognized')
                        elif mode == 'initiate':
                            os.makedirs(settings_dict[key])
                else:
                    if mode == 'check':
                        raise InternalError(f'{settings_dict[key]} not recognized')
            else:
                # print(f'missing value for key: {key}')
                pass
        if mode == 'dict':
            LIBRARY = settings_dict[KEY_LIBRARY]
            ARCHIVE = settings_dict[KEY_ARCHIVE]
            current = settings_dict
            return settings_dict


settings_get()


def settings_set(settings_dict=None, do_initiate: bool = False, new_settings=None):
    """
    Saves the values provided (inserted in the application) to the SETTING_FILE.
    Then it checks if the new settings are valid. If not, retrieves the backed up settings.
    :param settings_dict: settings organized in a dictionary
    :param do_initiate: if True, creates the folders provided
    :param new_settings: settings as key-word arguments-values pairs
    :return: boolean success or failure to find the paths provided
    """
    global LIBRARY, ARCHIVE, current
    if settings_dict and not new_settings:
        new_settings = settings_dict
    settings_json = settings_get()
    settings_json_new = {}
    for key in settings_json:
        if key in new_settings:
            if isinstance(new_settings[key], str) and isinstance(settings_json[key], str):
                settings_json_new[key] = new_settings[key]
            elif isinstance(new_settings[key], str) and isinstance(settings_json[key], list):
                settings_json_new[key] = settings_json[key]
                settings_json_new[key].append(new_settings[key])
            elif isinstance(new_settings[key], list) and isinstance(settings_json[key], list):
                settings_json_new[key] = new_settings[key]
        else:
            settings_json_new[key] = settings_json[key]
    try:
        if do_initiate:
            settings_get(mode='initiate', settings_dict=settings_json_new)
        else:
            settings_get(mode='check', settings_dict=settings_json_new)
        with open(SETTINGS_PATH, 'w') as settings_buffer:
            settings_buffer.write(json.dumps(settings_json_new, indent=4))
        LIBRARY = settings_json_new[KEY_LIBRARY]
        ARCHIVE = settings_json_new[KEY_ARCHIVE]
        current = settings_json_new
        return True
    except InternalError:
        return False
