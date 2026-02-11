import os.path
import tkinter
import _tkinter
from tkinter.messagebox import askquestion
from tkinter.filedialog import askopenfilenames, askdirectory
from tkinter.ttk import Treeview
from tklinenums import TkLineNumbers

import source.shared as s
from source.initiator import initiate
from source.constructor import load_file, load_directories
from source.editor import reformat_string, text_find_replace, move_file, duplicates_find
from source.module_control import modules_filter, modules_sort, snapshot_take, snapshot_compare, \
    module_detect_changes, module_copy, detect_new_modules, \
    definition_edit, DEFINITION_EXAMPLE, DEFINITION_NAME, DEFINITION_CLASSES

UNIT_WIDTH = 80
UNIT_HEIGHT = 40
TEXT_WIDTH = UNIT_WIDTH * 12
FULL_WIDTH = UNIT_WIDTH * 15
LIST_WIDTH = 160
# MODULE_COLUMNS = ('name', 'class', 'progress', 'description')
MODULE_COLUMNS = {'name': 1, 'class': 1, 'progress': 1, 'description': 5}

new_module_name = ''
new_module_source = ''


class NewModuleDialog(tkinter.Toplevel):
    """ a Tk/TCl Toplevel-based class """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.title = f'{s.PROGRAM_NAME}: new module initiator'
        self.iconbitmap('aesthetic/icon.ico')
        self.geometry('320x360')
        self.resizable(False, False)
        self.configure(background=s.APP_BACKGROUND_COLOR)
        s.set_title_bar_color(self)

        self.name_label = tkinter.Label(master=self)
        self.name_label.place(x=UNIT_WIDTH * 0, y=UNIT_HEIGHT * 0, width=UNIT_WIDTH * 4, height=UNIT_HEIGHT)
        self.name_label.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], text='Please provide the new module name')
        self.name_entry = tkinter.Entry(master=self)
        self.name_entry.place(x=int(UNIT_WIDTH * 0.5), y=UNIT_HEIGHT * 1, width=UNIT_WIDTH * 3, height=UNIT_HEIGHT)
        self.name_entry.configure(background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0])
        self.options_label = tkinter.Label(master=self)
        self.options_label.place(x=UNIT_WIDTH * 0, y=UNIT_HEIGHT * 3, width=UNIT_WIDTH * 4, height=UNIT_HEIGHT)
        self.options_label.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0],
            text='Please choose the definition creation mode')
        self.options_container = tkinter.Frame(master=self)
        self.options_container.place(x=int(UNIT_WIDTH * 0.5), y=UNIT_HEIGHT * 4, width=UNIT_WIDTH * 3,
                                     height=UNIT_HEIGHT * 3)
        self.options_container.configure(background=s.ENTRY_BACKGROUND_COLOR)
        self.variable_option = tkinter.StringVar()
        option_button_a = tkinter.Checkbutton(
            master=self.options_container, text='present directory', variable=self.variable_option, onvalue='directory')
        option_button_a.place(x=UNIT_WIDTH * 0, y=UNIT_HEIGHT * 0, width=2 * UNIT_WIDTH, height=UNIT_HEIGHT)
        option_button_a.configure(background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0],
                                  activebackground=s.APP_BACKGROUND_COLOR, activeforeground=s.TEXT_COLORS[0],
                                  selectcolor=s.ENTRY_BACKGROUND_COLOR)
        option_button_b = tkinter.Checkbutton(
            master=self.options_container, text='comparison', variable=self.variable_option, onvalue='comparison')
        option_button_b.place(x=UNIT_WIDTH * 0, y=UNIT_HEIGHT * 1, width=2 * UNIT_WIDTH, height=UNIT_HEIGHT)
        option_button_b.configure(background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0],
                                  activebackground=s.APP_BACKGROUND_COLOR, activeforeground=s.TEXT_COLORS[0],
                                  selectcolor=s.ENTRY_BACKGROUND_COLOR)
        option_button_c = tkinter.Checkbutton(
            master=self.options_container, text='snapshot', variable=self.variable_option, onvalue='snapshot')
        option_button_c.place(x=UNIT_WIDTH * 0, y=UNIT_HEIGHT * 2, width=2 * UNIT_WIDTH, height=UNIT_HEIGHT)
        option_button_c.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], selectcolor=s.ENTRY_BACKGROUND_COLOR,
            activebackground=s.APP_BACKGROUND_COLOR, activeforeground=s.TEXT_COLORS[0])
        option_button_a.select()

        self.ok_button = s.ReactiveButton(master=self, text='run', command=self.return_entry)
        self.ok_button.place(x=int(UNIT_WIDTH * 0.5), y=int(UNIT_HEIGHT * 7.5), width=UNIT_WIDTH, height=UNIT_HEIGHT)
        self.ok_button.configure(
            background=s.APP_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], image=s.BUTTON_SMALL_IDLE,
            activebackground=s.APP_BACKGROUND_COLOR, borderwidth=0, compound='center'
        )
        self.cancel_button = s.ReactiveButton(master=self, text='cancel', command=self.return_cancel)
        self.cancel_button.place(x=int(UNIT_WIDTH * 2.5), y=int(UNIT_HEIGHT * 7.5), width=UNIT_WIDTH,
                                 height=UNIT_HEIGHT)
        self.cancel_button.configure(
            background=s.APP_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], image=s.BUTTON_SMALL_IDLE,
            activebackground=s.APP_BACKGROUND_COLOR, borderwidth=0, compound='center'
        )
        self.protocol("WM_DELETE_WINDOW", self.return_cancel)
        self.mainloop()

    def return_entry(self):
        global new_module_name, new_module_source
        all_module_names = modules_filter(return_type='names')
        if self.name_entry.get() and self.variable_option.get() and self.name_entry.get() not in all_module_names:
            new_module_name = self.name_entry.get()
            new_module_source = self.variable_option.get()
            self.quit()
            self.destroy()
        else:
            self.name_label.configure(text=' Please provide a name unique to the new module')

    def return_cancel(self):
        global new_module_name, new_module_source
        new_module_name, new_module_source = '', ''
        self.quit()
        self.destroy()


class ColumnedListbox(tkinter.ttk.Treeview):
    """ a Tk/Tcl Treeview-based class with predefined columns"""

    def __init__(self, master, width=0, height=0, columns=None, show='tree headings'):  # , **kw
        super().__init__(master=master, height=height, show=show)
        if columns is None:
            columns = MODULE_COLUMNS
        self.width = width
        self.columns_list = list(columns.keys())
        self.configure(columns=self.columns_list)
        for column in self.columns_list:
            self.heading(column, text=column)
        self.set_columns_proportions(list(columns.values()))

    def set_columns_proportions(self, proportions):
        total_quotient = sum(proportions, 1)
        self.column('#0', width=int(self.width / total_quotient))
        for column_index in range(len(proportions)):
            self.column(
                self.columns_list[column_index],
                width=int(self.width / total_quotient * proportions[column_index])
            )
            if column_index == len(proportions) - 1:
                self.column(
                    self.columns_list[column_index],
                    width=int(self.width / total_quotient * proportions[column_index]) - 5
                )

    def open_children(self):
        for search_index in range(10):
            open_children(self, parent=str(search_index))


def open_children(tree, parent):
    """ Recurring function to display all modules hierarchically. """
    try:
        tree.item(parent, open=True)
        for child in tree.get_children(parent):
            open_children(tree, child)
    except _tkinter.TclError:
        pass


main_window = None


class Window(tkinter.Tk):
    """ Tk-based app Window """

    def __init__(self):
        super().__init__()
        global main_window
        main_window = self
        self.current_path = ''
        self.current_window = ''

        self.global_modules = []
        self.current_levels = []
        self.current_file_content_backup = ''

        self.key_to_command_module = {
            '<Return>': self.command_browser_forward,
            '<Right>': self.focus_on_next_item,
            '<Left>': self.focus_on_next_item,
        }
        self.key_to_command_browser = {
            '<Return>': self.command_browser_forward,
            '<BackSpace>': self.command_browser_back,
            '<Escape>': self.set_window_modules,
        }
        self.key_to_command_text = {
            '<Escape>': self.command_browser_back
        }
        self.key_to_command_current = {
            '<Return>': self.set_window_modules,
        }

        initiate()

        self.iconbitmap('aesthetic/icon.ico')
        self.title(s.PROGRAM_NAME)
        self.minsize(width=1100, height=400)
        self.maxsize(width=1600, height=900)
        self.geometry('1250x650')
        self.configure(padx=10, pady=10, background=s.APP_BACKGROUND_COLOR)
        self.bind('<Key>', self.press_key_in_current_mode)
        self.bind_all('<Control-Key-f>', self.use_selected_text)
        self.bind_all('<Control-Key-r>', self.use_selected_text)
        s.set_title_bar_color(self)
        s.main_window = self
        s.current_info = tkinter.Toplevel(master=self)
        s.current_info.destroy()
        s.load_aesthetic()

        self.container_command = tkinter.Frame(master=self)
        self.container_command_buttons = tkinter.Frame(master=self.container_command)
        self.button_run = s.ReactiveButton(master=self.container_command_buttons)
        self.button_execute = s.ReactiveButton(master=self.container_command_buttons, text='clear logs'.upper(),
                                               command=self.set_log_update)
        self.text_result = tkinter.Text(master=self.container_command, state='disabled')
        self.button_menu_modules = s.ReactiveButton(
            master=self.container_command_buttons, text='modules'.upper(), command=self.set_window_modules)
        self.button_menu_back = s.ReactiveButton(master=self.container_command_buttons, text='back'.upper())
        self.button_menu_settings = s.ReactiveButton(
            master=self.container_command_buttons, text='edit settings'.upper(), command=self.set_window_settings)

        self.button_function_find = s.ReactiveButton(
            master=self.container_command_buttons, text='find text'.upper(), command=self.set_window_find)
        self.button_function_replace = s.ReactiveButton(
            master=self.container_command_buttons, text='replace text'.upper(), command=self.set_window_replace)

        self.container_current = tkinter.Frame(master=self)

        self.container_file_content = tkinter.Frame(master=self.container_current)
        self.text_file_content = tkinter.Text(master=self.container_file_content, width=TEXT_WIDTH, height=30,
                                              undo=True)
        numeration = TkLineNumbers(self.container_file_content, self.text_file_content, justify='right')
        self.event_delete('<<SelectAll>>', '<Control-Key-/>')
        self.text_file_content.bind('<Control-Key-/>', self.use_selected_text)
        self.text_file_content.bind(r'<Control-Key-\>', self.use_selected_text)
        self.text_file_content.bind('<<Modified>>', lambda event: self.after_idle(numeration.redraw), add=True)
        self.text_file_content.bind('<<Modified>>', lambda event: self.after_idle(self.set_text_color), add=True)

        self.container_settings = tkinter.Frame(master=self.container_current)
        list_labels_settings = []
        self.list_entry_settings = []
        list_buttons_settings = []
        for setting in s.current:
            if setting == 'comment':
                continue
            list_labels_settings.append(tkinter.Label(master=self.container_settings, text=setting))
            self.list_entry_settings.append(tkinter.Entry(master=self.container_settings))
            list_buttons_settings.append(s.ReactiveButton(master=self.container_settings, text='select'.upper()))

        try:
            list_buttons_settings[2].configure(command=lambda: self.settings_select_new_directory(2))
            list_buttons_settings[3].configure(command=lambda: self.settings_select_new_directory(3))
            list_buttons_settings[4].configure(command=lambda: self.settings_select_add_directory(4))
        except IndexError:
            pass

        self.container_modules = tkinter.Frame(master=self.container_current)
        label_modules_idle = tkinter.Label(master=self.container_modules, text='available modules:')
        self.treeview_modules_idle = ColumnedListbox(master=self.container_modules, width=LIST_WIDTH, height=10)
        self.treeview_modules_idle.bind('<<TreeviewSelect>>', self.on_select_module_idle)
        self.treeview_modules_idle.bind('<Double-1>', self.command_module_browse)
        container_module_buttons = tkinter.Frame(master=self.container_modules, pady=7)
        self.button_module_attach = s.ReactiveButton(
            master=container_module_buttons, text='attach module'.upper(), command=self.command_module_attach)
        self.button_module_retrieve = s.ReactiveButton(
            master=container_module_buttons, text='detach module'.upper(), command=self.command_module_retrieve)
        self.button_module_reload = s.ReactiveButton(
            master=container_module_buttons, text='reload module'.upper(), command=self.command_module_reload)
        self.button_module_browse = s.ReactiveButton(
            master=container_module_buttons, text='open module'.upper(), command=self.command_module_browse)
        self.button_module_copy = s.ReactiveButton(
            master=container_module_buttons, text='copy module'.upper(), command=self.command_module_copy)
        self.button_module_new = s.ReactiveButton(
            master=container_module_buttons, text='new module'.upper(), command=self.command_module_new)
        self.button_definition_edit = s.ReactiveButton(
            master=container_module_buttons, text='edit module data'.upper(), command=self.set_window_definition)

        label_modules_active = tkinter.Label(master=self.container_modules, text='active modules:',
                                             width=UNIT_WIDTH * 2)
        self.treeview_modules_active = ColumnedListbox(master=self.container_modules, width=LIST_WIDTH, height=10)
        self.treeview_modules_active.bind('<<TreeviewSelect>>', self.on_select_module_active)
        self.treeview_modules_active.bind('<Double-1>', self.command_module_browse)

        self.container_definition = tkinter.Frame(master=self.container_current)
        list_labels_module_editor = []
        self.list_text_definition_editor = []
        for key in DEFINITION_EXAMPLE:
            if key == 'comment' or key == 'changes':
                continue
            list_labels_module_editor.append(tkinter.Label(master=self.container_definition, text=key))
            self.list_text_definition_editor.append(tkinter.Text(master=self.container_definition))

        self.container_browser = tkinter.Frame(master=self.container_current)
        self.label_browser = tkinter.Label(master=self.container_browser)
        self.listbox_browser = tkinter.Listbox(master=self.container_browser, width=LIST_WIDTH, height=20)
        self.listbox_browser.bind('<<ListboxSelect>>', self.on_select_browser_item)
        self.listbox_browser.bind('<Double-1>', self.command_browser_forward)

        self.container_scope_select = tkinter.Frame(master=self.container_current)
        self.label_scope_select = tkinter.Label(master=self.container_scope_select, text='in file(s) or folder(s):')
        self.text_scope_select = tkinter.Text(master=self.container_scope_select)
        button_scope_select_file = s.ReactiveButton(
            master=self.container_scope_select, text='select a file'.upper(),
            command=lambda: self.command_select_file(self.text_scope_select))
        self.button_scope_select_folder = s.ReactiveButton(
            master=self.container_scope_select, text='select a folder'.upper(),
            command=lambda: self.command_select_folder(self.text_scope_select))
        self.label_scope_except = tkinter.Label(master=self.container_scope_select, text='except:')
        self.text_scope_except = tkinter.Text(master=self.container_scope_select)
        self.button_scope_except_file = s.ReactiveButton(
            master=self.container_scope_select, text='select a file'.upper(),
            command=lambda: self.command_select_file(self.text_scope_except))
        button_scope_except_folder = s.ReactiveButton(
            master=self.container_scope_select, text='select a folder'.upper(),
            command=lambda: self.command_select_folder(self.text_scope_except))

        self.container_find = tkinter.Frame(master=self.container_current)
        label_find = tkinter.Label(master=self.container_find, text='find text:')
        self.text_find = tkinter.Text(master=self.container_find)

        self.container_replace = tkinter.Frame(master=self.container_current)
        button_replace_copy = s.ReactiveButton(master=self.container_replace, text='copy text'.upper(),
                                               command=self.command_copy_find)
        label_replace = tkinter.Label(master=self.container_replace, text='replace with text:')
        self.text_replace = tkinter.Text(master=self.container_replace)

        containers = [
            self.container_current,
            self.container_settings,
            self.container_modules,
            container_module_buttons,
            self.container_definition,
            self.container_browser,
            self.container_file_content,
            self.container_scope_select,
            self.container_find,
            self.container_replace,
            self.container_command,
            self.container_command_buttons,
        ]
        small_buttons = [
            self.button_menu_back,
        ]
        for button_settings in list_buttons_settings:
            if list_buttons_settings.index(button_settings) < 2:
                continue
            small_buttons.append(button_settings)
        large_buttons = [
            self.button_menu_settings,
            self.button_module_attach,
            self.button_module_retrieve,
            self.button_module_reload,
            self.button_module_browse,
            self.button_module_new,
            self.button_definition_edit,
            button_replace_copy,
            self.button_menu_modules,
            button_scope_select_file,
            self.button_scope_select_folder,
            self.button_scope_except_file,
            button_scope_except_folder,
            self.button_function_find,
            self.button_function_replace,
            self.button_run,
            self.button_execute,
        ]
        labels = [
            label_modules_idle,
            label_modules_active,
            self.label_browser,
            self.label_scope_select,
            label_find,
            label_replace,
            self.label_scope_except
        ]
        for setting_label in list_labels_settings:
            labels.append(setting_label)
        for parameter_label in list_labels_module_editor:
            labels.append(parameter_label)
        texts = [
            self.text_result,
            self.text_find,
            self.text_replace,
            self.text_file_content,
            self.text_scope_select,
            self.text_scope_except
        ]
        for parameter_text in self.list_text_definition_editor:
            texts.append(parameter_text)
        entries = [
        ]
        for setting_entry in self.list_entry_settings:
            entries.append(setting_entry)

        for button in small_buttons:
            button.place_configure(width=UNIT_WIDTH, height=UNIT_HEIGHT)
        for button in large_buttons:
            button.place_configure(width=UNIT_WIDTH * 2, height=UNIT_HEIGHT)
        for label in labels:
            label.place_configure(width=UNIT_WIDTH * 2, height=UNIT_HEIGHT)
        for text in texts:
            text.place_configure(width=TEXT_WIDTH)
        for entry in entries:
            entry.place_configure(width=TEXT_WIDTH)

        try:
            for button in small_buttons:
                button.configure(
                    image=s.BUTTON_SMALL_IDLE, compound='center', foreground=s.TEXT_COLORS[0], font=s.FONT_BUTTON,
                    border=0, background=s.APP_BACKGROUND_COLOR, activebackground=s.APP_BACKGROUND_COLOR)
            for button in large_buttons:
                button.configure(
                    image=s.BUTTON_LARGE_IDLE, compound='center', foreground=s.TEXT_COLORS[0], font=s.FONT_BUTTON,
                    border=0, background=s.APP_BACKGROUND_COLOR, activebackground=s.APP_BACKGROUND_COLOR)
        except _tkinter.TclError:
            for button in small_buttons:
                button.configure(
                    foreground=s.TEXT_COLORS[0], font=s.FONT_BUTTON,
                    border=1, background=s.APP_BACKGROUND_COLOR, activebackground=s.APP_BACKGROUND_COLOR)
            for button in large_buttons:
                button.configure(
                    foreground=s.TEXT_COLORS[0], font=s.FONT_BUTTON,
                    border=1, background=s.APP_BACKGROUND_COLOR, activebackground=s.APP_BACKGROUND_COLOR)

        for container in containers:
            container.configure(background=s.APP_BACKGROUND_COLOR)
        for label in labels:
            label.configure(background=s.APP_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], font=s.FONT_TEXT)
        for text in texts:
            text.configure(
                foreground=s.TEXT_COLORS[0], font=s.FONT_TEXT, selectforeground=s.TEXT_COLORS[-1],
                background=s.ENTRY_BACKGROUND_COLOR, selectbackground=s.TEXT_COLORS[0])
        for entry in entries:
            entry.configure(
                background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], font=s.FONT_TEXT,
                selectbackground=s.TEXT_COLORS[0], selectforeground=s.TEXT_COLORS[-1],
                disabledbackground=s.ENTRY_BACKGROUND_COLOR, disabledforeground=s.TEXT_COLORS[0])
        self.text_result.configure(foreground=s.TEXT_COLORS[1])
        self.listbox_browser.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], font=s.FONT_TEXT,
            selectbackground=s.TEXT_COLORS[0], selectforeground=s.TEXT_COLORS[-1])
        current_style = tkinter.ttk.Style(master=self)
        current_style.theme_use('clam')
        tkinter.ttk.Style().configure(
            '.', width=UNIT_WIDTH * 2, font=s.FONT_TEXT, foreground=s.TEXT_COLORS[0],
            background=s.ENTRY_BACKGROUND_COLOR)
        tkinter.ttk.Style().configure(
            'Treeview', background=s.ENTRY_BACKGROUND_COLOR, fieldbackground=s.ENTRY_BACKGROUND_COLOR, fieldbw=0,
            selectbackground=s.TEXT_COLORS[0], selectforeground=s.TEXT_COLORS[-1])
        tkinter.ttk.Style().configure(
            'Treeview.Heading', borderwidth=0, overbackground=s.TEXT_COLORS[0], overforeground=s.TEXT_COLORS[-1])

        for index in range(len(s.current) - 1):
            list_labels_settings[index].place(x=0, y=UNIT_HEIGHT * index, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT)
            self.list_entry_settings[index].place(x=UNIT_WIDTH * 2 + 10, y=UNIT_HEIGHT * index,
                                                  width=TEXT_WIDTH - UNIT_WIDTH,
                                                  height=UNIT_HEIGHT)
            if index < 2:
                self.list_entry_settings[index].configure(state='disabled')
                continue
            list_buttons_settings[index].place(x=TEXT_WIDTH + UNIT_WIDTH + 10, y=UNIT_HEIGHT * index,
                                               width=UNIT_WIDTH, height=UNIT_HEIGHT)

        for index in range(len(DEFINITION_EXAMPLE) - 2):
            list_labels_module_editor[index].place(x=0, y=UNIT_HEIGHT * index, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT)
            self.list_text_definition_editor[index].place(
                x=UNIT_WIDTH * 2 + 10, y=UNIT_HEIGHT * index, width=TEXT_WIDTH, height=UNIT_HEIGHT)
        self.list_text_definition_editor[-1].place_configure(height=UNIT_HEIGHT * 4)

        self.dict_position = {
            self.container_current: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 13),

            label_modules_idle: dict(x=0, y=int(UNIT_HEIGHT * 2.5), width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            self.treeview_modules_idle: dict(x=UNIT_WIDTH * 2, y=0, width=TEXT_WIDTH, height=UNIT_HEIGHT * 5),
            container_module_buttons: dict(x=UNIT_WIDTH * 0, y=UNIT_HEIGHT * 5 + 5, width=FULL_WIDTH,
                                           height=UNIT_HEIGHT + 10),
            self.button_module_new: dict(x=UNIT_WIDTH * 0, y=0),
            self.button_module_attach: dict(x=UNIT_WIDTH * 2, y=0, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            label_modules_active: dict(x=0, y=int(UNIT_HEIGHT * 9), width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            self.treeview_modules_active: dict(x=UNIT_WIDTH * 2, y=int(UNIT_HEIGHT * 6.5), width=TEXT_WIDTH,
                                               height=UNIT_HEIGHT * 5),

            self.label_browser: dict(x=0, y=0, width=TEXT_WIDTH, height=UNIT_HEIGHT),
            self.listbox_browser: dict(x=UNIT_WIDTH * 1, y=UNIT_HEIGHT, width=TEXT_WIDTH, height=UNIT_HEIGHT * 10),

            self.label_scope_select: dict(x=0, y=0),
            self.text_scope_select: dict(x=UNIT_WIDTH * 2, y=UNIT_HEIGHT * 0, width=TEXT_WIDTH - UNIT_WIDTH * 4,
                                         height=UNIT_HEIGHT),
            button_scope_select_file: dict(x=TEXT_WIDTH - UNIT_WIDTH * 2, y=UNIT_HEIGHT * 0),
            self.button_scope_select_folder: dict(x=TEXT_WIDTH, y=UNIT_HEIGHT * 0),
            self.label_scope_except: dict(x=0, y=UNIT_HEIGHT * 1),
            self.text_scope_except: dict(x=UNIT_WIDTH * 2, y=UNIT_HEIGHT * 1, width=TEXT_WIDTH - UNIT_WIDTH * 4,
                                         height=UNIT_HEIGHT),
            self.button_scope_except_file: dict(x=TEXT_WIDTH - UNIT_WIDTH * 2, y=UNIT_HEIGHT * 1),
            button_scope_except_folder: dict(x=TEXT_WIDTH, y=UNIT_HEIGHT * 1),

            self.text_file_content: dict(x=UNIT_WIDTH * 1, y=0, width=TEXT_WIDTH, height=UNIT_HEIGHT * 12),
            numeration: dict(x=0, y=0, width=UNIT_WIDTH - 1, height=UNIT_HEIGHT * 12),
            label_find: dict(x=0, y=0, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            self.text_find: dict(x=UNIT_WIDTH * 2, y=0, width=TEXT_WIDTH, height=UNIT_HEIGHT),
            button_replace_copy: dict(x=0, y=0),
            label_replace: dict(x=0, y=UNIT_HEIGHT),
            self.text_replace: dict(x=UNIT_WIDTH * 2, y=0, width=TEXT_WIDTH, height=UNIT_HEIGHT * 2),
            # self.container_command:
            self.text_result: dict(x=0, y=0, width=FULL_WIDTH, height=int(UNIT_HEIGHT * 0.75)),
            self.container_command_buttons: dict(x=0, y=UNIT_HEIGHT * 2, anchor='sw', width=FULL_WIDTH,
                                                 height=UNIT_HEIGHT),
            self.button_menu_back: dict(x=0, y=0),
            self.button_menu_modules: dict(x=UNIT_WIDTH * 1, y=0),
            self.button_menu_settings: dict(x=UNIT_WIDTH * 3, y=0),
            self.button_run: dict(x=UNIT_WIDTH * 5, y=0),
            self.button_execute: dict(x=UNIT_WIDTH * 7, y=0),
            # button_function_duplicate: dict(x=UNIT_WIDTH * 9, y=0),
            self.button_function_find: dict(x=UNIT_WIDTH * 11, y=0),
            self.button_function_replace: dict(x=UNIT_WIDTH * 13, y=0),

            # non-default
            self.container_modules: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 13),
            self.button_module_browse: dict(x=UNIT_WIDTH * 8, y=0, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            self.button_definition_edit: dict(x=UNIT_WIDTH * 12, y=0, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            self.button_module_retrieve: dict(x=UNIT_WIDTH * 4, y=0, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),
            self.button_module_reload: dict(x=UNIT_WIDTH * 6, y=0, width=UNIT_WIDTH * 2, height=UNIT_HEIGHT),

            self.container_command: dict(x=0, y=UNIT_HEIGHT * 15, anchor='sw', width=FULL_WIDTH,
                                         height=UNIT_HEIGHT * 2),
            self.container_settings: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 11),
            self.container_definition: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 11),
            self.container_browser: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 12),
            # container_select_file: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 2),
            # container_folder_select: dict(x=0, y=UNIT_HEIGHT * 2, width=FULL_WIDTH, height=UNIT_HEIGHT * 3),
            self.container_scope_select: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 2),
            self.container_file_content: dict(x=0, y=0, width=FULL_WIDTH, height=UNIT_HEIGHT * 13),
            self.container_find: dict(x=0, y=int(UNIT_HEIGHT * 7.5), width=FULL_WIDTH, height=UNIT_HEIGHT * 1),
            self.container_replace: dict(x=0, y=int(UNIT_HEIGHT * 8.5), width=FULL_WIDTH, height=UNIT_HEIGHT * 2),
        }

        self.position(
            self.container_current, self.text_result,
            self.container_command_buttons, self.button_menu_back, self.button_menu_modules, self.button_menu_settings,
            self.button_run,
            self.button_execute, self.button_function_find, self.button_function_replace,
            container_module_buttons, self.button_module_new, self.button_module_attach,
            self.text_file_content, numeration, self.label_browser, self.listbox_browser,
            label_modules_idle, self.treeview_modules_idle, label_modules_active, self.treeview_modules_active,
            self.label_scope_select, button_scope_select_file, self.button_scope_select_folder, self.text_scope_select,
            self.label_scope_except, self.button_scope_except_file, button_scope_except_folder, self.text_scope_except,
            label_find, self.text_find, button_replace_copy, label_replace, self.text_replace,
        )  #

        self.set_window_modules()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        self.mainloop()

    def warning_file_save(self):
        """ Checks if the edited file have been edited since the previous saving and prompts a question if not. """
        file_named = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip('\n\t {}')
        if file_named and self.current_file_content_backup:
            if self.text_file_content.get('1.0', 'end').strip() != self.current_file_content_backup.strip():
                save_file = tkinter.messagebox.askquestion(f'{s.PROGRAM_NAME}:', 'Do you want to save the file?')
                if save_file == 'yes':
                    self.command_file_save()
        self.current_file_content_backup = ''

    def on_app_close(self):
        """ Triggered on closing the application to catch unsaved changes in files. """
        self.set_log_update('closing application')
        self.warning_file_save()
        self.quit()

    def clear_window(self):
        """ Cleans the screen of all containers. """
        if self.current_window == 'file_editor':
            self.warning_file_save()
        self.current_window = ''
        self.retrieve(self.container_browser, self.container_modules, self.container_definition,
                      self.container_find, self.container_replace,
                      self.container_scope_select, self.container_file_content, self.container_settings)

    def set_window_find(self):
        """ Loads the screen for finding text. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.container_current.place_configure(height=UNIT_HEIGHT * 10)
        self.text_file_content.place_configure(height=UNIT_HEIGHT * 5)
        self.container_command.place_configure(height=UNIT_HEIGHT * 5)
        self.container_command_buttons.place_configure(y=UNIT_HEIGHT * 5)
        self.text_result.place_configure(height=UNIT_HEIGHT * 4)
        self.position(self.container_file_content, self.container_scope_select, self.container_find,
                      self.button_function_replace,
                      self.button_scope_select_folder, self.button_scope_except_file)
        self.container_file_content.place_configure(height=UNIT_HEIGHT * 5)
        self.container_scope_select.place_configure(y=int(UNIT_HEIGHT * 5.5))
        self.button_menu_back.config(command=self.set_window_file)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.retrieve(self.button_menu_settings, self.button_function_find)
        try:
            selection = reformat_string(self.text_file_content.selection_get(), direction='display')
            self.text_find.delete('1.0', 'end')
            self.text_find.insert('1.0', selection)
        except UnboundLocalError:
            print('set_window_find error: UnboundLocalError')
        except _tkinter.TclError:
            print('set_window_find warning: no text selected')
        self.button_run.configure(text='find text'.upper(), command=self.command_run_find)
        self.button_execute.configure(text='clear logs'.upper(), command=self.set_log_update)
        self.text_result.focus()
        self.current_window = 'self.text_find'
        self.set_log_update('find feature loaded')
        self.command_run_find()

    def set_window_replace(self):
        """ Loads the screen for replacing text. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.text_file_content.place_configure(height=UNIT_HEIGHT * 5)
        self.container_current.place_configure(height=UNIT_HEIGHT * 11)
        self.container_command.place_configure(height=UNIT_HEIGHT * 4)
        self.container_command_buttons.place_configure(y=UNIT_HEIGHT * 4)
        self.text_result.place_configure(height=UNIT_HEIGHT * 3)
        self.position(self.container_file_content, self.container_scope_select, self.container_find,
                      self.container_replace,
                      self.button_function_find, self.button_scope_select_folder, self.button_scope_except_file)
        self.container_file_content.place_configure(height=UNIT_HEIGHT * 5)
        self.container_scope_select.place_configure(y=int(UNIT_HEIGHT * 5.5))
        self.retrieve(self.button_menu_settings, self.button_function_replace)
        try:
            selection = reformat_string(self.text_file_content.selection_get(), direction='display')
            self.text_find.delete('1.0', 'end')
            self.text_find.insert('1.0', selection)
        except UnboundLocalError:
            print('set_window_find error: UnboundLocalError')
        except _tkinter.TclError:
            print('set_window_find warning: no text selected')
        self.button_menu_back.config(command=self.set_window_file)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.button_run.configure(text='replace text'.upper(), command=self.command_run_replace)
        self.button_run.focus()
        self.button_execute.configure(text='clear logs'.upper(), command=self.set_log_update)
        self.current_window = 'self.text_replace'
        self.set_log_update('replace feature loaded')

    def set_window_move(self):
        """ Loads the screen for moving files. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.container_current.place_configure(height=UNIT_HEIGHT * 5)
        self.container_command.place_configure(height=UNIT_HEIGHT * 10)
        self.container_command_buttons.place_configure(y=UNIT_HEIGHT * 10)
        self.text_result.place_configure(height=UNIT_HEIGHT * 9)
        self.position(self.container_scope_select)  # , container_folder_select
        try:
            self.current_path = f"{self.label_browser.cget('text')}/{self.listbox_browser.selection_get()}".replace(
                '\\', '/')
        except _tkinter.TclError:
            print('file not selected')
        self.button_menu_back.configure(command=self.command_browser_back)
        self.label_scope_select.configure(text='file')
        self.text_scope_select.delete('1.0', 'end')
        try:
            self.text_scope_select.insert('1.0',
                                          f"{self.label_browser.cget('text')}/{self.listbox_browser.selection_get()}")
        except _tkinter.TclError:
            self.text_scope_select.insert('end', self.current_path)
        self.label_scope_except.configure(text='to folder')
        self.retrieve(self.button_scope_select_folder, self.button_scope_except_file)
        self.button_run.configure(text='move the file'.upper(), command=self.command_run_move)
        self.button_run.focus()
        self.button_execute.configure(text='clear logs'.upper(), command=self.set_log_update)
        self.current_window = 'file_move'
        self.set_log_update(f'move feature loaded. file: {self.current_path}')

    def set_window_file(self):
        """ Loads the screen for file edition """
        if self.command_file_load():
            self.clear_window()
            self.key_to_command_current = self.key_to_command_text.copy()
            self.container_current.place_configure(height=UNIT_HEIGHT * 13)
            self.text_file_content.place_configure(height=UNIT_HEIGHT * 12)
            self.container_command.place_configure(height=UNIT_HEIGHT * 2)
            self.container_command_buttons.place_configure(y=UNIT_HEIGHT * 2)
            self.text_result.place_configure(height=int(UNIT_HEIGHT * 0.75))
            self.position(self.container_file_content, self.button_run, self.button_function_find,
                          self.button_function_replace)
            self.retrieve(self.button_execute)
            self.text_file_content.focus()
            self.button_menu_back.configure(command=self.command_browser_back)
            self.button_run.configure(text='save file'.upper(), command=self.command_file_save, state='normal')
            self.current_window = 'file_editor'
            self.set_log_update(f'file editor loaded. file {self.current_path}')
            return True
        else:
            return False

    def set_window_modules(self):
        """ Loads the screen for managing modules. """
        self.key_to_command_current = self.key_to_command_module.copy()
        self.clear_window()
        self.container_current.place_configure(height=UNIT_HEIGHT * 13)
        self.position(self.container_modules, self.button_module_new, self.container_command, self.button_run,
                      self.button_execute,
                      self.button_menu_settings, self.container_command_buttons, self.text_result)
        self.button_run.configure(text='take snapshot'.upper(), command=self.command_snapshot_take)
        self.button_execute.configure(text='compare snapshots'.upper(), command=self.command_snapshot_compare)
        self.button_menu_settings.configure(text='edit settings'.upper(), command=self.set_window_settings)
        self.button_menu_modules.configure(text='refresh modules'.upper())
        self.retrieve(self.button_module_copy, self.button_definition_edit, self.button_function_find,
                      self.button_function_replace,
                      self.button_menu_back)
        self.refresh_definitions()
        self.treeview_modules_idle.focus_set()
        try:
            self.treeview_modules_idle.selection_set(self.treeview_modules_idle.get_children()[0])
            self.treeview_modules_idle.focus(self.treeview_modules_idle.get_children()[0])
        except IndexError:
            pass
        self.current_window = 'modules'
        self.set_log_update('module manager window loaded.')

    def set_window_definition(self):
        """ Loads the screen for modification of module definitions. """
        if not self.global_modules:
            self.global_modules = modules_filter(return_type='definitions')
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.position(self.container_definition, self.button_menu_back)
        self.retrieve(self.button_menu_settings, self.button_menu_back, self.button_execute)
        self.button_menu_back.configure(command=self.set_window_modules)
        self.button_run.configure(text='save parameters'.upper(), command=self.command_definition_save)
        self.button_menu_modules.configure(text='return to modules'.upper())
        module_selected = self.current_path.split('/')[-1]
        for module in self.global_modules:
            if module_selected == module['name']:
                level = 0
                for param in DEFINITION_EXAMPLE:
                    if param == 'comment':
                        continue
                    elif param == 'changes':
                        # TODO later: reformat the changes into a listbox
                        continue
                    self.list_text_definition_editor[level].configure(state='normal')
                    self.list_text_definition_editor[level].delete('1.0', 'end')
                    if isinstance(module[param], bool):
                        self.list_text_definition_editor[level].insert('end', str(module[param]))
                    else:
                        self.list_text_definition_editor[level].insert('end', module[param])
                    if 'active' in param or param == 'path':  # or param == 'class':
                        self.list_text_definition_editor[level].configure(state='disabled')
                    level += 1
        self.set_log_update('module definition edition feature loaded.')
        self.current_window = 'definition'

    def set_window_browser(self):
        """ Loads the screen for browsing in modules directories. """
        self.key_to_command_current = self.key_to_command_browser.copy()
        self.clear_window()
        self.container_current.place_configure(height=UNIT_HEIGHT * 13)
        self.container_command.place_configure(height=UNIT_HEIGHT * 2)
        self.container_command_buttons.place_configure(y=UNIT_HEIGHT * 2)
        self.text_result.place_configure(height=int(UNIT_HEIGHT * 0.75))
        self.position(self.container_browser)
        self.retrieve(self.button_module_new, self.button_function_find, self.button_function_replace,
                      self.button_menu_settings)
        self.button_run.configure(text='open'.upper(), command=self.command_browser_forward)
        self.button_execute.configure(text='move file'.upper(), command=self.set_window_move)
        self.open_browser_item()
        self.button_menu_back.config(command=self.command_browser_back)
        self.listbox_browser.focus()
        self.current_window = 'browser'
        self.set_log_update(f'File browser loaded. Path: {os.path.abspath(self.current_path)}')

    def set_window_settings(self):
        """ Loads the screen for settings edition. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.position(self.container_settings, self.text_result)
        self.command_settings_reload()
        self.button_menu_settings.configure(text='save settings'.upper(), command=self.command_settings_save)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.retrieve(self.button_run, self.button_execute, self.button_function_find, self.button_function_replace)
        self.current_window = 'settings'
        self.set_log_update('settings edition feature loaded')

    def command_snapshot_take(self):
        """ Takes a snapshot of all files in the selected directory. """
        self.set_log_update('generating snapshot - please wait')
        try:
            result_path = snapshot_take()
        except s.InternalError:
            self.set_log_update(f'snapshot not generated. path not selected')
        else:
            self.set_log_update(f'snapshot generated. path: {result_path}')

    def command_snapshot_compare(self):
        """ Runs a comparison between selected snapshots. """
        self.set_log_update('generating snapshot comparison - please wait')
        try:
            result_path = snapshot_compare(return_type='path')
        except s.InternalError:
            self.set_log_update(f'snapshot comparison not generated. Snapshots not selected.')
        else:
            self.set_log_update(f'snapshot comparison generated. path: {result_path}')

    def command_settings_save(self):
        """ Reads the values inserted in the settings text fields and saves them to the SETTINGS_FILE. """
        counter = 0
        setting_value = []
        new_settings = {}
        for entry_setting in self.list_entry_settings:
            setting_value.append(entry_setting.get())
        for setting_key in s.current:
            if setting_key == 'comment':
                continue
            if s.current[setting_key] != setting_value[counter]:
                # TODO later: check for empty settings list
                if isinstance(s.current[setting_key], list):
                    setting_dict_list = setting_value[counter].split(', ')
                    if s.current[setting_key] and setting_dict_list:
                        if s.current[setting_key] != setting_dict_list:
                            new_settings[setting_key] = setting_dict_list
                    elif setting_dict_list != ['']:
                        new_settings[setting_key] = setting_dict_list
                    else:
                        pass
                elif isinstance(s.current[setting_key], str):
                    new_settings[setting_key] = setting_value[counter]
            counter += 1
        if new_settings:
            try:
                output = s.settings_set(new_settings)
                self.set_log_update(output)
            except s.InternalError as error:
                self.set_log_update(error.message)
                self.command_settings_reload()

    def command_settings_reload(self):
        """ Reads the settings from the SETTINGS_FILE and inserts them into the settings text fields. """
        counter = 0
        for setting_key in s.current:
            if setting_key == 'comment':
                continue
            self.list_entry_settings[counter].delete('0', 'end')
            if isinstance(s.current[setting_key], list):
                self.list_entry_settings[counter].insert('end', ', '.join(s.current[setting_key]))
            else:
                self.list_entry_settings[counter].insert('end', s.current[setting_key])
            counter += 1

    def command_select_folder(self, text_widget):
        """ Launches a window for selecting a folder and pastes it into the folder text field. """
        selected_folder = askdirectory(
            title=f'{s.PROGRAM_NAME}: select a folder',
            initialdir=self.current_path if os.path.isdir(self.current_path) else self.current_path[
                                                                                  :self.current_path.rfind('/')])
        if len(text_widget.get('1.0', 'end')) > 1:
            text_widget.insert('end', f', {selected_folder}')
        else:
            text_widget.insert('end', selected_folder)
        self.set_log_update(f'folder {selected_folder} selected')

    def command_select_file(self, text_widget):
        """ Launches a window for selecting one or more file(s) and pastes it into the file text field. """
        selected_files = askopenfilenames(
            title=f'{s.PROGRAM_NAME}: select one or multiple files',
            initialdir=self.current_path if os.path.isdir(self.current_path) else self.current_path[
                                                                                  :self.current_path.rfind('/')])
        if selected_files:
            strip_chars = "(),'"
            if len(text_widget.get('1.0', 'end')) > 1:
                text_widget.insert('end', f', {str(selected_files).strip(strip_chars)}')
            else:
                text_widget.insert('end', f"{str(selected_files).strip(strip_chars)}")
        self.set_log_update(f'file(s) {selected_files} selected')

    def set_text_color(self, event=None):
        """ Provides colors to elements of an edited text file that are defined as its delimiters. """
        if event:
            pass
        for tag_name in self.text_file_content.tag_names():
            self.text_file_content.tag_delete(tag_name)
        text_lines = self.text_file_content.get('1.0', 'end').split('\n')
        for line_index in range(1, len(text_lines) + 1):
            line = text_lines[line_index - 1]
            rest_of_line = line
            if line.strip() == '':
                continue
            elif line.strip()[0] in s.INI_COMMENTS:
                self.text_file_content.tag_add('comment', f'{line_index}.0', f'{line_index}.end')
                rest_of_line = ''
            elif s.INI_COMMENTS[0] in line:
                self.text_file_content.tag_add('comment', f'{line_index}.{line.index(s.INI_COMMENTS[0])}',
                                               f'{line_index}.end')
                rest_of_line = line[:line.index(s.INI_COMMENTS[0])]
            elif s.INI_COMMENTS[1] * 2 in line:
                self.text_file_content.tag_add('comment', f'{line_index}.{line.index(s.INI_COMMENTS[1] * 2)}',
                                               f'{line_index}.end')
                rest_of_line = line[:line.index(s.INI_COMMENTS[1] * 2)]
            self.text_file_content.tag_config('comment', foreground='grey')
            if rest_of_line:
                level = rest_of_line.rstrip().count(s.LEVEL_INDENT)
                self.text_file_content.tag_config(f'level{level}', foreground=s.INI_LEVEL_COLORS[level])
                if rest_of_line.split()[0].strip() in self.current_levels[level]:
                    self.text_file_content.tag_add(f'level{level}', f'{line_index}.0',
                                                   f'{line_index}.{len(rest_of_line)}')
                elif rest_of_line.strip() in s.INI_ENDS:
                    self.text_file_content.tag_add(f'level{level}', f'{line_index}.0',
                                                   f'{line_index}.{len(rest_of_line)}')

    def command_text_comment(self):
        """ Comments the text selected in the text editor """
        text_to_comment = ''
        try:
            text_to_comment += self.text_file_content.get('insert linestart', 'sel.last lineend')
        except _tkinter.TclError:
            text_to_comment += self.text_file_content.get('insert linestart', 'insert lineend')
            self.text_file_content.tag_add('sel', 'insert linestart', 'insert lineend')
        lines_to_comment = text_to_comment.split('\n')
        text_commented = ''
        for line in lines_to_comment:
            for level in range(7):
                if line.startswith(s.LEVEL_INDENT * (6 - level)):
                    text_commented += f'{s.LEVEL_INDENT * (6 - level)}; {line.strip()}\n'
                    break
        if text_commented:
            self.text_file_content.replace('sel.first linestart', 'sel.last lineend + 1 chars', text_commented)
        self.set_text_color()
        self.set_log_update('selected text has been commented out')

    def command_text_uncomment(self):
        """ Uncomments the text selected in the text editor """
        text_to_comment = ''
        try:
            text_to_comment += self.text_file_content.get('insert linestart', 'sel.last lineend')
        except _tkinter.TclError:
            self.text_file_content.tag_add('sel', 'insert linestart', 'insert lineend')
            text_to_comment += self.text_file_content.get('insert linestart', 'insert lineend')
        lines_to_comment = text_to_comment.split('\n')
        text_commented = ''
        for line in lines_to_comment:
            for level in range(7):
                if line.startswith(s.LEVEL_INDENT * (6 - level)):
                    if '; ' in line:
                        text_commented += f"{s.LEVEL_INDENT * (6 - level)}{line.strip()[len('; '):]}\n"
                    elif '//' in line:
                        text_commented += f"{s.LEVEL_INDENT * (6 - level)}{line.strip()[len('//'):]}\n"
                    break
        if text_commented:
            self.text_file_content.replace('sel.first linestart', 'sel.last lineend + 1 chars', text_commented)
        self.set_text_color()
        self.set_log_update('selected text has been uncommented')

    def command_file_load(self):  # not a command anymore
        """
        Loads the selected file into the text editor and into a variable.
        :return: True if the file is readable | False if the file could not be read
        """
        self.text_file_content.delete('1.0', 'end')
        file_loaded = self.text_scope_select.get('1.0', 'end').replace('\\', '/').strip('\n\t {}')
        self.current_path = file_loaded
        try:
            self.current_file_content_backup, self.current_levels = load_file(full_path=file_loaded)
            self.text_file_content.insert('end', self.current_file_content_backup)
            self.set_text_color()
            self.set_log_update(f'file {file_loaded} loaded successfully')
            return True
        except TypeError:
            self.command_browser_back()
            self.set_log_update('cannot open this type of file')
        except s.InternalError as error:
            self.command_browser_back()
            self.set_log_update(error.message)
        return False

    def command_file_save(self):
        """ Saves the text edited in the application back into its original file. """
        content_to_save = self.text_file_content.get('1.0', 'end')
        file_named = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip().replace('{', '').replace('}',
                                                                                                                  '')
        with open(file_named, 'w') as file_overwritten:
            file_overwritten.write(content_to_save)
        self.set_log_update(f'file {file_named} saved')

    def command_copy_find(self):
        """ Copies the string to find into the field of the string to replace it with. """
        find = self.text_find.get('1.0', 'end').strip()
        self.text_replace.delete('1.0', 'end')
        self.text_replace.insert('1.0', find)

    def command_run_find(self):
        """ Runs the find_text function. """
        find = reformat_string(self.text_find.get('1.0', 'end').strip(), direction='display')
        scope = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip()
        exception_string = self.text_scope_except.get('1.0', 'end').replace('/', '\\').strip()
        exceptions = exception_string.split(', ')
        if find and scope:
            output = text_find_replace(find=find, scope=scope, exceptions=exceptions, mode='initiate')
            self.set_log_update(output)

    def command_run_replace(self):
        """ Runs the replace_text function. """
        find = reformat_string(self.text_find.get('1.0', 'end').strip(), direction='display')
        replace_with = reformat_string(self.text_replace.get('1.0', 'end').strip(), direction='display')
        scope = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip()
        exception_string = self.text_scope_except.get('1.0', 'end').replace('/', '\\').strip()
        exceptions = exception_string.split(', ')
        output = text_find_replace(find=find, replace_with=replace_with, scope=scope, exceptions=exceptions)
        self.set_log_update(output)
        self.text_file_content.delete('1.0', 'end')
        self.text_file_content.insert('end', load_file(scope)[0])
        self.set_text_color()

    def command_run_move(self):
        """ Runs the move_file function. """
        files_named = self.text_scope_select.get('1.0', 'end').replace('\\', '/').strip()
        to_folder = self.text_scope_except.get('1.0', 'end').replace('\\', '/').strip()
        output = ''
        for file_named in files_named.split('} {'):
            file_named = file_named.replace('{', '').replace('}', '')
            try:
                output += move_file(file_named, to_folder)
            except s.InternalError as error:
                output += error.message
            else:
                module_index_start = self.current_path.find(s.LIBRARY) + len(s.LIBRARY) + 1
                module_index_end = self.current_path.replace('\\', '/').find('/', module_index_start)
                current_module_name = self.current_path[module_index_start: module_index_end]
                current_module_list = modules_filter(name=current_module_name)
                if current_module_list:
                    current_module = current_module_list[0]
                else:
                    module_index_start = self.current_path.find(s.MAIN_DIRECTORY) + len(s.MAIN_DIRECTORY) + 1
                    module_index_end = self.current_path.replace('\\', '/').find('/', module_index_start)
                    current_module_name = self.current_path[module_index_start: module_index_end]
                    current_module_list = modules_filter(name=current_module_name)
                    if current_module_list:
                        current_module = current_module_list[0]
                    else:
                        output += '\nmodule not found - definition not updated.\n'
                        return self.set_log_update(output)
                new_changes = {}
                for file_path in current_module['changes']:
                    file_name = file_named.replace('\\', '/').split('/')[-1]
                    if file_path.split('/')[-1] == file_name:
                        file_rel_path = '..' + to_folder[module_index_end + 1:].replace('\\', '/')
                        new_changes[f'{file_rel_path}/{file_name}'] = current_module['changes'][file_path]
                    else:
                        new_changes[file_path] = current_module['changes'][file_path]
                definition_edit(current_module, changes=new_changes)
        self.set_log_update(output)

    def command_run_duplicate(self):
        """ Runs the duplicates_commenter function. """
        file_named = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip()
        output = duplicates_find(of_object_or_file=file_named)
        self.set_log_update(output)

    def command_definition_save(self):
        """ Saves the current module definition. """
        output = 'module data edition failed'
        module_selected = self.current_path.split('/')[-1]
        for module in self.global_modules:
            if module_selected == module['name']:
                edited_parameters = {}
                expected_definition = module.copy()
                level = 0
                for param in DEFINITION_EXAMPLE:
                    if param == 'comment':
                        continue
                    elif param == 'changes':
                        # TODO later: reformat the changes
                        continue
                    value = self.list_text_definition_editor[level].get('1.0', 'end').strip()
                    if value != module[param]:
                        if param == 'class' and value not in DEFINITION_CLASSES:
                            break
                        elif param != 'active':
                            edited_parameters[param] = value
                            expected_definition[param] = value
                    level += 1
                try:
                    new_definition = definition_edit(module, **edited_parameters)
                    if new_definition == expected_definition:
                        output = 'new definition saved'
                    if 'class' in edited_parameters and module['active'] is True:
                        module.reload_after_class_change()
                    break
                except s.InternalError as error:
                    output = error.message
        self.set_log_update(output)

    def on_select_module_idle(self, event):
        """ Triggered on selection of a non-active module, shows or hides the desired buttons"""
        if event:
            pass
        try:
            self.current_path = (
                f"{s.LIBRARY}/"
                f"{self.treeview_modules_idle.item(self.treeview_modules_idle.selection()[0], 'values')[0]}")
            self.treeview_modules_active.selection_remove(self.treeview_modules_active.selection()[0])
            # # # selection_remove is a selection event steeling focus to the other list
            self.treeview_modules_idle.selection_set(self.treeview_modules_idle.selection()[0])
        except IndexError:
            pass
        self.key_to_command_current['<Return>'] = self.command_module_browse
        self.position(self.button_module_attach, self.button_module_browse, self.button_definition_edit)
        self.retrieve(self.button_module_retrieve, self.button_module_reload)
        self.treeview_modules_idle.focus()

    def on_select_module_active(self, event):
        """ Triggered on selection of an active module, shows or hides the desired buttons. """
        if event:
            pass
        try:
            self.current_path = (
                f"{s.LIBRARY}/"
                f"{self.treeview_modules_active.item(self.treeview_modules_active.selection()[0], 'values')[0]}")
            self.treeview_modules_idle.selection_remove(self.treeview_modules_idle.selection()[0])
            self.treeview_modules_active.selection_set(self.treeview_modules_active.selection()[0])
        except IndexError:
            pass
        self.key_to_command_current['<Return>'] = self.command_module_browse
        self.position(self.button_module_retrieve, self.button_module_reload, self.button_module_browse,
                      self.button_definition_edit)
        self.retrieve(self.button_module_attach)

    def refresh_definitions(self):
        """ Refreshes the lists of active and non-active modules. """
        try:
            self.set_log_update(detect_new_modules())
            self.treeview_modules_active.delete(*self.treeview_modules_active.get_children())
            self.treeview_modules_idle.delete(*self.treeview_modules_idle.get_children())
            active_modules = modules_filter('definitions', active=True)
            active_module_parent_dict = modules_sort(modules=active_modules)
            for module in active_modules:
                self.treeview_modules_active.insert(
                    parent='', index=active_modules.index(module), iid=active_modules.index(module),
                    values=tuple(module[_] for _ in MODULE_COLUMNS)
                )
                self.global_modules.append(module)
            for module in active_modules:
                try:
                    parent_index = active_module_parent_dict[module['name']]
                    self.treeview_modules_active.move(active_modules.index(module), parent_index, 0)
                except KeyError:
                    pass
            self.treeview_modules_active.open_children()
            idle_modules = modules_filter('definitions', active=False)
            idle_module_parent_dict = modules_sort(modules=idle_modules)
            for module in idle_modules:
                self.treeview_modules_idle.insert(
                    parent='', index=idle_modules.index(module), iid=idle_modules.index(module),
                    values=tuple(module[_] for _ in MODULE_COLUMNS)
                )
                self.global_modules.append(module)
            for module in idle_modules:
                try:
                    parent_index = idle_module_parent_dict[module['name']]
                    self.treeview_modules_idle.move(idle_modules.index(module), parent_index, 0)
                except KeyError:
                    pass
            self.treeview_modules_idle.open_children()
        except s.InternalError:
            self.set_log_update('definitions not loaded - settings not loaded.')
            return
        self.retrieve(self.button_module_retrieve, self.button_module_attach)

    def command_module_new(self):
        """ Creates a new module after asking for a name and a way to create it. """
        global new_module_name
        NewModuleDialog()
        if new_module_name:
            self.set_log_update(f'command_module_new: creating module {new_module_name}. Please wait ...')
            self.set_log_update(module_copy(new_module_name, changes_source=new_module_source))
            self.refresh_definitions()
        else:
            self.set_log_update('command_module_new error: a correct unique name was not provided')
        new_module_name = ''

    def command_module_copy(self):
        """ Copies the selected module. Currently, not in use """
        module_selected = self.current_path
        name = module_selected.split('/')[-1] + '_copy'
        self.set_log_update(module_copy(name, module_selected))
        self.refresh_definitions()

    def command_module_attach(self):
        # TODO: if the module overrides another, ask if save it as ancestor / heir
        """ Activates the selected module """
        if not self.global_modules:
            self.global_modules = modules_filter(return_type='definitions')
        try:
            module_selected = self.treeview_modules_idle.item(self.treeview_modules_idle.focus(), 'values')[0]
            self.set_log_update(f'loading module {module_selected} ...')
            for module in self.global_modules:
                if module['name'] == module_selected:
                    module.attach()
                    self.set_log_update(f'module {module_selected} loaded')
                    return self.refresh_definitions()
            self.set_log_update(f'command_module_attach error: module {module_selected} not found')
        except _tkinter.TclError:
            self.set_log_update('command_module_attach warning: TclError')
        except s.InternalError as err:
            self.set_log_update(err.message)

    def command_module_retrieve(self):
        """ Deactivates the selected module. """
        if not self.global_modules:
            self.global_modules = modules_filter(return_type='definitions')
        try:
            module_selected = self.treeview_modules_active.item(self.treeview_modules_active.focus(), 'values')[0]
            self.set_log_update(f'unloading mod {module_selected} ...')
            for module in self.global_modules:
                if module['name'] == module_selected:
                    changes = module_detect_changes(module=module)
                    # TODO: test changes
                    if changes:
                        do_proceed = tkinter.messagebox.askokcancel(
                            title=f'{s.PROGRAM_NAME}: module retrieval:',
                            message='Files have been changed since the module have been attached.\n'
                                    f'They will be deleted if the module is a {DEFINITION_CLASSES[1]}'
                                    f' or incorporated if it is a {DEFINITION_CLASSES[0]}'
                                    ' Do you wish to proceed?\n'
                                    f'{changes}'
                        )
                        if do_proceed is True:
                            changes = ''
                    if not changes:
                        module.retrieve()
                        self.refresh_definitions()
                        self.set_log_update(f"module {module['name']} deactivated")
                        return
                    else:
                        self.set_log_update(
                            f'command_module_retrieve error: module {module_selected} retrieval aborted')
            self.set_log_update(f'command_module_retrieve error: module {module_selected} not found')
        except _tkinter.TclError:
            self.set_log_update('command_module_retrieve error: module not selected')
        except s.InternalError as err:
            self.set_log_update(err.message)

    def command_module_reload(self):
        """ Reloads the selected module by detaching it and attaching again. """
        if not self.global_modules:
            self.global_modules = modules_filter(return_type='definitions')
        try:
            module_selected = self.treeview_modules_active.item(self.treeview_modules_active.focus(), 'values')[0]
            self.set_log_update(f'Reloading module {module_selected}. Please wait ...')
            for module in self.global_modules:
                if module['name'] == module_selected:
                    if module.reload():
                        self.refresh_definitions()
                        self.set_log_update(f'Module {module_selected} reloaded. Please wait ...')
                        return
                    else:
                        self.set_log_update(f'The module could not be reloaded.')
            self.set_log_update(f'command_module_reload error: mod {module_selected} not found')
        except _tkinter.TclError:
            self.set_log_update('command_module_reload error: no mod selected')

    def command_module_browse(self, event=None):
        """ Allows to start browsing from the object folder if it can be found. """
        if event:
            pass
        current_module = modules_filter(name=self.current_path.split('/')[-1])[0]
        game_paths = s.current[s.KEY_GAMES]
        if current_module['class'] == DEFINITION_CLASSES[0] and current_module['active']:
            if not current_module['game']:
                for change_key in current_module['changes']:
                    change_split = change_key.split('/')
                    if os.path.isdir('/'.join(change_split[:2])) and '/'.join(change_split[1:-1]) in game_paths:
                        self.current_path = '/'.join((change_split[0], game_paths[game_paths.index(change_split[1])]))
                        if os.path.isdir(f'{self.current_path}/data/ini/object'):
                            self.current_path = f'{self.current_path}/data/ini/object'
                        break
            elif current_module['game'] in game_paths:
                if os.path.isdir(f"../{game_paths[game_paths.index(current_module['game'])]}"):
                    self.current_path = f"../{game_paths[game_paths.index(current_module['game'])]}"
            elif f"{current_module['game']}/aotr" in game_paths:
                if os.path.isdir(f"../{current_module['game']}/aotr/data/ini/object"):
                    self.current_path = f"../{current_module['game']}/aotr/data/ini/object"
                elif os.path.isdir(f"../{current_module['game']}/aotr"):
                    self.current_path = f"../{current_module['game']}/aotr"
        else:
            for game_name in game_paths:
                if os.path.isdir(f'{self.current_path}/{game_name}/data/ini/object'):
                    self.current_path = f'{self.current_path}/{game_name}/data/ini/object'
                    break
                elif os.path.isdir(f'{self.current_path}/{game_name}'):
                    self.current_path = f'{self.current_path}/{game_name}'
                    break
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.set_window_browser()

    def command_browser_back(self):
        """ Browses back a level in the directory hierarchy or returns to browser from file screen. """
        if self.current_window == 'self.text_find' or self.current_window == 'self.text_replace':
            self.set_window_file()
        if os.path.isdir(self.current_path[:self.current_path.rfind('/')]):
            self.current_path = self.current_path[:self.current_path.rfind('/')]
            if self.focus_get() == self.listbox_browser:
                self.open_browser_item()
            else:
                self.set_window_browser()
        if len(self.current_path) <= len('..'):
            self.retrieve(self.button_menu_back)
            self.key_to_command_current['<BackSpace>'] = self.set_window_modules
        self.set_log_update(f'going back to {os.path.abspath(self.current_path)}')
        self.key_to_command_current = self.key_to_command_browser.copy()

    def on_select_browser_item(self, event=None):
        """ Triggered on selection of an item in the directory to enable or disable buttons. """
        if event:
            pass
        if self.current_window != 'file_editor':
            try:
                file_name = self.listbox_browser.selection_get()
                if file_name == DEFINITION_NAME or file_name.endswith('.big'):
                    raise s.InternalError
                elif os.path.isfile(f'{self.current_path}/{self.listbox_browser.selection_get()}'):
                    self.key_to_command_current = self.key_to_command_browser.copy()
                    self.button_run.configure(text='open file'.upper())
                    self.position(self.button_run, self.button_execute)  # , button_function_duplicate
                else:
                    raise IndexError
            except IndexError:
                self.position(self.button_run)
                self.button_run.configure(text='open folder'.upper())
                self.retrieve(self.button_execute)
            except s.InternalError:
                self.retrieve(self.button_run, self.button_execute)
                try:
                    self.key_to_command_current.pop('<Return>')
                except KeyError:
                    pass

    def command_browser_forward(self, event=None):
        """ Gets the selected item in the directory and opens it """
        if event:
            pass
        try:
            item_selected = self.listbox_browser.get(self.listbox_browser.curselection())
            self.current_path += f'/{item_selected}'
            if os.path.isdir(self.current_path):
                os.listdir(self.current_path)
            self.set_log_update(f'going to {os.path.abspath(self.current_path)}')
            self.open_browser_item()
        except _tkinter.TclError:
            print('command_browser_forward error: _tkinter.TclError - no selection')
        except PermissionError as error:
            self.set_log_update(error.strerror)
            self.current_path = self.current_path[:self.current_path.rfind('/')]

    def open_browser_item(self):
        """ Opens the selected item in the directory whether it is a folder or a file. """
        if os.path.isdir(self.current_path):
            try:
                output_folders, output_files = load_directories(self.current_path)
                self.listbox_browser.delete(0, 'end')
                item_index = 0
                for output_folder in output_folders:
                    self.listbox_browser.insert(item_index, output_folder)
                    self.listbox_browser.itemconfig(item_index, foreground=s.INI_LEVEL_COLORS[1])
                    item_index += 1
                for output_file in output_files:
                    self.listbox_browser.insert(item_index, output_file)
                    self.listbox_browser.itemconfig(
                        item_index,
                        foreground=s.INI_LEVEL_COLORS[3] if output_file.endswith('.ini') else s.INI_LEVEL_COLORS[2]
                    )
                    item_index += 1
                self.listbox_browser.activate(0)
                if not output_folders and not output_files:
                    self.retrieve(self.button_run, self.button_execute)
                elif not output_folders:
                    self.button_run.configure(text='open file'.upper())
                    self.position(self.button_execute)
                else:
                    self.button_run.configure(text='open folder'.upper())
                    self.retrieve(self.button_execute)
                self.listbox_browser.select_set(0)
                self.set_log_update(f'opened {os.path.abspath(self.current_path)}')
            except s.InternalError as error:
                self.set_log_update(error.message)
        elif os.path.isfile(self.current_path):
            self.text_scope_select.delete('1.0', 'end')
            self.text_scope_select.insert('end', self.current_path)
            if self.set_window_file():
                self.listbox_browser.selection_clear(self.listbox_browser.curselection())
                self.position(self.button_execute)
                self.set_log_update(f'opened {os.path.abspath(self.current_path)}')
        self.label_browser.configure(text=os.path.abspath(self.current_path))
        self.position(self.button_menu_back)

    def focus_on_next_item(self):
        """ Binds arrow pressing with the change between the lists of active and non-active modules. """
        if self.focus_get() == self.treeview_modules_idle:
            self.treeview_modules_idle.selection_remove(self.treeview_modules_idle.selection())
            self.treeview_modules_active.focus_set()
            if self.treeview_modules_active.focus():
                module_selected = self.treeview_modules_active.focus()
            elif self.treeview_modules_active.selection():
                module_selected = self.treeview_modules_active.selection()
            elif len(self.treeview_modules_active.get_children()) > 0:
                module_selected = self.treeview_modules_active.get_children()[0]
            else:
                return
            self.treeview_modules_active.selection_set(module_selected)
        elif self.focus_get() == self.treeview_modules_active:
            self.treeview_modules_active.selection_remove(self.treeview_modules_active.selection())
            self.treeview_modules_idle.focus_set()
            self.treeview_modules_idle.selection_set(self.treeview_modules_idle.focus())
            if self.treeview_modules_idle.focus():
                module_selected = self.treeview_modules_idle.focus()
            elif self.treeview_modules_idle.selection():
                module_selected = self.treeview_modules_idle.selection()
            elif self.treeview_modules_idle.get_children():
                module_selected = self.treeview_modules_idle.get_children()[0]
            else:
                return
            self.treeview_modules_idle.selection_set(module_selected)
        elif self.focus_get() == self.listbox_browser:
            list_length = len(self.listbox_browser.get('0', 'end'))
            selected_item_index = self.listbox_browser.get('0', 'end').index(self.listbox_browser.selection_get())
            self.listbox_browser.selection_set((selected_item_index + 1) % list_length)
        else:
            print(self.focus_get())

    def set_log_update(self, line=''):
        """ Replaces the content of the result field with a given content. """
        self.text_result.configure(state='normal')
        self.text_result.delete('1.0', 'end')
        self.text_result.insert('end', line)
        self.text_result.configure(state='disabled')
        self.update()

    def use_selected_text(self, event=None):
        """ Binds key presses with functions in the file editor. """
        try:
            if event.keysym == 'f':
                self.set_window_find()
            elif event.keysym == 'r':
                self.set_window_replace()
            elif event.keysym == 'slash':
                self.command_text_comment()
            elif event.keysym == 'backslash':
                self.command_text_uncomment()
            else:
                print(event.keysym)
        except UnboundLocalError:
            print("error use_selected_text: selection seems empty")

    def press_key_in_current_mode(self, event=None):
        """ Binds key presses to functions in the current dictionary of key-functions. """
        if f'<{event.keysym}>' in self.key_to_command_current:
            self.key_to_command_current[f'<{event.keysym}>']()
        else:
            pass

    def settings_select_new_directory(self, index_funct):
        """ Prompts to select a directory and replaces the old one with it in a settings entry field. """
        added = askdirectory(title=f'{s.PROGRAM_NAME}: select a new directory', initialdir='../')
        if added:
            self.list_entry_settings[index_funct].delete(0, 'end')
            if '/' == added[-1]:
                added = added[:-1]
            new_path = os.path.relpath(added).replace('\\', '/')
            self.list_entry_settings[index_funct].insert('end', new_path)
            self.set_log_update('setting configuration successful')
        else:
            self.set_log_update('setting configuration aborted')

    def settings_select_add_directory(self, index_funct):
        """ Prompts to select a directory and adds it to a settings entry field. """
        present = self.list_entry_settings[index_funct].get()
        added = f"{askdirectory(title=f'{s.PROGRAM_NAME}: select a new directory', initialdir='../')}"
        if added:
            new_path = os.path.relpath(added).replace('\\', '/')
            if not present:
                self.list_entry_settings[index_funct].insert('end', new_path)
            else:
                self.list_entry_settings[index_funct].insert('end', f', {new_path}')
            self.set_log_update('setting configuration successful')
        else:
            self.set_log_update('setting configuration aborted')

    def position(self, *elements):
        for element in elements:
            try:
                element.place(self.dict_position[element])
            except AttributeError as err:
                print(f'element {element} not predefined\n{err}')

    def retrieve(self, *elements):
        for element in elements:
            try:
                element.place_forget()
            except NameError:
                print(element)
