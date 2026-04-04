import os.path
import json
import inspect
import tkinter
import _tkinter
from ctypes import windll, byref, sizeof, c_int, create_unicode_buffer
from enum import StrEnum
from pathlib import Path

PROGRAM_NAME = 'Lord of the Mods'
THIS_PATH = Path(__file__).parent.resolve()
MAIN_DIRECTORY = Path(__file__).parent.parent.resolve()
MOD_DEF_FILE_NAME = '_definition.json'
LOG_PATH = f'{MAIN_DIRECTORY}/change_logs'
LEVEL_INDENT = ' ' * 4
INI_COMMENTS = [';', '/']
INI_ENDS = ['End', 'END', 'EndScript']
INI_DELIMITERS = []
STR_DELIMITERS = []


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

UNIT_WIDTH = 80
UNIT_HEIGHT = 40
DOUBLE_WIDTH = UNIT_WIDTH * 2
TEXT_WIDTH = UNIT_WIDTH * 12
FULL_WIDTH = UNIT_WIDTH * 15
LIST_WIDTH = 160

# # # default aesthetic
FONT_TEXT = ('Lato', 11, 'normal')
FONT_BUTTON = ('Lato', 11, 'normal')
APP_BACKGROUND_COLOR = "#303840"
ENTRY_BACKGROUND_COLOR = "#292F36"
TEXT_COLORS = ["#C9AB69", "#757364", "#ABA298", "#484D43"]
INI_LEVEL_COLORS = ["#81B895", "#7B9AAB", "#8C7EAB", "#AB7D8C", "#7DAB9B"]
BUTTON_SMALL_IDLE = None
BUTTON_SMALL_HOVER = None
BUTTON_LARGE_IDLE = None
BUTTON_LARGE_HOVER = None
ICON_PATH = ''
KEY_LABEL = 'label'
KEY_RETURN = 'command'
KEY_INFO = 'info'
AESTHETIC_PATH = f'{MAIN_DIRECTORY}/aesthetic/'

# # # global variable
main_window: tkinter.Tk
current_info: tkinter.Toplevel


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


# # # load delimiters
for delimiter_path in [f'{MAIN_DIRECTORY}/_delimiters_ini.json', f'{MAIN_DIRECTORY}/_delimiters_str.json']:
    if os.path.isfile(delimiter_path):
        with open(delimiter_path) as delimiters_buffer:
            if '_ini' in delimiter_path:
                INI_DELIMITERS = json.load(delimiters_buffer)
            elif '_str' in delimiter_path:
                STR_DELIMITERS = json.load(delimiters_buffer)
    else:
        raise InternalError("delimiters files not found")


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
        if self.default_image:
            self.configure(image=self.default_image)
        self.configure(compound='center', foreground=TEXT_COLORS[0], font=FONT_BUTTON,
                       background=APP_BACKGROUND_COLOR, activebackground=APP_BACKGROUND_COLOR)

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
        BUTTON_SMALL_IDLE, BUTTON_SMALL_HOVER, BUTTON_LARGE_IDLE, BUTTON_LARGE_HOVER, ICON_PATH
    if os.path.isfile(f'{AESTHETIC_PATH}icon.ico'):
        ICON_PATH = f'{AESTHETIC_PATH}icon.ico'
    if os.path.isfile(f'{AESTHETIC_PATH}aesthetic.json'):
        with open(f'{AESTHETIC_PATH}aesthetic.json') as aesthetic_buffer:
            aesthetic_json = json.load(aesthetic_buffer)
        APP_BACKGROUND_COLOR = aesthetic_json["APP_BACKGROUND_COLOR"]
        ENTRY_BACKGROUND_COLOR = aesthetic_json["ENTRY_BACKGROUND_COLOR"]
        TEXT_COLORS = aesthetic_json["TEXT_COLORS"]
        INI_LEVEL_COLORS = aesthetic_json["INI_LEVEL_COLORS"]
        BUTTON_SMALL_IDLE = tkinter.PhotoImage(file=f'{AESTHETIC_PATH}button_small_idle.png')
        BUTTON_SMALL_HOVER = tkinter.PhotoImage(file=f'{AESTHETIC_PATH}button_small_hover.png')
        BUTTON_LARGE_IDLE = tkinter.PhotoImage(file=f'{AESTHETIC_PATH}button_large_idle.png')
        BUTTON_LARGE_HOVER = tkinter.PhotoImage(file=f'{AESTHETIC_PATH}button_large_hover.png')
        font_path = f'{AESTHETIC_PATH}{aesthetic_json["FONT_FILE_NAME"]}'
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


class ChoiceWindow(tkinter.Toplevel):
    """
    TK-based popping window for choices. Replacing askquestions etc.
    """
    def __init__(self, title, text, buttons):
        super().__init__()
        load_aesthetic()
        set_title_bar_color(self)
        if os.path.isfile(f'{AESTHETIC_PATH}icon.ico'):
            self.iconbitmap(ICON_PATH)
        self.width = DOUBLE_WIDTH*4
        self.height = UNIT_HEIGHT*6
        self.geometry(f'{self.width}x{self.height}')
        self.attributes('-topmost', True)
        self.configure(background=APP_BACKGROUND_COLOR)
        self.protocol("WM_DELETE_WINDOW", self.on_choosing)
        self.title = f'{PROGRAM_NAME}: {title}'
        # OPTIMIZE: the changes text is truncated
        self.text_label = tkinter.Label(master=self, background=APP_BACKGROUND_COLOR, font=FONT_TEXT, text=text[:1000],
                                        foreground=TEXT_COLORS[0])
        self.text_label.place(x=UNIT_WIDTH, y=UNIT_HEIGHT, width=self.width-2*UNIT_WIDTH, height=UNIT_HEIGHT*2)
        self.container_buttons = tkinter.Frame(self, background=APP_BACKGROUND_COLOR)
        self.container_buttons.place(x=0, y=UNIT_HEIGHT*3, width=self.width, height=self.height)
        self.buttons = []
        for button in buttons:
            self.add_button(button[KEY_LABEL], button[KEY_RETURN], button[KEY_INFO])
        self.rearrange()
        self.chosen_value = False
        self.mainloop()

    def on_choosing(self, value=None):
        self.quit()
        self.destroy()
        self.chosen_value = value
        return value

    def add_button(self, label: str, value: object, info: str, position: int = None):
        if position is None:
            position = len(self.buttons)
        self.buttons.insert(position, ReactiveButton(
            info_content=info, text=label, master=self.container_buttons, command=lambda: self.on_choosing(value)))

    def rearrange(self):
        for button in self.buttons:
            button.place(x=UNIT_WIDTH*(self.buttons.index(button)+1)*2,
                         y=UNIT_HEIGHT, width=UNIT_WIDTH, height=UNIT_HEIGHT, anchor='ne')


def invoke_choice(**key_args):
    choice_window = ChoiceWindow(**key_args)
    return choice_window.chosen_value
