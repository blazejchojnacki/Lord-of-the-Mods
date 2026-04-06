import os
import tkinter as tk
from tkinter import ttk

import source.shared as shared
from source.shared import load_aesthetic, ReactiveButton
from source.constants import PROGRAM_NAME
from models.mod import Mod

from interface.views.mod_manager import ModManagerView
from interface.views.settings import SettingsView
from interface.views.mod_editor import ModEditorView
from interface.views.file_browser import FileBrowserView
from interface.views.file_editor import FileEditorView
from interface.views.find_replace import FindReplaceView
from interface.views.change_editor import ChangeEditorView
from interface.views.move_file import MoveFileView
from interface.views.new_mod import NewModView


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        # Setup aesthetic defaults
        load_aesthetic()
        self.title(PROGRAM_NAME)
        if os.path.isfile(shared.ICON_PATH):
            self.iconbitmap(shared.ICON_PATH)
        self.geometry("1250x650")
        self.configure(bg=shared.APP_BACKGROUND_COLOR)
        self._apply_ttk_styles()

        # Build the Navigation Header
        self._build_header()

        # This is the master container where screens will be loaded
        self.main_container = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.last_view = ''

        # Dictionary to cache our views so we don't rebuild them every click
        self.frames = {}

        # Load the default view
        self.show_frame("ModManagerView")

    def _apply_ttk_styles(self):
        """ Restores the dark mode/custom Treeview styling. """
        style = ttk.Style(self)

        # 'clam' theme allows for deep color customization
        style.theme_use('clam')

        # Base ttk style
        style.configure(
            '.',
            font=shared.FONT_TEXT,
            foreground=shared.TEXT_COLORS[0],
            background=shared.ENTRY_BACKGROUND_COLOR
        )

        # Treeview (Listbox body) style
        style.configure(
            'Treeview',
            background=shared.ENTRY_BACKGROUND_COLOR,
            fieldbackground=shared.ENTRY_BACKGROUND_COLOR,
            fieldbw=0,
            selectbackground=shared.TEXT_COLORS[0],
            selectforeground=shared.TEXT_COLORS[-1]
        )

        # Treeview Headers style
        style.configure(
            'Treeview.Heading',
            borderwidth=0,
            background=shared.APP_BACKGROUND_COLOR,
            foreground=shared.TEXT_COLORS[0]
        )

        # Hover effects for headers
        style.map(
            'Treeview.Heading',
            background=[('active', shared.TEXT_COLORS[0])],
            foreground=[('active', shared.TEXT_COLORS[-1])]
        )

    def _build_header(self):
        """ Builds a permanent navigation bar at the top of the window. """
        header = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        header.pack(fill="x", padx=10, pady=(10, 0))

        btn_mods = ReactiveButton(header, text="MODS", command=lambda: self.show_frame("ModManagerView"))
        btn_mods.pack(side="left", padx=(0, 5))

        btn_settings = ReactiveButton(header, text="SETTINGS", command=lambda: self.show_frame("SettingsView"))
        btn_settings.pack(side="left")

    def show_frame(self, page_name: str):
        """ Swaps the currently visible screen. """
        # Hide all existing frames
        for frame in self.frames.values():
            frame.pack_forget()

        # If we haven't built this view yet, build it and cache it!
        if page_name not in self.frames:
            if page_name == "ModManagerView":
                self.frames[page_name] = ModManagerView(self.main_container, self)
            elif page_name == "SettingsView":
                self.frames[page_name] = SettingsView(self.main_container, self)

        # Show the requested frame
        frame = self.frames[page_name]
        frame.pack(fill="both", expand=True)

        # Tell the view it just became active so it can refresh its data
        if hasattr(frame, "on_show"):
            frame.on_show()

    def open_mod_editor(self, mod: Mod):
        # 1. Ensure the view exists
        if "ModEditorView" not in self.frames:
            self.frames["ModEditorView"] = ModEditorView(self.main_container, self)

        # 2. Inject the data!
        self.frames["ModEditorView"].load_mod_data(mod)

        # 3. Swap the screen
        self.show_frame("ModEditorView")

    def open_browser_for_mod(self, mod: Mod):
        # Determine the correct starting path based on the logic from old interface.py
        # You can port over the `command_mod_browse` path calculation logic here
        target_path = mod.directory  # Simplified example

        if "FileBrowserView" not in self.frames:
            self.frames["FileBrowserView"] = FileBrowserView(self.main_container, self)

        # Point the browser at the folder!
        self.frames["FileBrowserView"].load_path(target_path)
        self.show_frame("FileBrowserView")

    def open_file_editor(self, filepath: str):
        if "FileEditorView" not in self.frames:
            self.frames["FileEditorView"] = FileEditorView(self.main_container, self)

        # Push the path to the view!
        self.frames["FileEditorView"].load_file_path(filepath)
        self.show_frame("FileEditorView")

    def open_find_tool(self, selection: str, filepath: str):
        """ Routes from File Editor to Find tool. """
        if "FindReplaceView" not in self.frames:
            self.frames["FindReplaceView"] = FindReplaceView(self.main_container, self)

        self.frames["FindReplaceView"].load_context(selection, filepath)

        # Save history so we know where to go back to!
        self.last_view = "FileEditorView"
        self.show_frame("FindReplaceView")

    def open_replace_tool(self, selection: str, filepath: str):
        """ Routes from File Editor to Replace tool (they now share a view!). """
        self.open_find_tool(selection, filepath)

    def reload_file_editor(self, scope: str):
        """ Called by FindReplace when a file is modified externally. """
        if "FileEditorView" in self.frames:
            # We check if the editor is currently looking at the file we just changed
            if self.frames["FileEditorView"].current_path.replace('/', '\\') == scope.replace('/', '\\'):
                self.frames["FileEditorView"].load_file_path(scope)

    def navigate_back(self):
        """ Returns to the previous screen. """
        if hasattr(self, 'last_view') and self.last_view:
            self.show_frame(self.last_view)
        else:
            self.show_frame("ModManagerView")  # Safe fallback

    def show_changes_for_mod(self, mod: Mod):
        """ Routes from Mod Editor to the Change Editor. """
        if "ChangeEditorView" not in self.frames:
            self.frames["ChangeEditorView"] = ChangeEditorView(self.main_container, self)

        # Push the mod data!
        self.frames["ChangeEditorView"].load_mod_data(mod)
        self.show_frame("ChangeEditorView")

    def open_move_file_view(self, filepath: str):
        if "MoveFileView" not in self.frames:
            self.frames["MoveFileView"] = MoveFileView(self.main_container, self)

        self.frames["MoveFileView"].load_file_to_move(filepath)
        self.last_view = "FileBrowserView"
        self.show_frame("MoveFileView")

    def open_browser_at_path(self, folderpath: str):
        if "FileBrowserView" in self.frames:
            self.frames["FileBrowserView"].load_path(folderpath)
            self.show_frame("FileBrowserView")

    def open_new_mod_view(self, preset_name: str = ""):
        """ Routes the user to the New Mod creation screen. """
        # 1. Instantiate it if it doesn't exist yet
        if "NewModView" not in self.frames:
            self.frames["NewModView"] = NewModView(self.main_container, self)

        # 2. Inject the preset name (if any)
        self.frames["NewModView"].load_preset_name(preset_name)

        # 3. Swap the screen!
        self.show_frame("NewModView")


if __name__ == "__main__":
    app = Application()
    app.mainloop()
