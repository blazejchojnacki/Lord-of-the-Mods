import inspect
import logging
import os
from pathlib import Path

LOG_PATH = f"{Path(__file__).parent.parent.resolve()}/logging"


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: '\033[96m',
        logging.WARNING: '\033[93m',
        logging.ERROR: '\033[91m',
        'END': '\033[0m'
    }

    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelno, self.COLORS['END'])
        return f"{color}{log_message}{self.COLORS['END']}"


def get_custom_logger(logger_name: str, file_name: str) -> logging.Logger:
    """
    Creates or retrieves a logger mapped to a specific file.
    """
    # Ask Python for a logger with this specific name
    custom_logger = logging.getLogger(logger_name)

    # IMPORTANT: If it already has handlers, we already set it up previously!
    # We just return it to avoid duplicating lines in the log file.
    if custom_logger.hasHandlers():
        return custom_logger

    custom_logger.setLevel(logging.DEBUG)
    os.makedirs(LOG_PATH, exist_ok=True)

    # 1. Attach the File Handler for this specific file
    file_path = f"{LOG_PATH}/{file_name}"
    file_handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s'))
    custom_logger.addHandler(file_handler)

    # 2. Attach the Console Handler (Optional: remove this if you want
    # secondary logs to ONLY go to the file and not clutter the console)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorFormatter('%(levelname)s: %(message)s'))
    custom_logger.addHandler(console_handler)

    return custom_logger


log = get_custom_logger("main", "main_change_log.txt")


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
