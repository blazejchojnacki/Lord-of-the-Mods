import os.path
import shutil
import subprocess
import tkinter
import _tkinter
from tkinter.filedialog import askopenfilenames, askdirectory
from tkinter.ttk import Treeview
from tklinenums import TkLineNumbers

import source.core as core
import source.shared as s
from source.constructor import load_file, load_directories
from source.editor import reformat_string, text_find_replace, move_file, duplicates_find
from source.module_control import modules_filter, modules_sort, snapshot_take, snapshot_compare, \
    module_detect_changes, module_copy, module_new, hash_file, Property, \
    definition_edit, DEFINITION_EXAMPLE, DEFINITION_NAME, DEFINITION_CLASSES, Change, check_relative

MODULE_COLUMNS = {Property.NAME: 1, Property.TRANSFER_TYPE: 1, Property.DESCRIPTION: 5}
CHANGES_COLUMNS = {'path': 6, 'type': 1}


class ColumnedListbox(tkinter.ttk.Treeview):
    """ a Tk/Tcl Treeview-based class with predefined columns"""

    def __init__(self, master, width=s.LIST_WIDTH, height=s.UNIT_HEIGHT * 3, columns_dict=None, show='tree headings'):
        super().__init__(master=master, height=height, show=show)
        self.width = width * 6  # # # required for columns widths to set properly
        if columns_dict:
            self.set_columns(columns_dict)

    def set_columns(self, columns_dict):
        self.configure(columns=list(columns_dict.keys()))
        total_quotient = sum(list(columns_dict.values()), 1)
        column_unit_width = int(self.width / total_quotient)
        self.column('#0', width=column_unit_width)
        for column_name in columns_dict:
            self.heading(column_name, text=column_name)
            self.column(
                column_name, width=column_unit_width * columns_dict[column_name]
            )

    def open_children(self):
        for search_index in range(10):
            self.open_children_recursive(parent=str(search_index))

    def open_children_recursive(self, parent):
        """ Recursive function to display all items hierarchically. """
        try:
            self.item(parent, open=True)
            for child in self.get_children(parent):
                self.open_children_recursive(child)
        except _tkinter.TclError:
            pass


popping_list_deployed = False
popping_list_chosen = ''


class PoppingList(tkinter.Toplevel):
    """ Tk-based popping window with a list of choices """

    def __init__(self, master, focus_point, choices: list, **kwargs):
        global popping_list_deployed
        super().__init__(master, **kwargs)
        self.master = master
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.option_listbox = tkinter.Listbox(master=self)
        self.option_listbox.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], font=s.FONT_TEXT,
            selectbackground=s.TEXT_COLORS[0], selectforeground=s.TEXT_COLORS[-1])
        self.option_listbox.pack()
        self.option_list = choices
        for option_name in self.option_list:
            self.option_listbox.insert('end', option_name)

        self.option_listbox.bind('<<ListboxSelect>>', self.on_select_option)
        self.master.bind('<Configure>', self.keep_track)
        popping_list_deployed = True
        self.offset_x = focus_point[0]
        self.offset_y = focus_point[1]
        self.keep_track()
        self.bind('<FocusOut>', self.on_select_cancel)
        self.click_func = self.master.bind('<Button>', self.on_select_cancel, add=True)
        self.mainloop()

    def keep_track(self, event=None):
        """ moves the object along with its master"""
        if event:
            pass
        self.master.update()
        try:
            if popping_list_deployed is True:
                self.geometry(
                    f'+{self.master.winfo_x() + self.offset_x}+{self.master.winfo_y() + self.offset_y}'
                )
        except _tkinter.TclError:
            print(s.internal_message('selection aborted: window closed'))

    def on_select_option(self, event):
        global popping_list_chosen, popping_list_deployed
        if event:
            pass
        try:
            selected_option = self.option_listbox.selection_get()
            popping_list_chosen = selected_option
            self.quit()
            self.destroy()
            popping_list_deployed = False
        except _tkinter.TclError:
            print(s.internal_message('TclError'))

    def on_select_cancel(self, event=None):
        global popping_list_deployed
        if event:
            pass
        try:
            self.destroy()
            popping_list_deployed = False
            self.master.unbind('<Button>', self.click_func)
        except NameError:
            pass


def count_files_recursive(path, counter: int = -1):
    """ Recursively counts the number of files in a directory. """
    if counter == -1:
        items = [_ for _ in os.listdir(path) if os.path.isdir(f'{path}/{_}')]
        counter = 0
    else:
        items = os.listdir(path)
    dir_exceptions = ['.git']
    for item in items:
        if os.path.isdir(f'{path}/{item}') and item not in dir_exceptions:
            counter = count_files_recursive(f'{path}/{item}', counter)
        elif os.path.isfile(f'{path}/{item}'):
            counter += 1
    return counter


def get_change_statistics(module):
    if module[Property.NAME]:
        module_path = f"{core.library}/{module[Property.NAME]}"
        output = (f"mentioned: {len(module[Property.CHANGES])} ("
                  f" removed: {len([_ for _ in module[Property.CHANGES] if _[0] == Change.REMOVED])}"
                  f') | present in module: {count_files_recursive(module_path)}')
        return output
    return ''


class Window(tkinter.Tk):
    """ Tk-based app Window """

    def __init__(self, start_file=None):
        super().__init__()

        s.main_window = self
        s.current_info = tkinter.Toplevel(master=self)
        s.current_info.destroy()
        s.load_aesthetic()
        s.set_title_bar_color(self)

        self.iconbitmap(s.ICON_PATH)
        self.title(s.PROGRAM_NAME)
        self.minsize(width=1100, height=400)
        self.maxsize(width=1600, height=900)
        self.geometry('1250x650')
        self.configure(padx=10, pady=10, background=s.APP_BACKGROUND_COLOR)
        self.focus()

        self.bind('<Key>', self.press_key_in_current_mode)
        self.bind_all('<Control-Key-f>', self.use_selected_text)
        self.bind_all('<Control-Key-r>', self.use_selected_text)

        self.key_to_command_module = {
            '<Return>': self.command_browser_forward,
            '<Right>': self.switch_modules_list,
            '<Left>': self.switch_modules_list,
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

        self.current_path = ''
        self.current_window = ''
        self.global_modules = []
        self.loaded_module = None
        self.current_levels = []
        self.current_file_content_backup = ''
        self.new_module_name = ''
        self.new_module_source = ''
        self.new_changes = {}

        # # # main menu
        self.container_command = tkinter.Frame(master=self)
        self.container_command_buttons = tkinter.Frame(master=self.container_command)
        self.button_menu_back = s.ReactiveButton(master=self.container_command_buttons, small=True, text='back'.upper(),
                                                 command=self.set_window_modules)
        self.button_menu_modules = s.ReactiveButton(
            master=self.container_command_buttons, text='modules'.upper(), command=self.set_window_modules)
        self.button_menu_settings = s.ReactiveButton(
            master=self.container_command_buttons, text='edit settings'.upper(), command=self.set_window_settings)
        self.button_run = s.ReactiveButton(master=self.container_command_buttons)
        self.button_execute = s.ReactiveButton(master=self.container_command_buttons, text='clear logs'.upper(),
                                               command=self.set_log_update)
        self.button_function_find = s.ReactiveButton(
            master=self.container_command_buttons, text='find text'.upper(), command=self.set_window_find)
        self.button_function_replace = s.ReactiveButton(
            master=self.container_command_buttons, text='replace text'.upper(), command=self.set_window_replace)
        self.text_result = tkinter.Text(master=self.container_command, state='disabled')

        self.container_current = tkinter.Frame(master=self)

        # # # window file editor
        self.container_file_content = tkinter.Frame(master=self.container_current)
        self.text_file_content = tkinter.Text(master=self.container_file_content, width=s.TEXT_WIDTH, height=30,
                                              undo=True)
        numeration = TkLineNumbers(self.container_file_content, self.text_file_content, justify='right')
        self.event_delete('<<SelectAll>>', '<Control-Key-/>')
        self.text_file_content.bind('<Control-Key-/>', self.use_selected_text)
        self.text_file_content.bind(r'<Control-Key-\>', self.use_selected_text)
        self.text_file_content.bind('<<Modified>>', lambda event: self.after_idle(numeration.redraw), add=True)
        self.text_file_content.bind('<<Modified>>', lambda event: self.after_idle(self.set_text_color), add=True)

        # # # window settings
        self.container_settings = tkinter.Frame(master=self.container_current)
        list_labels_settings = []
        self.list_entry_settings = []
        list_buttons_settings = []
        for setting in core.settings:
            list_labels_settings.append(tkinter.Label(master=self.container_settings, text=setting))
            self.list_entry_settings.append(tkinter.Entry(master=self.container_settings))
            list_buttons_settings.append(s.ReactiveButton(master=self.container_settings, small=True,
                                                          text='select'.upper()))
        try:
            list_buttons_settings[2].configure(command=lambda: self.settings_select_new_directory(2))
            list_buttons_settings[3].configure(command=lambda: self.settings_select_new_directory(3))
            list_buttons_settings[4].configure(command=lambda: self.settings_select_add_directory(4))
        except IndexError:
            pass

        # # # window modules
        self.container_modules = tkinter.Frame(master=self.container_current)
        label_modules_idle = tkinter.Label(master=self.container_modules, text='available modules:')
        self.treeview_modules_idle = ColumnedListbox(
            master=self.container_modules, width=s.LIST_WIDTH, height=10, columns_dict=MODULE_COLUMNS)
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
        self.button_module_launch = s.ReactiveButton(
            master=container_module_buttons, text='launch'.upper(), command=self.command_module_launch)
        self.button_module_new = s.ReactiveButton(
            master=container_module_buttons, text='new module'.upper(), command=self.set_window_module_new)
        self.button_definition_edit = s.ReactiveButton(
            master=container_module_buttons, text='edit module data'.upper(), command=self.set_window_definition)
        label_modules_active = tkinter.Label(
            master=self.container_modules, text='active modules:', width=s.UNIT_WIDTH * 2)
        self.treeview_modules_active = ColumnedListbox(
            master=self.container_modules, width=s.LIST_WIDTH, height=10, columns_dict=MODULE_COLUMNS)
        self.treeview_modules_active.bind('<<TreeviewSelect>>', self.on_select_module_active)
        self.treeview_modules_active.bind('<Double-1>', self.command_module_browse)

        # # # window definition
        self.container_definition = tkinter.Frame(master=self.container_current)
        self.list_labels_module_editor = []
        self.list_text_definition_editor = []
        for key in DEFINITION_EXAMPLE:
            self.list_labels_module_editor.append(tkinter.Label(master=self.container_definition, text=key))
            self.list_text_definition_editor.append(tkinter.Text(master=self.container_definition))

        # # # window changes
        self.container_changes = tkinter.Frame(master=self.container_current)
        self.label_changes = tkinter.Label(master=self.container_changes, text='changes')
        self.proportions_changes = (6, 1)
        self.treeview_changes = ColumnedListbox(
            master=self.container_changes, width=s.TEXT_WIDTH, height=20, show='headings', columns_dict=CHANGES_COLUMNS)
        self.treeview_changes.bind('<<TreeviewSelect>>', self.on_select_change)
        self.container_changes_new = tkinter.Frame(master=self.container_current)
        self.treeview_changes_new = ColumnedListbox(
            master=self.container_changes_new, width=s.TEXT_WIDTH, height=10, show='headings',
            columns_dict=CHANGES_COLUMNS)
        self.treeview_changes_new.bind('<<TreeviewSelect>>', self.on_select_change)
        self.treeview_changes_new.bind('<Double-1>', self.on_double_click_change_new)

        # # # window new module
        self.container_module_new = tkinter.Frame(master=self.container_current)
        self.label_module_new_name = tkinter.Label(master=self.container_module_new, text='New module name:')
        self.entry_module_new_name = tkinter.Entry(master=self.container_module_new)
        self.label_module_new_options = tkinter.Label(master=self.container_module_new, text='it will be based on:')
        self.label_module_new_options.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0])
        self.container_module_new_options = tkinter.Frame(master=self.container_module_new)
        self.container_module_new_options.configure(background=s.ENTRY_BACKGROUND_COLOR)
        self.variable_option = tkinter.StringVar()
        self.option_button_0 = tkinter.Checkbutton(
            master=self.container_module_new_options, text='nothing', variable=self.variable_option,
            onvalue='nothing')
        self.option_button_a = tkinter.Checkbutton(
            master=self.container_module_new_options, text='a present directory', variable=self.variable_option,
            onvalue='directory')
        self.option_button_b = tkinter.Checkbutton(
            master=self.container_module_new_options, text='a comparison file', variable=self.variable_option,
            onvalue='comparison')
        self.option_button_c = tkinter.Checkbutton(
            master=self.container_module_new_options, text='a snapshot file', variable=self.variable_option,
            onvalue='snapshot')
        self.option_button_0.select()

        # # # window browser
        self.container_browser = tkinter.Frame(master=self.container_current)
        self.label_browser = tkinter.Label(master=self.container_browser)
        self.listbox_browser = tkinter.Listbox(master=self.container_browser, width=s.LIST_WIDTH, height=20)
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

        # # # window find
        self.container_find_replace = tkinter.Frame(master=self.container_current)
        self.container_find = tkinter.Frame(master=self.container_find_replace)
        label_find = tkinter.Label(master=self.container_find, text='find text:')
        self.text_find = tkinter.Text(master=self.container_find)

        # # # window replace
        self.container_replace = tkinter.Frame(master=self.container_find_replace)
        button_replace_copy = s.ReactiveButton(master=self.container_find_replace, command=self.command_copy_find,
                                               text='↓', info_content='copy text to replace field')
        label_replace = tkinter.Label(master=self.container_replace, text='replace with text:')
        self.text_replace = tkinter.Text(master=self.container_replace)

        containers = [
            self.container_current,
            self.container_settings,
            self.container_modules,
            container_module_buttons,
            self.container_module_new,
            self.container_module_new_options,
            self.container_definition,
            self.container_changes,
            self.container_changes_new,
            self.container_browser,
            self.container_file_content,
            self.container_scope_select,
            self.container_find_replace,
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
            self.button_menu_modules,
            self.button_menu_settings,
            self.button_run,
            self.button_execute,
            self.button_function_find,
            self.button_function_replace,
            self.button_module_new,
            self.button_module_attach,
            self.button_module_retrieve,
            self.button_module_reload,
            self.button_module_browse,
            self.button_module_launch,
            self.button_definition_edit,
            button_replace_copy,
            button_scope_select_file,
            self.button_scope_select_folder,
            self.button_scope_except_file,
            button_scope_except_folder,
        ]
        self.check_buttons = [self.option_button_0, self.option_button_a, self.option_button_b, self.option_button_c]
        labels = [
            label_modules_idle,
            label_modules_active,
            self.label_module_new_name,
            self.label_module_new_options,
            self.label_changes,
            self.label_browser,
            self.label_scope_select,
            label_find,
            label_replace,
            self.label_scope_except
        ]
        for setting_label in list_labels_settings:
            labels.append(setting_label)
        for parameter_label in self.list_labels_module_editor:
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
            self.entry_module_new_name
        ]
        for setting_entry in self.list_entry_settings:
            entries.append(setting_entry)

        for button in small_buttons:
            button.place_configure(width=s.UNIT_WIDTH, height=s.UNIT_HEIGHT)
        for button in large_buttons:
            button.place_configure(width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT)
        for label in labels:
            label.place_configure(width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT)
        for text in texts:
            text.place_configure(width=s.TEXT_WIDTH)
        for entry in entries:
            entry.place_configure(width=s.TEXT_WIDTH)

        # # # buttons configured on creation

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
        for check_button in self.check_buttons:
            check_button.configure(background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0],
                                   activebackground=s.APP_BACKGROUND_COLOR, activeforeground=s.TEXT_COLORS[0],
                                   selectcolor=s.ENTRY_BACKGROUND_COLOR)
        self.listbox_browser.configure(
            background=s.ENTRY_BACKGROUND_COLOR, foreground=s.TEXT_COLORS[0], font=s.FONT_TEXT,
            selectbackground=s.TEXT_COLORS[0], selectforeground=s.TEXT_COLORS[-1])
        current_style = tkinter.ttk.Style(master=self)
        current_style.theme_use('clam')
        tkinter.ttk.Style().configure(
            '.', width=s.UNIT_WIDTH * 2, font=s.FONT_TEXT, foreground=s.TEXT_COLORS[0],
            background=s.ENTRY_BACKGROUND_COLOR)
        tkinter.ttk.Style().configure(
            'Treeview', background=s.ENTRY_BACKGROUND_COLOR, fieldbackground=s.ENTRY_BACKGROUND_COLOR, fieldbw=0,
            selectbackground=s.TEXT_COLORS[0], selectforeground=s.TEXT_COLORS[-1])
        tkinter.ttk.Style().configure(
            'Treeview.Heading', borderwidth=0, overbackground=s.TEXT_COLORS[0], overforeground=s.TEXT_COLORS[-1])

        for index in range(len(core.settings)):
            list_labels_settings[index].place(x=0, y=s.UNIT_HEIGHT * index, width=s.UNIT_WIDTH * 2,
                                              height=s.UNIT_HEIGHT)
            self.list_entry_settings[index].place(
                x=s.UNIT_WIDTH * 2 + 10, y=s.UNIT_HEIGHT * index, width=s.TEXT_WIDTH - s.UNIT_WIDTH,
                height=s.UNIT_HEIGHT)
            if index < 2:
                self.list_entry_settings[index].configure(state='disabled')
                continue
            list_buttons_settings[index].place(x=s.TEXT_WIDTH + s.UNIT_WIDTH + 10, y=s.UNIT_HEIGHT * index,
                                               width=s.UNIT_WIDTH, height=s.UNIT_HEIGHT)

        for index in range(len(DEFINITION_EXAMPLE)):
            self.list_labels_module_editor[index].place(x=0, y=s.UNIT_HEIGHT * index, width=s.UNIT_WIDTH * 2,
                                                        height=s.UNIT_HEIGHT)
            self.list_text_definition_editor[index].place(
                x=s.UNIT_WIDTH * 2 + 10, y=s.UNIT_HEIGHT * index, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT)
        self.list_text_definition_editor[-2].place_configure(height=s.UNIT_HEIGHT * 3)
        self.list_text_definition_editor[-1].place_configure(y=s.UNIT_HEIGHT * len(DEFINITION_EXAMPLE))
        self.list_labels_module_editor[-1].place_configure(y=s.UNIT_HEIGHT * len(DEFINITION_EXAMPLE))

        self.dict_position = {
            self.container_current: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 13),

            label_modules_idle: dict(x=0, y=int(s.UNIT_HEIGHT * 2.5), width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            self.treeview_modules_idle: dict(x=s.UNIT_WIDTH * 2, y=0, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT * 5),
            container_module_buttons: dict(x=s.UNIT_WIDTH * 0, y=s.UNIT_HEIGHT * 5 + 5, width=s.FULL_WIDTH,
                                           height=s.UNIT_HEIGHT + 10),
            self.button_module_new: dict(x=s.UNIT_WIDTH * 0, y=0),
            self.button_module_launch: dict(x=s.UNIT_WIDTH * 10, y=0, width=s.DOUBLE_WIDTH, height=s.UNIT_HEIGHT),
            self.button_module_attach: dict(x=s.UNIT_WIDTH * 2, y=0, width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            label_modules_active: dict(x=0, y=int(s.UNIT_HEIGHT * 9), width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            self.treeview_modules_active: dict(x=s.UNIT_WIDTH * 2, y=int(s.UNIT_HEIGHT * 6.5), width=s.TEXT_WIDTH,
                                               height=s.UNIT_HEIGHT * 5),

            self.label_browser: dict(x=0, y=0, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT),
            self.listbox_browser: dict(x=s.UNIT_WIDTH * 1, y=s.UNIT_HEIGHT, width=s.TEXT_WIDTH,
                                       height=s.UNIT_HEIGHT * 10),
            # # # container_module_new
            self.container_module_new: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 13),
            self.label_module_new_name: dict(x=0, y=0, width=s.UNIT_WIDTH * 4, height=s.UNIT_HEIGHT),
            self.entry_module_new_name: dict(x=int(s.UNIT_WIDTH * 0.5), y=s.UNIT_HEIGHT * 1, width=s.UNIT_WIDTH * 3,
                                             height=s.UNIT_HEIGHT),
            self.container_module_new_options: dict(x=int(s.UNIT_WIDTH * 0.5), y=s.UNIT_HEIGHT * 4,
                                                    width=s.UNIT_WIDTH * 3, height=s.UNIT_HEIGHT * 4),
            self.label_module_new_options: dict(x=0, y=s.UNIT_HEIGHT * 3, width=s.UNIT_WIDTH * 4, height=s.UNIT_HEIGHT),
            self.option_button_0: dict(x=0, y=s.UNIT_HEIGHT * 0, width=s.DOUBLE_WIDTH, height=s.UNIT_HEIGHT),
            self.option_button_a: dict(x=0, y=s.UNIT_HEIGHT * 1, width=s.DOUBLE_WIDTH, height=s.UNIT_HEIGHT),
            self.option_button_b: dict(x=0, y=s.UNIT_HEIGHT * 2, width=s.DOUBLE_WIDTH, height=s.UNIT_HEIGHT),
            self.option_button_c: dict(x=0, y=s.UNIT_HEIGHT * 3, width=s.DOUBLE_WIDTH, height=s.UNIT_HEIGHT),

            self.container_changes: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 12),
            self.label_changes: dict(x=0, y=0, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT),
            self.treeview_changes: dict(x=s.UNIT_WIDTH * 1, y=s.UNIT_HEIGHT, width=s.TEXT_WIDTH,
                                        height=s.UNIT_HEIGHT * 10),
            self.container_changes_new: dict(x=0, y=s.UNIT_HEIGHT * 6, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 6),
            self.treeview_changes_new: dict(x=s.UNIT_WIDTH, y=s.UNIT_HEIGHT * 0, width=s.TEXT_WIDTH,
                                            height=s.UNIT_HEIGHT * 5),

            self.label_scope_select: dict(x=0, y=0),
            self.text_scope_select: dict(x=s.UNIT_WIDTH * 2, y=s.UNIT_HEIGHT * 0, width=s.TEXT_WIDTH - s.UNIT_WIDTH * 4,
                                         height=s.UNIT_HEIGHT),
            button_scope_select_file: dict(x=s.TEXT_WIDTH - s.UNIT_WIDTH * 2, y=s.UNIT_HEIGHT * 0),
            self.button_scope_select_folder: dict(x=s.TEXT_WIDTH, y=s.UNIT_HEIGHT * 0),
            self.label_scope_except: dict(x=0, y=s.UNIT_HEIGHT * 1),
            self.text_scope_except: dict(x=s.UNIT_WIDTH * 2, y=s.UNIT_HEIGHT * 1, width=s.TEXT_WIDTH - s.UNIT_WIDTH * 4,
                                         height=s.UNIT_HEIGHT),
            self.button_scope_except_file: dict(x=s.TEXT_WIDTH - s.UNIT_WIDTH * 2, y=s.UNIT_HEIGHT * 1),
            button_scope_except_folder: dict(x=s.TEXT_WIDTH, y=s.UNIT_HEIGHT * 1),

            self.text_file_content: dict(x=s.UNIT_WIDTH * 1, y=0, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT * 12),
            numeration: dict(x=0, y=0, width=s.UNIT_WIDTH - 1, height=s.UNIT_HEIGHT * 12),

            self.container_find_replace: dict(x=0, y=int(s.UNIT_HEIGHT * 7.5), width=s.FULL_WIDTH,
                                              height=s.UNIT_HEIGHT * 3),
            self.container_find: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 1),
            label_find: dict(x=0, y=0, width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            self.text_find: dict(x=s.UNIT_WIDTH * 2, y=0, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT),
            self.container_replace: dict(x=0, y=s.UNIT_HEIGHT, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 2),
            button_replace_copy: dict(x=0, y=0),
            label_replace: dict(x=0, y=s.UNIT_HEIGHT),
            self.text_replace: dict(x=s.UNIT_WIDTH * 2, y=0, width=s.TEXT_WIDTH, height=s.UNIT_HEIGHT * 2),
            # self.container_command:
            self.text_result: dict(x=0, y=0, width=s.FULL_WIDTH, height=int(s.UNIT_HEIGHT * 0.75)),
            self.container_command_buttons: dict(x=0, y=s.UNIT_HEIGHT * 2, anchor='sw', width=s.FULL_WIDTH,
                                                 height=s.UNIT_HEIGHT),
            self.button_menu_back: dict(x=0, y=0),
            self.button_menu_modules: dict(x=s.UNIT_WIDTH * 1, y=0),
            self.button_menu_settings: dict(x=s.UNIT_WIDTH * 3, y=0),
            self.button_run: dict(x=s.UNIT_WIDTH * 5, y=0),
            self.button_execute: dict(x=s.UNIT_WIDTH * 7, y=0),
            self.button_function_find: dict(x=s.UNIT_WIDTH * 11, y=0),
            self.button_function_replace: dict(x=s.UNIT_WIDTH * 13, y=0),

            # non-default
            self.container_modules: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 13),
            self.button_module_browse: dict(x=s.UNIT_WIDTH * 8, y=0, width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            self.button_definition_edit: dict(x=s.UNIT_WIDTH * 12, y=0, width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            self.button_module_retrieve: dict(x=s.UNIT_WIDTH * 4, y=0, width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),
            self.button_module_reload: dict(x=s.UNIT_WIDTH * 6, y=0, width=s.UNIT_WIDTH * 2, height=s.UNIT_HEIGHT),

            self.container_command: dict(x=0, y=s.UNIT_HEIGHT * 15, anchor='sw', width=s.FULL_WIDTH,
                                         height=s.UNIT_HEIGHT * 2),
            self.container_settings: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 11),
            self.container_definition: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 13),
            self.container_browser: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 12),
            self.container_scope_select: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 2),
            self.container_file_content: dict(x=0, y=0, width=s.FULL_WIDTH, height=s.UNIT_HEIGHT * 13),
        }

        self.position(
            self.container_current, self.text_result,
            self.container_command_buttons, self.button_menu_back, self.button_menu_modules, self.button_menu_settings,
            self.label_module_new_name, self.entry_module_new_name, self.label_module_new_options,
            self.container_module_new_options,
            self.option_button_0, self.option_button_a, self.option_button_b, self.option_button_c,
            self.button_run,
            self.button_execute, self.button_function_find, self.button_function_replace,
            container_module_buttons, self.button_module_new, self.button_module_attach,
            self.text_file_content, numeration, self.label_browser, self.listbox_browser,
            label_modules_idle, self.treeview_modules_idle, label_modules_active, self.treeview_modules_active,
            self.label_scope_select, button_scope_select_file, self.button_scope_select_folder, self.text_scope_select,
            self.label_scope_except, self.button_scope_except_file, button_scope_except_folder, self.text_scope_except,
            label_find, self.text_find, button_replace_copy, label_replace, self.text_replace,
            self.container_changes, self.label_changes, self.treeview_changes, self.container_changes_new,
            self.treeview_changes_new,
        )

        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        if start_file:
            self.current_path = start_file
            if self.try_set_window_file():
                pass
            else:
                self.set_window_modules()
                self.set_log_update(self.current_path)
        else:
            self.set_window_modules()
        self.mainloop()

    def on_app_close(self):
        """ Triggered on closing the application to catch unsaved changes in files. """
        self.set_log_update('closing application')
        self.warning_file_save()
        self.quit()

    def set_log_update(self, line=''):
        """ Replaces the content of the result field with a given content. """
        self.text_result.configure(state='normal')
        self.text_result.delete('1.0', 'end')
        self.text_result.insert('end', line)
        self.text_result.configure(state='disabled')
        self.update()

    def warning_file_save(self):
        """ Checks if the edited file have been edited since the previous saving and prompts a question if not. """
        file_named = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip('\n\t {}')
        if file_named and self.current_file_content_backup:
            if self.text_file_content.get('1.0', 'end').strip() != self.current_file_content_backup.strip():
                save_file = s.invoke_choice(
                    title='closing program',
                    text='Do you want to save the file?',
                    buttons=({s.KEY_LABEL: 'yes', s.KEY_RETURN: True, s.KEY_INFO: ''},)
                )
                if save_file == 'yes':
                    self.command_file_save()
        self.current_file_content_backup = ''

    def warning_unsaved_changes(self):
        if self.treeview_changes_new.get_children():
            do_proceed = s.invoke_choice(
                title='unsaved changes',
                text='some changes have not been applied.\n Do you wish to apply them?',
                buttons=({s.KEY_LABEL: 'yes', s.KEY_RETURN: True, s.KEY_INFO: ''},
                         {s.KEY_LABEL: 'no', s.KEY_RETURN: False, s.KEY_INFO: ''})
            )
            if do_proceed is True:
                self.command_change_confirm()
            elif do_proceed is False:
                pass

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

    def clear_container(self, container):
        self.retrieve(container.winfo_children())

    def clear_window(self):
        """ Cleans the screen of all containers. """
        if self.current_window == 'file_editor':
            self.warning_file_save()
        elif self.current_window == 'changes_new':
            self.warning_unsaved_changes()
        self.current_window = ''
        self.retrieve(self.container_browser, self.container_modules, self.container_definition,
                      self.container_find_replace, self.container_find, self.container_replace,
                      self.container_module_new,
                      self.container_scope_select, self.container_file_content, self.container_settings,
                      self.container_changes_new, self.container_changes)

    def set_window_settings(self):
        """ Loads the screen for settings edition. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.retrieve(self.button_run, self.button_execute, self.button_function_find, self.button_function_replace)
        self.position(self.container_settings, self.text_result)
        self.button_menu_settings.configure(text='save settings'.upper(), command=self.command_settings_save)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.command_settings_reload()
        self.current_window = 'settings'
        self.set_log_update('settings edition feature loaded')

    def set_window_modules(self):
        """ Loads the screen for managing modules. """
        self.key_to_command_current = self.key_to_command_module.copy()
        self.clear_window()
        self.retrieve(self.button_definition_edit, self.button_function_find,
                      self.button_function_replace, self.button_menu_back)
        self.position(self.container_modules, self.button_module_new, self.container_command, self.button_run,
                      self.button_execute,
                      self.button_menu_settings, self.container_command_buttons, self.text_result)
        self.container_current.place_configure(height=s.UNIT_HEIGHT * 13)
        self.button_run.configure(text='take snapshot'.upper(), command=self.command_snapshot_take)
        self.button_execute.configure(text='compare snapshots'.upper(), command=self.command_snapshot_compare)
        self.button_menu_settings.configure(text='edit settings'.upper(), command=self.set_window_settings)
        self.button_menu_modules.configure(text='refresh modules'.upper())
        self.refresh_definitions()
        self.treeview_modules_idle.focus_set()
        try:
            self.treeview_modules_idle.selection_set(self.treeview_modules_idle.get_children()[0])
            self.treeview_modules_idle.focus(self.treeview_modules_idle.get_children()[0])
        except IndexError:
            pass
        self.current_window = 'modules'
        self.set_log_update('module manager window loaded.')

    def set_window_module_new(self, start_name: str = ''):
        self.clear_window()
        self.retrieve(self.button_menu_modules, self.button_menu_settings, self.button_execute)
        self.position(self.container_module_new, self.button_menu_back, self.button_run)
        self.button_run.configure(text='create'.upper(), command=self.command_module_new)
        self.button_menu_back.configure(command=self.command_module_new_cancel)
        if start_name:
            self.entry_module_new_name.insert('end', start_name)
        self.current_window = 'module_new'

    def set_window_definition(self):
        """ Loads the screen for modification of module definitions. """
        if not self.global_modules:
            self.global_modules = modules_filter()
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.retrieve(self.button_menu_settings, self.button_function_find, self.button_menu_back)
        self.position(self.container_definition, self.button_execute)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.button_run.configure(text='save parameters'.upper(), command=self.command_definition_save)
        self.button_execute.configure(text='see changed files', command=self.set_window_changes)
        module_selected = self.current_path.split('/')[-1]
        for module in self.global_modules:
            if module_selected == module[Property.NAME]:
                level = 0
                for param in DEFINITION_EXAMPLE:
                    if param == Property.CHANGES:
                        self.list_labels_module_editor[-1].configure(text='changes')
                        self.list_text_definition_editor[-1].delete('1.0', 'end')
                        self.list_text_definition_editor[-1].insert('end', get_change_statistics(module))
                        continue
                    self.list_text_definition_editor[level].configure(state='normal')
                    self.list_text_definition_editor[level].delete('1.0', 'end')
                    if isinstance(module[param], bool):
                        self.list_text_definition_editor[level].insert('end', str(module[param]))
                    else:
                        self.list_text_definition_editor[level].insert('end', module[param])
                    if Property.ACTIVE in param:
                        self.list_text_definition_editor[level].configure(state='disabled')
                    level += 1
                self.loaded_module = module
                break
        self.set_log_update('module definition edition feature loaded.')
        self.current_window = 'definition'

    def set_window_changes(self):
        self.key_to_command_current = self.key_to_command_browser.copy()
        self.clear_window()
        self.retrieve(self.button_execute, self.button_function_find, self.button_function_replace, self.button_run)
        self.position(self.container_changes, self.treeview_changes, self.button_menu_back,
                      self.button_menu_modules, self.button_menu_settings)
        self.button_menu_back.configure(text='back', command=self.set_window_definition)
        self.button_menu_modules.configure(text='return to modules', command=self.set_window_modules)
        self.button_menu_settings.configure(text='edit changes', command=self.set_window_change_new)
        # # # displayed on selection - see on_select_change()
        self.button_execute.configure(text='open file', command=self.set_window_file)
        self.treeview_changes.delete(*self.treeview_changes.get_children())
        change_index = 0
        for change in self.loaded_module[Property.CHANGES]:
            change_values = (change, self.loaded_module[Property.CHANGES][change][0])
            self.treeview_changes.insert(index=change_index, parent='', values=change_values, iid=change_index)
            change_index += 1
        self.label_changes.configure(text=f"changes of {self.loaded_module[Property.NAME]}")
        self.treeview_changes.bind('<Double-1>', self.set_window_file)
        self.current_window = 'changes'
        self.set_log_update('Changes screen loaded')

    def set_window_change_new(self):
        self.retrieve()
        self.position(self.container_changes_new, self.button_menu_modules, self.button_menu_settings,
                      self.button_run, self.button_execute, self.button_function_find)
        self.button_menu_back.configure(command=self.set_window_changes)
        self.button_menu_modules.configure(text='add file(s)', command=self.command_change_path)
        self.button_menu_settings.configure(text='copy file(s)', command=self.command_change_copy)
        self.button_run.configure(text='delete change(s)', command=self.command_change_delete)
        self.button_execute.configure(text='apply change(s)', command=self.command_change_confirm)
        self.button_function_find.configure(text='change type', command=self.change_type)
        self.container_changes.place_configure(height=s.UNIT_HEIGHT * 6)
        self.treeview_changes.place_configure(height=s.UNIT_HEIGHT * 5)
        self.treeview_changes.bind('<Double-1>', self.on_double_click_change_old)
        self.current_window = 'changes_new'
        self.set_log_update('Changes edition screen loaded')

    def set_window_browser(self):
        """ Loads the screen for browsing in modules directories. """
        self.key_to_command_current = self.key_to_command_browser.copy()
        self.clear_window()
        self.retrieve(self.button_module_new, self.button_function_find, self.button_function_replace,
                      self.button_menu_settings)
        self.position(self.container_browser)
        self.container_current.place_configure(height=s.UNIT_HEIGHT * 13)
        self.container_command.place_configure(height=s.UNIT_HEIGHT * 2)
        self.container_command_buttons.place_configure(y=s.UNIT_HEIGHT * 2)
        self.text_result.place_configure(height=int(s.UNIT_HEIGHT * 0.75))
        self.button_run.configure(text='open'.upper(), command=self.command_browser_forward)
        self.button_execute.configure(text='move file'.upper(), command=self.set_window_move)
        self.button_menu_back.config(command=self.command_browser_back)
        self.open_browser_item()
        self.listbox_browser.focus()
        self.current_window = 'browser'
        self.set_log_update(f'File browser loaded. Path: {os.path.abspath(self.current_path)}')

    def set_window_move(self):
        """ Loads the screen for moving files. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.retrieve(self.button_scope_select_folder, self.button_scope_except_file)
        self.position(self.container_scope_select)
        self.container_current.place_configure(height=s.UNIT_HEIGHT * 5)
        self.container_command.place_configure(height=s.UNIT_HEIGHT * 10)
        self.container_command_buttons.place_configure(y=s.UNIT_HEIGHT * 10)
        self.button_menu_back.configure(command=self.command_browser_back)
        self.button_run.configure(text='move the file'.upper(), command=self.command_run_move)
        self.button_run.focus()
        self.button_execute.configure(text='clear logs'.upper(), command=self.set_log_update)
        self.text_result.place_configure(height=s.UNIT_HEIGHT * 9)
        try:
            self.current_path = f"{self.label_browser.cget('text')}/{self.listbox_browser.selection_get()}".replace(
                '\\', '/')
        except _tkinter.TclError:
            print(s.internal_message('file not selected'))
        self.label_scope_select.configure(text='file')
        self.text_scope_select.delete('1.0', 'end')
        try:
            self.text_scope_select.insert('1.0',
                                          f"{self.label_browser.cget('text')}/{self.listbox_browser.selection_get()}")
        except _tkinter.TclError:
            self.text_scope_select.insert('end', self.current_path)
        self.label_scope_except.configure(text='to folder')
        self.current_window = 'file_move'
        self.set_log_update(f'move feature loaded. file: {self.current_path}')

    def try_set_window_file(self):
        if self.command_file_load():
            self.set_window_file()
            return True
        return False

    def set_window_file(self, event=None):
        """ Loads the screen for file edition """
        if event:
            pass
        self.clear_window()
        self.key_to_command_current = self.key_to_command_text.copy()
        self.retrieve(self.button_execute)
        self.position(self.container_file_content, self.button_run, self.button_function_find,
                      self.button_function_replace)
        self.container_current.place_configure(height=s.UNIT_HEIGHT * 13)
        self.text_file_content.place_configure(height=s.UNIT_HEIGHT * 12)
        self.container_command.place_configure(height=s.UNIT_HEIGHT * 2)
        self.container_command_buttons.place_configure(y=s.UNIT_HEIGHT * 2)
        self.text_result.place_configure(height=int(s.UNIT_HEIGHT * 0.75))
        self.text_file_content.focus()
        self.button_menu_back.configure(command=self.command_browser_back)
        self.button_run.configure(text='save file'.upper(), command=self.command_file_save, state='normal')
        self.current_window = 'file_editor'
        self.set_log_update(f'file editor loaded. file {self.current_path}')

    def set_window_find(self):
        """ Loads the screen for finding text. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.retrieve(self.button_menu_settings, self.button_function_find)
        self.position(self.container_file_content, self.container_scope_select, self.container_find,
                      self.button_function_replace, self.container_find_replace,
                      self.button_scope_select_folder, self.button_scope_except_file)
        self.container_current.place_configure(height=s.UNIT_HEIGHT * 10)
        self.text_file_content.place_configure(height=s.UNIT_HEIGHT * 5)
        self.container_command.place_configure(height=s.UNIT_HEIGHT * 5)
        self.container_command_buttons.place_configure(y=s.UNIT_HEIGHT * 5)
        self.text_result.place_configure(height=s.UNIT_HEIGHT * 4)
        self.container_file_content.place_configure(height=s.UNIT_HEIGHT * 5)
        self.container_scope_select.place_configure(y=int(s.UNIT_HEIGHT * 5.5))
        self.button_menu_back.config(command=self.set_window_file)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.button_run.configure(text='find text'.upper(), command=self.command_run_find)
        self.button_execute.configure(text='clear logs'.upper(), command=self.set_log_update)
        try:
            selection = reformat_string(self.text_file_content.selection_get(), direction='display')
            self.text_find.delete('1.0', 'end')
            self.text_find.insert('1.0', selection)
        except UnboundLocalError:
            print(s.internal_message('UnboundLocalError'))
        except _tkinter.TclError:
            print(s.internal_message('no text selected'))
        self.text_result.focus()
        self.current_window = 'text_find'
        self.set_log_update('find feature loaded')
        self.command_run_find()

    def set_window_replace(self):
        """ Loads the screen for replacing text. """
        self.key_to_command_current = self.key_to_command_text.copy()
        self.clear_window()
        self.retrieve(self.button_menu_settings, self.button_function_replace)
        self.position(self.container_file_content, self.container_scope_select, self.container_find,
                      self.container_replace, self.container_find_replace,
                      self.button_function_find, self.button_scope_select_folder, self.button_scope_except_file)
        self.text_file_content.place_configure(height=s.UNIT_HEIGHT * 5)
        self.container_current.place_configure(height=s.UNIT_HEIGHT * 11)
        self.container_command.place_configure(height=s.UNIT_HEIGHT * 4)
        self.container_command_buttons.place_configure(y=s.UNIT_HEIGHT * 4)
        self.text_result.place_configure(height=s.UNIT_HEIGHT * 3)
        self.container_file_content.place_configure(height=s.UNIT_HEIGHT * 5)
        self.container_scope_select.place_configure(y=int(s.UNIT_HEIGHT * 5.5))
        self.button_menu_back.config(command=self.set_window_file)
        self.button_menu_modules.configure(text='return to modules'.upper())
        self.button_run.configure(text='replace text'.upper(), command=self.command_run_replace)
        self.button_run.focus()
        self.button_execute.configure(text='clear logs'.upper(), command=self.set_log_update)
        try:
            selection = reformat_string(self.text_file_content.selection_get(), direction='display')
            self.text_find.delete('1.0', 'end')
            self.text_find.insert('1.0', selection)
        except UnboundLocalError:
            print(s.internal_message('UnboundLocalError'))
        except _tkinter.TclError:
            print(s.internal_message('no text selected'))
        self.current_window = 'self.text_replace'
        self.set_log_update('replace feature loaded')

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

    def command_settings_save(self):
        """ Reads the values inserted in the settings text fields and saves them to the SETTINGS_FILE. """
        counter = 0
        setting_value = []
        new_settings = {}
        for entry_setting in self.list_entry_settings:
            setting_value.append(entry_setting.get())
        for setting_key in core.settings:
            if core.settings[setting_key] != setting_value[counter]:
                if isinstance(core.settings[setting_key], list):
                    setting_dict_list = setting_value[counter].split(', ')
                    if core.settings[setting_key] and setting_dict_list:
                        if core.settings[setting_key] != setting_dict_list:
                            new_settings[setting_key] = setting_dict_list
                    elif setting_dict_list != ['']:
                        new_settings[setting_key] = setting_dict_list
                    else:
                        pass
                elif isinstance(core.settings[setting_key], str):
                    new_settings[setting_key] = setting_value[counter]
            counter += 1
        if new_settings:
            try:
                if core.settings.load(new_settings):
                    self.set_log_update('Settings saved and checked.')
                else:
                    self.set_log_update('The provided value seems to be incorrect.')
            except s.InternalError as error:
                self.set_log_update(error.message)
                self.command_settings_reload()

    def command_settings_reload(self):
        """ Reads the settings from the SETTINGS_FILE and inserts them into the settings text fields. """
        counter = 0
        for setting_key in core.settings:
            self.list_entry_settings[counter].delete('0', 'end')
            if isinstance(core.settings[setting_key], list):
                self.list_entry_settings[counter].insert('end', ', '.join(core.settings[setting_key]))
            else:
                self.list_entry_settings[counter].insert('end', core.settings[setting_key])
            counter += 1

    def on_select_module_idle(self, event):
        """ Triggered on selection of a non-active module, shows or hides the desired buttons"""
        if event:
            pass
        try:
            self.loaded_module = modules_filter(
                **{Property.NAME:
                    self.treeview_modules_idle.item(self.treeview_modules_idle.selection()[0], 'values')[0]})[0]
            self.current_path = (
                f"{core.library}/"
                f"{self.treeview_modules_idle.item(self.treeview_modules_idle.selection()[0], 'values')[0]}")
            self.treeview_modules_active.selection_remove(self.treeview_modules_active.selection()[0])
            # # # selection_remove is a selection event steeling focus to the other list
            self.treeview_modules_idle.selection_set(self.treeview_modules_idle.selection()[0])
        except IndexError:
            pass
        self.key_to_command_current['<Return>'] = self.command_module_browse
        self.position(self.button_module_attach, self.button_module_browse, self.button_definition_edit)
        self.retrieve(self.button_module_retrieve, self.button_module_reload, self.button_module_launch)
        self.treeview_modules_idle.focus()

    def on_select_module_active(self, event):
        """ Triggered on selection of an active module, shows or hides the desired buttons. """
        if event:
            pass
        try:
            self.loaded_module = modules_filter(
                **{Property.NAME:
                    self.treeview_modules_active.item(self.treeview_modules_active.selection()[0], 'values')[0]})[0]
            self.current_path = (
                f"{core.library}/"
                f"{self.treeview_modules_active.item(self.treeview_modules_active.selection()[0], 'values')[0]}")
            self.treeview_modules_idle.selection_remove(self.treeview_modules_idle.selection()[0])
            self.treeview_modules_active.selection_set(self.treeview_modules_active.selection()[0])
        except IndexError:
            pass
        self.key_to_command_current['<Return>'] = self.command_module_browse
        self.position(self.button_module_retrieve, self.button_module_reload, self.button_module_browse,
                      self.button_definition_edit)
        if self.loaded_module[Property.LAUNCH]:
            self.position(self.button_module_launch)
        else:
            self.retrieve(self.button_module_launch)
        self.retrieve(self.button_module_attach)

    def switch_modules_list(self):
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

    def refresh_definitions(self):
        """ Refreshes the lists of active and non-active modules. """
        try:
            self.treeview_modules_active.delete(*self.treeview_modules_active.get_children())
            library_folders = [_ for _ in os.listdir(core.library) if _ not in core.settings[s.Setting.EXCEPTIONS]]
            for folder in library_folders:
                if not os.path.isfile(f'{core.library}/{folder}/{DEFINITION_NAME}'):
                    self.set_log_update(f'Detected a definition-less folder in the library - {folder}')
                    do_initiate = s.invoke_choice(
                        title='unsaved changes',
                        text=f'The folder {core.library}/{folder}\n seems to have no properties.\n'
                             'Do you wish it to become a mod?\n',
                        buttons=({s.KEY_LABEL: 'yes', s.KEY_RETURN: True, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'no', s.KEY_RETURN: False, s.KEY_INFO: ''})
                    )
                    if do_initiate:
                        self.set_window_module_new(start_name=folder)
                        return
                    if not do_initiate:
                        core.settings.save({s.Setting.EXCEPTIONS: folder})
            active_modules = modules_filter(**{Property.ACTIVE: True})
            active_module_parent_dict = modules_sort(modules=active_modules)
            for module in active_modules:
                self.treeview_modules_active.insert(
                    parent='', index=active_modules.index(module), iid=active_modules.index(module),
                    values=tuple(module[_] for _ in MODULE_COLUMNS)
                )
                self.global_modules.append(module)
            for module in active_modules:
                try:
                    parent_index = active_module_parent_dict[module[Property.NAME]]
                    self.treeview_modules_active.move(active_modules.index(module), parent_index, 0)
                except KeyError:
                    pass
            self.treeview_modules_active.open_children()

            self.treeview_modules_idle.delete(*self.treeview_modules_idle.get_children())
            idle_modules = modules_filter(**{Property.ACTIVE: False})
            idle_module_parent_dict = modules_sort(modules=idle_modules)
            for module in idle_modules:
                self.treeview_modules_idle.insert(
                    parent='', index=idle_modules.index(module), iid=idle_modules.index(module),
                    values=tuple(module[_] for _ in MODULE_COLUMNS)
                )
                self.global_modules.append(module)
            for module in idle_modules:
                try:
                    parent_index = idle_module_parent_dict[module[Property.NAME]]
                    self.treeview_modules_idle.move(idle_modules.index(module), parent_index, 0)
                except KeyError:
                    pass
            self.treeview_modules_idle.open_children()
        except s.InternalError:
            self.set_log_update('definitions not loaded - settings not loaded.')
            return
        except _tkinter.TclError:
            self.set_log_update('loading module error')
        self.retrieve(self.button_module_retrieve, self.button_module_attach)

    def command_module_new(self):
        """ Creates a new module after asking for a name and a way to create it. """
        self.new_module_name = self.entry_module_new_name.get()
        self.new_module_source = self.variable_option.get()
        # TODO: test 'not in os.listdir(core.library)'
        if self.new_module_name and self.new_module_name not in os.listdir(core.library):
            self.set_log_update(f'command_module_new: creating module {self.new_module_name}. Please wait ...')
            output = module_new(self.new_module_name, changes_source=self.new_module_source)
            self.set_window_modules()
            self.set_log_update(output)
        else:
            self.label_module_new_name.configure(text=' Please provide a name unique to the new module')
            self.set_log_update('command_module_new error: a correct unique name was not provided')
        self.new_module_name = ''

    def command_module_new_cancel(self):
        """ escape the module_new screen """
        self.label_module_new_name.configure(text='')
        self.option_button_0.select()
        self.set_window_modules()
        self.set_log_update('new module creation cancelled')

    def command_module_copy(self):
        """ Copies the selected module. Currently, not in use """
        module_selected = self.current_path
        name = module_selected.split('/')[-1] + '_copy'
        self.set_log_update(module_copy(name, module_selected))
        self.refresh_definitions()

    def command_module_attach(self):
        """ Activates the selected module """
        if not self.global_modules:
            self.global_modules = modules_filter()
        try:
            name_module_selected = self.treeview_modules_idle.item(self.treeview_modules_idle.focus(), 'values')[0]
            self.set_log_update(f'loading module {name_module_selected} ...')
            try:
                module = modules_filter(**{Property.NAME: name_module_selected})[0]
                if ancestor_module := check_relative(module, Property.OVERRIDES):
                    answer = s.invoke_choice(
                        title='override retrieval',
                        text=f'This mod depends on another that is not active.\n'
                             f'Do you wish to attach the ancestor mod and continue?\n{ancestor_module[Property.NAME]}',
                        buttons=({s.KEY_LABEL: 'yes', s.KEY_RETURN: True, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'no', s.KEY_RETURN: False, s.KEY_INFO: ''})
                    )
                    if answer is True or answer == 'yes' or answer == 'ok':
                        ancestor_module.attach()
                    elif answer is None or answer == 'cancel' or answer is False:
                        self.set_log_update('module loading aborted')
                        return
                if changes := module_detect_changes(module):
                    answer = s.invoke_choice(
                        title='mod changes',
                        text=f'Changes have been detected.\nDo you wish to update the mod and continue?\n'
                             f'{str(changes)[:1000]}',
                        buttons=({s.KEY_LABEL: 'update', s.KEY_RETURN: True, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'no update', s.KEY_RETURN: False, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'cancel', s.KEY_RETURN: None, s.KEY_INFO: ''})
                    )
                    if answer is True or answer == 'yes':
                        module.edit(changes=module[Property.CHANGES].update(changes))
                    elif answer is False or answer == 'no':
                        pass
                    elif answer is None or answer == 'cancel':
                        self.set_log_update('module loading aborted')
                        return
                if module.attach():
                    self.set_log_update(f'module {name_module_selected} loaded')
                else:
                    self.set_log_update(f'module {name_module_selected} not loaded')
                return self.refresh_definitions()
            except IndexError:
                self.set_log_update(f'command_module_attach error: module {name_module_selected} not found')
        except _tkinter.TclError:
            self.set_log_update('command_module_attach warning: TclError')
        except s.InternalError as err:
            self.set_log_update(err.message)

    def command_module_retrieve(self):
        """ Deactivates the selected module. """
        if not self.global_modules:
            self.global_modules = modules_filter()
        try:
            module_selected = self.treeview_modules_active.item(self.treeview_modules_active.focus(), 'values')[0]
            self.set_log_update(f'unloading mod {module_selected} ...')
            try:
                module = modules_filter(**{Property.NAME: module_selected})[0]
                if heir_module := check_relative(module, Property.OVERRODE_BY):
                    answer = s.invoke_choice(
                        title='override retrieval',
                        text=f'This mod depends on another that is still active.\n'
                             f'Do you wish to detach the heir mod and continue?\n{heir_module[Property.NAME]}',
                        buttons=({s.KEY_LABEL: 'yes', s.KEY_RETURN: True, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'no', s.KEY_RETURN: False, s.KEY_INFO: ''})
                    )
                    if answer is True or answer == 'yes' or answer == 'ok':
                        heir_module.retrieve()
                    elif answer is None or answer == 'cancel' or answer is False:
                        self.set_log_update('module retrieval aborted')
                        return

                # OPTIMIZE: save changes in the definition
                if changes := module_detect_changes(module=module):
                    file_fate = ''
                    if module[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[1]:
                        file_fate = f"Since the module is a '{DEFINITION_CLASSES[1]}', they will be deleted.\n"
                    elif module[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0]:
                        file_fate = f"Since the module is a '{DEFINITION_CLASSES[0]}', they will be incorporated.\n"
                    do_proceed = s.invoke_choice(
                        title='mod changes',
                        text=f'Files have been changed since the mod have been attached.\n{file_fate}'
                             ' Do you wish to proceed and update the file?\n'
                             f'{str(changes)[:1000]}',
                        buttons=({s.KEY_LABEL: 'update', s.KEY_RETURN: True, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'no update', s.KEY_RETURN: False, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'cancel', s.KEY_RETURN: None, s.KEY_INFO: ''})
                    )  # # # too big changes crash the message box: it will not display and return False directly
                    if do_proceed is True:
                        module.edit(changes=module[Property.CHANGES].update(changes))
                        changes = {}
                    elif do_proceed is False:
                        changes = {}
                    elif do_proceed is None:
                        pass
                if not changes:
                    if module.retrieve():
                        self.refresh_definitions()
                        self.set_log_update(f"module {module[Property.NAME]} deactivated")
                    else:
                        self.set_log_update(
                            f'command_module_retrieve error: module {module_selected} retrieval aborted')
                    return
                else:
                    self.set_log_update(f'command_module_retrieve error: module {module_selected} retrieval aborted')
                    return
            except IndexError:
                self.set_log_update(f'command_module_retrieve error: module {module_selected} not found')
        except _tkinter.TclError:
            self.set_log_update('command_module_retrieve error: module not selected')
        except s.InternalError as err:
            self.set_log_update(err.message)

    def command_module_reload(self):
        """ Reloads the selected module by detaching it and attaching again. """
        if not self.global_modules:
            self.global_modules = modules_filter()
        try:
            module_selected = self.treeview_modules_active.item(self.treeview_modules_active.focus(), 'values')[0]
            self.set_log_update(f'Reloading module {module_selected}. Please wait ...')
            for module in self.global_modules:
                if module[Property.NAME] == module_selected:
                    if module.reload():
                        self.refresh_definitions()
                        self.set_log_update(f'Module {module_selected} reloaded. Please wait ...')
                        return
                    else:
                        self.set_log_update(f'The module could not be reloaded.')
            self.set_log_update(f'command_module_reload error: mod {module_selected} not found')
        except _tkinter.TclError:
            self.set_log_update('command_module_reload error: no mod selected')

    def command_module_launch(self, event=None):
        if event:
            pass
        if self.loaded_module is DEFINITION_EXAMPLE:
            self.loaded_module = modules_filter(**{Property.NAME: self.current_path.split('/')[-1]})[0]
        if self.loaded_module[Property.LAUNCH]:
            # # # restricting commands to launch an exe with a mod at best
            try:
                for command in self.loaded_module[Property.LAUNCH].split('\n'):
                    command_mod = ''
                    if '.exe' in command:
                        # # # OPTIMIZE: mount disk if not mounted
                        if command.endswith('.exe') and os.path.isfile(command):
                            command_exe = command
                        elif os.path.isfile(command[:command.index('.exe') + len('.exe')]) and ' -mod ' in command:
                            if os.path.isdir(command.split(' -mod ')[1].strip('"')):
                                command_exe = command[:command.index('.exe') + len('.exe')]
                                command_mod = command.split(' -mod ')[1]
                            else:
                                raise s.InternalError
                        else:
                            raise s.InternalError
                        if command_exe:
                            # # # OPTIMIZE: allow using LotM commands
                            if command_mod:
                                self.set_log_update(
                                    f'Launching {command_exe} -mod {command_mod}. The application will be paused.')
                                subprocess.run(f"{command_exe} -mod {command_mod}")
                                self.set_log_update('Application resumed.')
                            # # # OPTIMIZE: mount disk if not mounted
                            else:
                                self.set_log_update(f'Launching {command_exe}. The application will be paused.')
                                subprocess.run(f"{command_exe}")
                                self.set_log_update('Application resumed.')
                        else:
                            raise s.InternalError
                    else:
                        raise s.InternalError
            except s.InternalError:
                return self.set_log_update('launch command is incorrect')

    def command_definition_save(self):
        """ Saves the current module definition. """
        output = 'module data edition failed'
        module_selected = self.current_path.split('/')[-1]
        for module in self.global_modules:
            if module_selected == module[Property.NAME]:
                edited_parameters = {}
                expected_definition = module.copy()
                level = 0
                for param in DEFINITION_EXAMPLE:
                    if param == Property.CHANGES:
                        continue
                    value = self.list_text_definition_editor[level].get('1.0', 'end').strip()
                    if value != module[param]:
                        if param == Property.TRANSFER_TYPE and value not in DEFINITION_CLASSES:
                            break
                        elif param != Property.ACTIVE:
                            edited_parameters[param] = value
                            expected_definition[param] = value
                    level += 1
                try:
                    new_definition = definition_edit(module, **edited_parameters)
                    if new_definition == expected_definition:
                        output = 'new definition saved'
                    if Property.TRANSFER_TYPE in edited_parameters and module[Property.ACTIVE] is True:
                        module.reload_after_class_change()
                    break
                except s.InternalError as error:
                    output = error.message
        self.set_log_update(output)

    def on_select_change(self, event):
        """ upon selecting a changed file, enables the 'open file' button """
        if event:
            pass
        current_treeview: ColumnedListbox
        current_treeview = self.focus_get()
        if current_treeview == self.treeview_changes or current_treeview == self.treeview_changes_new:
            try:
                self.current_path = (
                    f"{core.library}/{self.loaded_module[Property.NAME]}/"
                    f"{current_treeview.item(current_treeview.selection()[0], 'values')[0]}")
                self.position(self.button_execute)
            except IndexError:
                self.retrieve(self.button_execute)
                pass

    def change_type(self, x=s.DOUBLE_WIDTH * 5, y=s.UNIT_HEIGHT * 8, tree='old and new'):
        """"""
        global popping_list_chosen
        PoppingList(
            master=self, focus_point=(x + s.DOUBLE_WIDTH, y + s.UNIT_HEIGHT * 2), choices=list(_ for _ in Change))
        try:
            if self.treeview_changes.selection() and 'old' in tree:
                for selected in self.treeview_changes.selection():
                    self.treeview_changes.set(
                        selected, CHANGES_COLUMNS[1], popping_list_chosen)
                    path_added = self.treeview_changes.item(selected, 'values')[0]
                    self.loaded_module[Property.CHANGES][path_added][0] = popping_list_chosen
            if self.treeview_changes_new.selection() and 'new' in tree:
                for selected in self.treeview_changes_new.selection():
                    self.treeview_changes_new.set(
                        selected, CHANGES_COLUMNS[1], popping_list_chosen)
                    path_added = self.treeview_changes_new.item(selected, 'values')[0]
                    self.new_changes[path_added][0] = popping_list_chosen
        except IndexError:
            pass
        except _tkinter.TclError:
            self.set_log_update(popping_list_chosen)

    def on_double_click_change_old(self, event=None):
        """ - """
        self.change_type(event.x, event.y, 'old')

    def on_double_click_change_new(self, event=None):
        """ - """
        self.change_type(event.x, event.y + s.UNIT_HEIGHT * 5, 'new')

    def command_change_path(self):
        """ - """
        module_path = f'{core.library}/{self.loaded_module[Property.NAME]}'
        paths_added = tkinter.filedialog.askopenfilenames(title=s.PROGRAM_NAME, initialdir=module_path)
        for path_added in paths_added:
            hash_value = hash_file(path_added)
            if module_path in path_added:
                path_added = path_added[len(module_path) + 1:]
            self.treeview_changes_new.insert('', 'end', values=(path_added, Change.CHANGED))
            try:
                self.new_changes[path_added] = [Change.CHANGED, hash_value]
            except TypeError as error:
                print(error)

    def command_change_copy(self):
        """ Copies selected files in the change list """
        module_path = f'{core.library}/{self.loaded_module[Property.NAME]}'
        game_directory = os.path.abspath('../').replace('\\', '/')
        paths_added = tkinter.filedialog.askopenfilenames(title=s.PROGRAM_NAME, initialdir='../')
        for path_added in paths_added:
            if game_directory in path_added and module_path not in path_added:
                new_path = path_added[path_added.rfind(game_directory) + len(game_directory):]
                os.makedirs(f'{module_path}/{new_path[:new_path.rfind('/')]}', exist_ok=True)
                shutil.copy2(src=path_added, dst=f'{module_path}/{new_path}')
                hash_value = hash_file(f'{module_path}/{new_path}')
                self.treeview_changes_new.insert('', 'end', values=(new_path, Change.CHANGED))
                self.new_changes[new_path] = [Change.CHANGED, hash_value]
            else:
                self.set_log_update(f'file {path_added} could be copied')

    def command_change_confirm(self):
        """ saves the changes pending in the change list """
        for change_new_id in self.treeview_changes_new.get_children():
            change_new_values = self.treeview_changes_new.item(change_new_id, 'values')
            if isinstance(change_new_values, tuple):
                self.treeview_changes.insert(parent='', index='end', values=change_new_values)
                self.treeview_changes.see(self.treeview_changes.get_children()[-1])
                self.treeview_changes_new.delete(change_new_id)
        # # # save changes:
        self.loaded_module[Property.CHANGES].update(self.new_changes)
        self.loaded_module.edit(changes=self.loaded_module[Property.CHANGES])
        self.set_window_changes()

    def command_change_delete(self):
        """ Deletes a change file position from a change list """
        try:
            if self.treeview_changes.selection():
                for selected in self.treeview_changes.selection():
                    file_path = self.treeview_changes.item(selected, 'values')[0]
                    self.loaded_module[Property.CHANGES].pop(file_path)
                    self.treeview_changes.delete(selected)
                self.loaded_module.edit(changes=self.loaded_module[Property.CHANGES])
            if self.treeview_changes_new.selection():
                for selected in self.treeview_changes_new.selection():
                    file_path = self.treeview_changes_new.item(selected, 'values')[0]
                    self.new_changes.pop(file_path)
                    self.treeview_changes_new.delete(selected)
        except _tkinter.TclError:
            print(s.internal_message('TclError'))
        except IndexError:
            print(s.internal_message('IndexError'))
        except KeyError:
            print(s.internal_message('KeyError'))

    def command_module_browse(self, event=None):
        """ Allows to start browsing from the object folder if it can be found. """
        if event:
            pass
        self.loaded_module = modules_filter(**{Property.NAME: self.current_path.split('/')[-1]})[0]
        game_paths = core.games
        if self.loaded_module[Property.TRANSFER_TYPE] == DEFINITION_CLASSES[0] and self.loaded_module[Property.ACTIVE]:
            if not self.loaded_module[Property.GAME]:
                for change_key in self.loaded_module[Property.CHANGES]:
                    change_split = change_key.split('/')
                    if os.path.isdir('/'.join(change_split[:2])) and '/'.join(change_split[1:-1]) in game_paths:
                        self.current_path = '/'.join((change_split[0], game_paths[game_paths.index(change_split[1])]))
                        if os.path.isdir(f'{self.current_path}/data/ini/object'):
                            self.current_path = f'{self.current_path}/data/ini/object'
                        break
            elif self.loaded_module[Property.GAME] in game_paths:
                if os.path.isdir(f"../{game_paths[game_paths.index(self.loaded_module[Property.GAME])]}"):
                    self.current_path = f"../{game_paths[game_paths.index(self.loaded_module[Property.GAME])]}"
            elif f"{self.loaded_module[Property.GAME]}/aotr" in game_paths:
                if os.path.isdir(f"../{self.loaded_module[Property.GAME]}/aotr/data/ini/object"):
                    self.current_path = f"../{self.loaded_module[Property.GAME]}/aotr/data/ini/object"
                elif os.path.isdir(f"../{self.loaded_module[Property.GAME]}/aotr"):
                    self.current_path = f"../{self.loaded_module[Property.GAME]}/aotr"
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
            print(s.internal_message('_tkinter.TclError - no selection'))
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
            if self.try_set_window_file():
                self.listbox_browser.selection_clear(self.listbox_browser.curselection())
                self.position(self.button_execute)
                self.set_log_update(f'opened {os.path.abspath(self.current_path)}')
        self.label_browser.configure(text=os.path.abspath(self.current_path))
        self.position(self.button_menu_back)

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
                module_index_start = self.current_path.find(core.library) + len(core.library) + 1
                module_index_end = self.current_path.replace('\\', '/').find('/', module_index_start)
                current_module_name = self.current_path[module_index_start: module_index_end]
                current_module_list = modules_filter(**{Property.NAME: current_module_name})
                if current_module_list:
                    self.loaded_module = current_module_list[0]
                else:
                    module_index_start = self.current_path.find(s.MAIN_DIRECTORY) + len(s.MAIN_DIRECTORY) + 1
                    module_index_end = self.current_path.replace('\\', '/').find('/', module_index_start)
                    current_module_name = self.current_path[module_index_start: module_index_end]
                    current_module_list = modules_filter(**{Property.NAME: current_module_name})
                    if current_module_list:
                        self.loaded_module = current_module_list[0]
                    else:
                        output += '\nmodule not found - definition not updated.\n'
                        return self.set_log_update(output)
                new_changes = {}
                for file_path in self.loaded_module[Property.CHANGES]:
                    file_name = file_named.replace('\\', '/').split('/')[-1]
                    if file_path.split('/')[-1] == file_name:
                        file_rel_path = '..' + to_folder[module_index_end + 1:].replace('\\', '/')
                        new_changes[f'{file_rel_path}/{file_name}'] = self.loaded_module[Property.CHANGES][file_path]
                    else:
                        new_changes[file_path] = self.loaded_module[Property.CHANGES][file_path]
                definition_edit(self.loaded_module, changes=new_changes)
        self.set_log_update(output)

    def command_run_duplicate(self):
        """ Runs the duplicates_commenter function. """
        file_named = self.text_scope_select.get('1.0', 'end').replace('/', '\\').strip()
        output = duplicates_find(of_object_or_file=file_named)
        self.set_log_update(output)

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
            print(s.internal_message("selection seems empty"))

    def press_key_in_current_mode(self, event=None):
        """ Binds key presses to functions in the current dictionary of key-functions. """
        if f'<{event.keysym}>' in self.key_to_command_current:
            self.key_to_command_current[f'<{event.keysym}>']()
        else:
            pass
