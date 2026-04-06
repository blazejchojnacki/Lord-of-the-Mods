import os.path
import json
import tkinter
import _tkinter
from ctypes import windll, byref, sizeof, c_int, create_unicode_buffer

from source.constants import MAIN_DIRECTORY, PROGRAM_NAME

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


class ReactiveButton(tkinter.Button):
    """ A self-contained button that handles its own hover states and floating info. """

    def __init__(self, master, small=False, info_content='', **kwargs):
        # Base styling setup
        super().__init__(master, **kwargs)
        self.info_content = info_content
        self.tooltip_window = None

        # Style configuration (adjust to your shared.py constants)
        self.configure(
            bg=ENTRY_BACKGROUND_COLOR,
            fg=TEXT_COLORS[0],
            activebackground=APP_BACKGROUND_COLOR,
            activeforeground=TEXT_COLORS[0]
        )

        # Bind hover events
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _on_enter(self, event):
        """ Triggered when the mouse hovers over the button. """
        # 1. Handle visual hover effect (if any)
        # self.configure(bg=APP_BACKGROUND_COLOR)

        # 2. Show floating info if it exists
        if self.info_content:
            self._show_tooltip()

    def _on_leave(self, event):
        """ Triggered when the mouse leaves the button. """
        # 1. Revert visual hover effect
        # self.configure(bg=ENTRY_BACKGROUND_COLOR)

        # 2. Destroy the tooltip
        self._hide_tooltip()

    def _show_tooltip(self):
        """ Creates a borderless Toplevel window right next to the button. """
        if self.tooltip_window or not self.info_content:
            return

        # Create a borderless window
        self.tooltip_window = tkinter.Toplevel(self)
        self.tooltip_window.overrideredirect(True)  # Removes the window frame/title bar

        # Calculate screen position (right below the button)
        x = self.winfo_rootx() + 20
        y = self.winfo_rooty() + self.winfo_height() + 5
        self.tooltip_window.geometry(f"+{x}+{y}")

        # Add the text label
        label = tkinter.Label(
            self.tooltip_window,
            text=self.info_content,
            justify='left',
            background="#ffffe0",  # Light yellow tooltip background
            relief='solid',
            borderwidth=1,
            font=("Arial", 9)
        )
        label.pack(ipadx=3, ipady=1)

    def _hide_tooltip(self):
        """ Safely destroys the tooltip window. """
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


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
        if os.path.isfile(ICON_PATH):
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
