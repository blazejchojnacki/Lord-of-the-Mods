import os.path
import json
import inspect
import tkinter
import _tkinter
from ctypes import windll, byref, sizeof, c_int, create_unicode_buffer

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

UNIT_WIDTH = 80
UNIT_HEIGHT = 40
DOUBLE_WIDTH = UNIT_WIDTH * 2
TEXT_WIDTH = UNIT_WIDTH * 12
FULL_WIDTH = UNIT_WIDTH * 15

# # # default aesthetic
FONT_TEXT = ('Lato', 11, 'normal')
FONT_BUTTON = ('Lato', 11, 'normal')
APP_BACKGROUND_COLOR = "#303840"
ENTRY_BACKGROUND_COLOR = "#292F36"
TEXT_COLORS = ["#C9AB69", "#757364", "#ABA298", "#484D43"]
INI_LEVEL_COLORS = ["#81B895", "#7B9AAB", "#8C7EAB", "#AB7D8C", "#7DAB9B"]
BUTTON_SMALL_IDLE = None  # tkinter.PhotoImage(file='./aesthetic/button_small_idle.png')
BUTTON_SMALL_HOVER = None  # tkinter.PhotoImage(file='./aesthetic/button_small_hover.png')
BUTTON_LARGE_IDLE = None  # tkinter.PhotoImage(file='./aesthetic/button_large_idle.png')
BUTTON_LARGE_HOVER = None  # tkinter.PhotoImage(file='./aesthetic/button_large_hover.png')

# # # global variable
current_info: tkinter.Toplevel
main_window: tkinter.Tk


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
    if os.path.isfile(delimiter_path) or os.path.isfile(f".{delimiter_path}"):
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


class ReactiveButton(tkinter.Button):
    """
    tkinter Button but changing its image on hovering and with showing an info popup on its master Window
    """
    def __init__(self, info_content='', small=False, **kwargs):
        super().__init__(**kwargs)
        if small:
            self.default_image = BUTTON_SMALL_IDLE
            self.active_image = BUTTON_SMALL_HOVER
        else:
            self.default_image = BUTTON_LARGE_IDLE
            self.active_image = BUTTON_LARGE_HOVER
        self.bind('<Enter>', self.on_hover)
        self.bind('<Leave>', self.out_hover)
        self.info_content = info_content
        self.info_id = ''
        self.super_master = main_window
        self.info = current_info
        self.configure(image=self.default_image, background=APP_BACKGROUND_COLOR)

    def on_hover(self, event=None):
        if event:
            pass
        self.configure(image=self.active_image, background=ENTRY_BACKGROUND_COLOR)
        self.info_id = self.super_master.after(1000, self.display_info)

    def out_hover(self, event=None):
        if event:
            pass
        self.configure(image=self.default_image, background=APP_BACKGROUND_COLOR)
        try:
            self.super_master.after_cancel(self.info_id)
            try:
                self.info.destroy()
            except NameError:
                pass
        except AttributeError:
            pass

    def display_info(self):
        if self.info_content:
            info_box = tkinter.Toplevel(master=self.super_master)
            try:
                self.info.destroy()
            except NameError:
                pass
            self.info = info_box
            info_box.winfo_x()
            info_box.overrideredirect(True)
            info_box.attributes('-topmost', True)
            info_box.configure(background=APP_BACKGROUND_COLOR, relief='ridge', borderwidth=5, padx=5, pady=5)
            info_text = tkinter.Label(master=info_box, text=self.info_content)
            info_text.pack()
            info_text.configure(background=APP_BACKGROUND_COLOR, foreground=TEXT_COLORS[0])
            cursor_x = self.super_master.winfo_pointerx()
            cursor_y = self.super_master.winfo_pointery()
            info_box.geometry(f'+{cursor_x}+{cursor_y - info_text.winfo_height() * UNIT_HEIGHT - 10}')

    def set(self, settings):
        for setting in settings:
            if setting == 'text':
                self.configure(**{setting: settings[setting].upper()})
            elif setting == 'info_content':
                self.info_content = settings[setting]
            else:
                try:
                    self.configure(**{setting: settings[setting]})
                except _tkinter.TclError:
                    print(f'button.set: unrecognized key {setting}')


def set_title_bar_color(window):
    """based on https://stackoverflow.com/questions/67444141/how-to-change-the-title-bar-in-tkinter"""
    window.update()
    hwnd = windll.user32.GetParent(window.winfo_id())
    dwmwa_caption_color = 35
    color_r = int(APP_BACKGROUND_COLOR[1:3], base=16)
    color_g = int(APP_BACKGROUND_COLOR[3:5], base=16)
    color_b = int(APP_BACKGROUND_COLOR[5:7], base=16)
    reformatted_color = color_b * 16 ** 4 + color_g * 16 ** 2 + color_r
    windll.dwmapi.DwmSetWindowAttribute(hwnd, dwmwa_caption_color, byref(c_int(reformatted_color)), sizeof(c_int))


def load_aesthetic():
    """
    Loads the aesthetic variables from the .json file into the application.
    """
    global APP_BACKGROUND_COLOR, ENTRY_BACKGROUND_COLOR, TEXT_COLORS, INI_LEVEL_COLORS, FONT_TEXT, FONT_BUTTON, \
        BUTTON_SMALL_IDLE, BUTTON_SMALL_HOVER, BUTTON_LARGE_IDLE, BUTTON_LARGE_HOVER
    if os.path.isfile('./aesthetic/aesthetic.json'):
        with open('./aesthetic/aesthetic.json') as aesthetic_buffer:
            aesthetic_json = json.load(aesthetic_buffer)
        APP_BACKGROUND_COLOR = aesthetic_json["APP_BACKGROUND_COLOR"]
        ENTRY_BACKGROUND_COLOR = aesthetic_json["ENTRY_BACKGROUND_COLOR"]
        TEXT_COLORS = aesthetic_json["TEXT_COLORS"]
        INI_LEVEL_COLORS = aesthetic_json["INI_LEVEL_COLORS"]
        BUTTON_SMALL_IDLE = tkinter.PhotoImage(file='./aesthetic/button_small_idle.png')
        BUTTON_SMALL_HOVER = tkinter.PhotoImage(file='./aesthetic/button_small_hover.png')
        BUTTON_LARGE_IDLE = tkinter.PhotoImage(file='./aesthetic/button_large_idle.png')
        BUTTON_LARGE_HOVER = tkinter.PhotoImage(file='./aesthetic/button_large_hover.png')
        font_path = f'./aesthetic/{aesthetic_json["FONT_FILE_NAME"]}'
        '''based on https://stackoverflow.com/questions/11993290/truly-custom-font-in-tkinter'''
        # https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
        if os.path.isfile(font_path):
            path_buf = create_unicode_buffer(font_path)
            flags = (0x10 | 0)
            num_fonts_added = windll.gdi32.AddFontResourceExW(byref(path_buf), flags, 0)
            if num_fonts_added:
                FONT_TEXT = (aesthetic_json["FONT_NAME"], aesthetic_json["FONT_SIZE_TEXT"], aesthetic_json["FONT_TYPE"])
                FONT_BUTTON = (aesthetic_json["FONT_NAME"], aesthetic_json["FONT_SIZE_BUTTON"],
                               aesthetic_json["FONT_TYPE"])
