import os
import tkinter as tk
from tkinter import ttk
from dataclasses import fields

from source.messaging import log, InternalError
import source.core as core
import source.shared as s
from source.constants import Property, MOD_DEF_FILE_NAME, Setting
from models.mod import Mod, LibraryManager

MOD_COLUMNS = {Property.NAME: 1, Property.TRANSFER_TYPE: 1, Property.DESCRIPTION: 5}


class ColumnedListbox(ttk.Treeview):
    """ A Tk/Tcl Treeview-based class with predefined columns. """

    def __init__(self, master, width=s.LIST_WIDTH, height=s.UNIT_HEIGHT * 3, columns_dict=None, show='tree headings'):
        super().__init__(master=master, height=height, show=show)
        self.width = width * 6
        if columns_dict:
            self.set_columns(columns_dict)

    def set_columns(self, columns_dict):
        self.configure(columns=list(columns_dict.keys()))
        total_quotient = sum(list(columns_dict.values()), 1)
        column_unit_width = int(self.width / total_quotient)
        self.column('#0', width=column_unit_width)
        for column_name in columns_dict:
            self.heading(column_name, text=column_name)
            self.column(column_name, width=column_unit_width * columns_dict[column_name])

    def open_children(self):
        for search_index in range(10):
            self.open_children_recursive(parent=str(search_index))

    def open_children_recursive(self, parent):
        try:
            self.item(parent, open=True)
            for child in self.get_children(parent):
                self.open_children_recursive(child)
        except tk.TclError:
            pass


class ModManagerView(tk.Frame):
    """ The View responsible for displaying and managing active and idle mods. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=s.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.global_mods = []
        self.loaded_mod = None

        self._build_ui()

    def _build_ui(self):
        """ Constructs the layout using fluid packing. """
        # --- Top Section: Idle Mods ---
        frame_idle = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_idle.pack(fill="both", expand=True, pady=(0, 5))

        lbl_idle = tk.Label(frame_idle, text="available mods:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                            font=s.FONT_TEXT)
        lbl_idle.pack(anchor="w")

        self.tree_idle = ColumnedListbox(frame_idle, width=s.LIST_WIDTH, height=8, columns_dict=MOD_COLUMNS)
        self.tree_idle.pack(fill="both", expand=True)
        self.tree_idle.bind('<<TreeviewSelect>>', self._on_select_idle)
        self.tree_idle.bind('<Double-1>', self._on_double_click)

        # --- Middle Section: Action Buttons ---
        self.frame_buttons = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        self.frame_buttons.pack(fill="x", pady=10)

        # We pre-create all buttons, but only pack the ones relevant to the selection
        self.btn_new = s.ReactiveButton(self.frame_buttons, text='NEW MOD', command=self._on_new_mod)
        self.btn_attach = s.ReactiveButton(self.frame_buttons, text='ATTACH MOD', command=self._on_attach)
        self.btn_detach = s.ReactiveButton(self.frame_buttons, text='DETACH MOD', command=self._on_detach)
        self.btn_reload = s.ReactiveButton(self.frame_buttons, text='RELOAD MOD', command=self._on_reload)
        self.btn_browse = s.ReactiveButton(self.frame_buttons, text='OPEN MOD', command=self._on_browse)
        self.btn_edit = s.ReactiveButton(self.frame_buttons, text='EDIT MOD DATA', command=self._on_edit)
        self.btn_launch = s.ReactiveButton(self.frame_buttons, text='LAUNCH', command=self._on_launch)

        # New Mod is always visible
        self.btn_new.pack(side="left", padx=5)

        # --- Bottom Section: Active Mods ---
        frame_active = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_active.pack(fill="both", expand=True, pady=(5, 0))

        lbl_active = tk.Label(frame_active, text="active mods:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                              font=s.FONT_TEXT)
        lbl_active.pack(anchor="w")

        self.tree_active = ColumnedListbox(frame_active, width=s.LIST_WIDTH, height=8, columns_dict=MOD_COLUMNS)
        self.tree_active.pack(fill="both", expand=True)
        self.tree_active.bind('<<TreeviewSelect>>', self._on_select_active)
        self.tree_active.bind('<Double-1>', self._on_double_click)

    def on_show(self):
        """ Called by the controller when this view is displayed to refresh data. """
        self._refresh_lists()
        self._hide_context_buttons()

    def _hide_context_buttons(self):
        """ Hides context-sensitive buttons until a mod is clicked. """
        for btn in [self.btn_attach, self.btn_detach, self.btn_reload, self.btn_browse, self.btn_edit, self.btn_launch]:
            btn.pack_forget()

    def _refresh_lists(self):
        """ Fetches mod data from the logic layer and populates the trees. """
        self.global_mods.clear()

        # 1. Check for missing definitions
        try:
            library_folders = [_ for _ in os.listdir(core.state.library) if _ not in core.state.exceptions]
            for folder in library_folders:
                if not os.path.isfile(f'{core.state.library}/{folder}/{MOD_DEF_FILE_NAME}'):
                    if hasattr(self.controller, 'set_log_update'):
                        self.controller.set_log_update(f'Detected a definition-less folder: {folder}')

                    # Restored popup logic!
                    do_initiate = s.invoke_choice(
                        title='Unregistered Folder',
                        text=f'The folder {core.state.library}/{folder}\nseems to have no properties.\n'
                             'Do you wish it to become a mod?\n',
                        buttons=({s.KEY_LABEL: 'yes', s.KEY_RETURN: True, s.KEY_INFO: ''},
                                 {s.KEY_LABEL: 'no', s.KEY_RETURN: False, s.KEY_INFO: ''})
                    )

                    if do_initiate:
                        # Route directly to the New Mod view and pass the folder name
                        if hasattr(self.controller, 'open_new_mod_view'):
                            self.controller.open_new_mod_view(preset_name=folder)
                        return  # Stop refreshing and jump to the new screen

                    elif do_initiate is False:
                        core.state.add_to_list(Setting.EXCEPTIONS, folder)
                        log.info(f"added {folder} to exceptions")
        except InternalError as err:
            log.error(err.message)

        # 2. Populate Active Mods
        self.tree_active.delete(*self.tree_active.get_children())
        active_mods = LibraryManager.select_mods(**{Property.ACTIVE: True})
        active_parent_dict = LibraryManager.sort_mods(mods=active_mods)

        for mod in active_mods:
            self.global_mods.append(mod)
            values = tuple(getattr(mod, field.name) for field in fields(mod) if field.name in MOD_COLUMNS)
            self.tree_active.insert('', index=active_mods.index(mod), iid=str(active_mods.index(mod)), values=values)

        for mod in active_mods:
            if mod.name in active_parent_dict:
                try:
                    self.tree_active.move(str(active_mods.index(mod)), str(active_parent_dict[mod.name]), 0)
                except tk.TclError:
                    pass
        self.tree_active.open_children()

        # 3. Populate Idle Mods
        self.tree_idle.delete(*self.tree_idle.get_children())
        idle_mods = LibraryManager.select_mods(**{Property.ACTIVE: False})
        idle_parent_dict = LibraryManager.sort_mods(mods=idle_mods)

        for mod in idle_mods:
            self.global_mods.append(mod)
            values = tuple(getattr(mod, field.name) for field in fields(mod) if field.name in MOD_COLUMNS)
            self.tree_idle.insert('', index=idle_mods.index(mod), iid=str(idle_mods.index(mod)), values=values)

        for mod in idle_mods:
            if mod.name in idle_parent_dict:
                try:
                    self.tree_idle.move(str(idle_mods.index(mod)), str(idle_parent_dict[mod.name]), 0)
                except tk.TclError:
                    pass
        self.tree_idle.open_children()

    def _on_select_idle(self, event=None):
        """ Handles clicking a mod in the top list. """
        selection = self.tree_idle.selection()
        if not selection: return

        mod_name = self.tree_idle.item(selection[0], 'values')[0]
        self.loaded_mod = LibraryManager.select_mods(**{Property.NAME: mod_name})[0]

        # Deselect active tree
        if self.tree_active.selection():
            self.tree_active.selection_remove(self.tree_active.selection()[0])

        self._hide_context_buttons()
        self.btn_attach.pack(side="left", padx=5)
        self.btn_browse.pack(side="left", padx=5)
        self.btn_edit.pack(side="left", padx=5)

    def _on_select_active(self, event=None):
        """ Handles clicking a mod in the bottom list. """
        selection = self.tree_active.selection()
        if not selection: return

        mod_name = self.tree_active.item(selection[0], 'values')[0]
        self.loaded_mod = LibraryManager.select_mods(**{Property.NAME: mod_name})[0]

        # Deselect idle tree
        if self.tree_idle.selection():
            self.tree_idle.selection_remove(self.tree_idle.selection()[0])

        self._hide_context_buttons()
        self.btn_detach.pack(side="left", padx=5)
        self.btn_reload.pack(side="left", padx=5)
        self.btn_browse.pack(side="left", padx=5)
        self.btn_edit.pack(side="left", padx=5)

        if self.loaded_mod.launch:
            self.btn_launch.pack(side="left", padx=5)

    def _on_double_click(self, event=None):
        if self.loaded_mod:
            self._on_browse()

    # --- Routing Methods to Controller or Logic ---

    def _on_new_mod(self):
        if hasattr(self.controller, 'open_new_mod_view'):
            self.controller.open_new_mod_view()

    def _on_attach(self):
        if not self.loaded_mod: return
        try:
            # Here we just ask the logic layer to do it!
            if self.loaded_mod.attach():
                if hasattr(self.controller, 'set_log_update'):
                    self.controller.set_log_update(f"Attached {self.loaded_mod.name}")
            self._refresh_lists()
        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)

    def _on_detach(self):
        if not self.loaded_mod: return
        try:
            if self.loaded_mod.retrieve():
                if hasattr(self.controller, 'set_log_update'):
                    self.controller.set_log_update(f"Detached {self.loaded_mod.name}")
            self._refresh_lists()
        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)

    def _on_reload(self):
        if not self.loaded_mod: return
        try:
            if self.loaded_mod.reload():
                self._refresh_lists()
        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)

    def _on_browse(self):
        # Route the browser request to the main controller
        if hasattr(self.controller, 'open_browser_for_mod'):
            self.controller.open_browser_for_mod(self.loaded_mod)

    def _on_edit(self):
        if hasattr(self.controller, 'open_mod_editor'):
            # Tell the main app to open the editor FOR this specific mod!
            self.controller.open_mod_editor(self.loaded_mod)

    def _on_launch(self):
        # The logic implementation from interface.py
        pass
