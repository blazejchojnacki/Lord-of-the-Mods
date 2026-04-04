import inspect
import logging
import os
from datetime import datetime

LOG_PATH = './logging'


# 1. Custom Formatter to keep your colors for the console!
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: '\033[96m',     # Cyan for information
        logging.WARNING: '\033[93m',  # Yellow for warnings
        logging.ERROR: '\033[91m',    # Red for errors
        'END': '\033[0m'
    }

    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelno, self.COLORS['END'])
        return f"{color}{log_message}{self.COLORS['END']}"


def setup_logger():
    if not os.path.isdir(LOG_PATH):
        os.mkdir(LOG_PATH)

    # 2. Create the core logger
    app_logger = logging.getLogger("Modificator")
    app_logger.setLevel(logging.DEBUG)

    # 3. Create File Handler (writes standard text to the file)
    file_path = f"{LOG_PATH}/main_change_log.txt"
    file_handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')
    file_format = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    file_handler.setFormatter(file_format)
    app_logger.addHandler(file_handler)

    # 4. Create Console Handler (prints colors to the terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorFormatter('%(levelname)s: %(message)s'))
    app_logger.addHandler(console_handler)

    return app_logger


# Initialize it once so the rest of the app can use it
log = setup_logger()


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
