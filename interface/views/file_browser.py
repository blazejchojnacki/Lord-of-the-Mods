import os
import tkinter as tk
from tkinter import ttk

from source.messaging import InternalError
import source.shared as s
from source.constants import MOD_DEF_FILE_NAME
from source.constructor import load_directories


class FileBrowserView(tk.Frame):
    """ The View responsible for navigating directories and selecting files to edit or move. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=s.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.current_path = ""

        self._build_ui()

    def _build_ui(self):
        """ Constructs the browser layout. """
        # --- Top Section: Navigation Bar ---
        frame_nav = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_nav.pack(fill="x", pady=(0, 5))

        self.btn_back = s.ReactiveButton(frame_nav, text="🡄 BACK", small=True, command=self._on_back)
        self.btn_back.pack(side="left", padx=(0, 10))

        self.lbl_path = tk.Label(frame_nav, text="Path: ", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                 font=s.FONT_TEXT)
        self.lbl_path.pack(side="left", fill="x", expand=True, anchor="w")

        # --- Middle Section: The Directory List ---
        frame_list = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_list.pack(fill="both", expand=True)

        # Add a scrollbar to the listbox (a massive usability upgrade!)
        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            frame_list,
            bg=s.ENTRY_BACKGROUND_COLOR,
            fg=s.TEXT_COLORS[0],
            font=s.FONT_TEXT,
            selectbackground=s.TEXT_COLORS[0],
            selectforeground=s.TEXT_COLORS[-1],
            yscrollcommand=scrollbar.set
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Bindings for navigation
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        self.listbox.bind('<Double-1>', self._on_forward)
        self.bind_all('<BackSpace>', self._on_back_key)  # Bind backspace to go up a folder

        # --- Bottom Section: Action Buttons ---
        self.frame_buttons = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        self.frame_buttons.pack(fill="x", pady=10)

        self.btn_open = s.ReactiveButton(self.frame_buttons, text="OPEN", command=self._on_forward)
        self.btn_open.pack(side="left", padx=5)

        self.btn_move = s.ReactiveButton(self.frame_buttons, text="MOVE FILE", command=self._on_move)
        # We start with the move button hidden until a file is selected
        self.btn_move.pack_forget()

    def load_path(self, target_path: str):
        """ Called by the controller to point the browser at a specific directory. """
        if not os.path.isdir(target_path):
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Error: {target_path} is not a valid directory.")
            return

        self.current_path = target_path.replace('\\', '/')
        self.lbl_path.configure(text=f"Path: {os.path.abspath(self.current_path)}")
        self._refresh_directory()

        # Reset button states
        self.btn_open.configure(state="normal", text="OPEN")
        self.btn_move.pack_forget()

    def _refresh_directory(self):
        """ Fetches folder contents and populates the listbox with colored text. """
        self.listbox.delete(0, tk.END)

        try:
            # Using the existing logic helper from constructor.py
            output_folders, output_files = load_directories(self.current_path)

            item_index = 0

            # Insert Folders (Color 1)
            for folder in output_folders:
                self.listbox.insert(item_index, folder)
                self.listbox.itemconfig(item_index, foreground=s.INI_LEVEL_COLORS[1])
                item_index += 1

            # Insert Files (Color 2 for text, Color 3 for INI)
            for file in output_files:
                self.listbox.insert(item_index, file)
                color = s.INI_LEVEL_COLORS[3] if file.endswith('.ini') else s.INI_LEVEL_COLORS[2]
                self.listbox.itemconfig(item_index, foreground=color)
                item_index += 1

            # Auto-select the first item if the folder isn't empty
            if output_folders or output_files:
                self.listbox.selection_set(0)
                self.listbox.activate(0)
                self._on_select()

        except InternalError as error:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(error.message)

    def _on_select(self, event=None):
        """ Triggered when clicking an item. Updates button states based on selection type. """
        selection = self.listbox.curselection()
        if not selection:
            return

        item_name = self.listbox.get(selection[0])
        full_item_path = f"{self.current_path}/{item_name}"

        if os.path.isdir(full_item_path):
            self.btn_open.configure(text="OPEN FOLDER", state="normal")
            self.btn_move.pack_forget()

        elif os.path.isfile(full_item_path):
            # Restrict opening functional files or archives in the text editor
            if item_name == MOD_DEF_FILE_NAME or item_name.endswith('.big'):
                self.btn_open.configure(text="CANNOT OPEN FILE", state="disabled")
            else:
                self.btn_open.configure(text="OPEN FILE", state="normal")

            self.btn_move.pack(side="left", padx=5)

    def _on_forward(self, event=None):
        """ Opens the selected folder or file. """
        selection = self.listbox.curselection()
        if not selection:
            return

        item_name = self.listbox.get(selection[0])
        full_item_path = f"{self.current_path}/{item_name}"

        if os.path.isdir(full_item_path):
            # Navigate deeper
            self.load_path(full_item_path)

        elif os.path.isfile(full_item_path):
            # Do not open restricted files
            if item_name == MOD_DEF_FILE_NAME or item_name.endswith('.big'):
                return

            # Hand the file off to the controller to open the File Editor View!
            if hasattr(self.controller, 'open_file_editor'):
                self.controller.open_file_editor(full_item_path)

    def _on_back(self):
        """ Navigates one directory up. """
        parent_path = os.path.dirname(self.current_path)

        # If we reached a root drive or the highest allowed level, return to Mod Manager
        if parent_path == self.current_path or len(parent_path) < 3:
            if hasattr(self.controller, 'show_frame'):
                self.controller.show_frame("ModManagerView")
        else:
            self.load_path(parent_path)

    def _on_back_key(self, event):
        """ Wrapper to handle the BackSpace key binding safely. """
        # Only navigate back if the browser is currently visible
        if self.winfo_ismapped():
            self._on_back()

    def _on_move(self):
        """ Routes the user to the Move File View. """
        selection = self.listbox.curselection()
        if not selection: return

        item_name = self.listbox.get(selection[0])
        full_item_path = f"{self.current_path}/{item_name}"

        if hasattr(self.controller, 'open_move_file_view'):
            self.controller.open_move_file_view(full_item_path)
