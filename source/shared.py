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


def load_delimiters():
    global INI_DELIMITERS, STR_DELIMITERS
    if os.path.isfile('./_delimiters_ini.json'):
        with open('./_delimiters_ini.json') as delimiters_buffer:
            INI_DELIMITERS = json.load(delimiters_buffer)
    if os.path.isfile('./_delimiters_str.json'):
        with open('./_delimiters_str.json') as delimiters_buffer:
            STR_DELIMITERS = json.load(delimiters_buffer)


load_delimiters()
