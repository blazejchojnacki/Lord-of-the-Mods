import inspect
import os

from constants import LOG_PATH


def log(output, file='file_changes.txt'):
    if not os.path.isdir(LOG_PATH):
        os.mkdir(LOG_PATH)
    if os.path.isfile(f'{LOG_PATH}/{file}'):
        with open(f'{LOG_PATH}/{file}', 'a') as log_file:
            log_file.write(output + '\n')
    elif os.path.isfile(f'.{LOG_PATH}/{file}'):
        with open(f'.{LOG_PATH}/{file}', 'a') as log_file:
            log_file.write(output + '\n')
    elif os.path.isdir(LOG_PATH):
        with open(f'{LOG_PATH}/{file}', 'w') as log_file:
            log_file.write(output + '\n')
    elif os.path.isdir(f'.{LOG_PATH}'):
        with open(f'.{LOG_PATH}/{file}', 'w') as log_file:
            log_file.write(output + '\n')


def get_calling_module(steps: int = 2):
    frame = inspect.currentframe()
    for step_back in range(steps):
        frame = frame.f_back
    module_name_full = str(inspect.getmodule(frame))
    return module_name_full[module_name_full.rfind('\\') + len('\\'):module_name_full.rfind('.')]


def get_calling_object(steps: int = 1):
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
        self.message = f'{get_calling_module()}.{get_calling_object(2)} error: {message}'
        super().__init__(message)


class InternalWarning(Warning):
    """
    The warning internal to this program - called when a behavior has to be pointed out
    :param: message (optional) - details conveyed after the module name and function name that called it
    """
    def __init__(self, message: str = ''):
        self.message = f'{get_calling_module()}.{get_calling_object(2)} warning: {message}'
        super().__init__(self.message)


def internal_message(message):
    return f'{get_calling_module()}.{get_calling_object(2)}: {message}'
