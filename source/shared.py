import os.path
import json
import inspect


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


LOG_PATH = './change_logs'
PROGRAM_NAME = 'Lord of the Mods'
INI_PATH_PART = '/data/ini'
LEVEL_INDENT = ' ' * 4
INI_COMMENTS = [';', '/']
INI_ENDS = ['End', 'END', 'EndScript']
INI_DELIMITERS = []
STR_DELIMITERS = []

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
