import os
import shutil
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilenames

import source.core as core
import source.shared as shared
from source.constants import Change, PROGRAM_NAME
from source.modificator import hash_file
from models.mod import Mod


class ChangeEditorView(tk.Frame):
    """ The View responsible for staging, modifying, and applying file changes to a Mod. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=shared.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.loaded_mod = None
        self.new_changes = {}  # Dictionary to hold staged changes before saving

        self._build_ui()
        self._build_context_menu()

    def _build_ui(self):
        """ Constructs the dual-list layout for current and staged changes. """
        # --- Top Section: Navigation ---
        frame_top = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_top.pack(fill="x", pady=(0, 10))

        btn_back = shared.ReactiveButton(frame_top, text="🡄 BACK TO MOD EDITOR", small=True, command=self._on_back)
        btn_back.pack(side="left", padx=(0, 10))

        self.lbl_title = tk.Label(frame_top, text="Changes Editor", bg=shared.APP_BACKGROUND_COLOR,
                                  fg=shared.TEXT_COLORS[0], font=shared.FONT_TEXT)
        self.lbl_title.pack(side="left", fill="x", expand=True, anchor="w")

        # --- Middle Section: Current Changes ---
        frame_current = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_current.pack(fill="both", expand=True, pady=5)

        tk.Label(frame_current, text="Current Mod Changes:", bg=shared.APP_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0],
                 font=shared.FONT_TEXT).pack(anchor="w")

        self.tree_current = self._create_treeview(frame_current)
        self.tree_current.pack(fill="both", expand=True)

        # --- Lower Middle Section: Staged/New Changes ---
        frame_staged = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_staged.pack(fill="both", expand=True, pady=5)

        tk.Label(frame_staged, text="Staged Changes (Unsaved):", bg=shared.APP_BACKGROUND_COLOR,
                 fg=shared.TEXT_COLORS[0], font=shared.FONT_TEXT).pack(anchor="w")

        self.tree_staged = self._create_treeview(frame_staged)
        self.tree_staged.pack(fill="both", expand=True)

        # --- Bottom Section: Actions ---
        frame_actions = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_actions.pack(fill="x", pady=10)

        # Left side actions (Adding files)
        shared.ReactiveButton(frame_actions, text="ADD FILE(S)", command=self._on_add_files).pack(side="left", padx=5)
        shared.ReactiveButton(frame_actions, text="COPY FILE(S)", command=self._on_copy_files).pack(side="left", padx=5)

        # Center actions (Modifying selection)
        shared.ReactiveButton(frame_actions, text="DELETE SELECTED", command=self._on_delete).pack(side="left", padx=20)
        shared.ReactiveButton(frame_actions, text="CHANGE TYPE",
                              info_content="Change whether file is Added, Removed, etc.",
                              command=self._on_change_type_btn).pack(side="left", padx=5)

        # Right side actions (Applying)
        shared.ReactiveButton(frame_actions, text="APPLY STAGED CHANGES",
                              command=self._on_apply_changes).pack(side="right", padx=5)
        shared.ReactiveButton(frame_actions, text="OPEN FILE", command=self._on_open_file).pack(side="right", padx=5)

    def _create_treeview(self, parent_frame) -> ttk.Treeview:
        """ Helper to build a consistent Treeview with a scrollbar. """
        scroll = tk.Scrollbar(parent_frame)
        scroll.pack(side="right", fill="y")

        tree = ttk.Treeview(parent_frame, columns=("path", "type"), show="headings", yscrollcommand=scroll.set,
                            height=6)
        tree.heading("path", text="File Path")
        tree.heading("type", text="Change Type")
        tree.column("path", width=600)
        tree.column("type", width=100, anchor="center")

        scroll.config(command=tree.yview)

        # Bind double click / right click for the context menu
        tree.bind("<Double-1>", self._on_double_click)
        tree.bind("<Button-3>", self._on_right_click)  # Right click on Windows/Linux

        return tree

    def _build_context_menu(self):
        """ Builds a native popup menu for selecting the Change Enum type. """
        self.type_menu = tk.Menu(self, tearoff=0, bg=shared.ENTRY_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0])

        # Add a command for each Change enum
        for change_type in Change:
            self.type_menu.add_command(
                label=change_type,
                command=lambda ct=change_type: self._apply_type_change(ct)
            )

    def load_mod_data(self, mod: Mod):
        """ Injects the mod data into the view. """
        self.loaded_mod = mod
        self.new_changes = {}  # Reset staged changes
        self.lbl_title.configure(text=f"Changes Editor: {mod.name}")
        self._refresh_trees()

    def _refresh_trees(self):
        """ Clears and repopulates both treeviews. """
        # Clear current
        for item in self.tree_current.get_children():
            self.tree_current.delete(item)

        # Clear staged
        for item in self.tree_staged.get_children():
            self.tree_staged.delete(item)

        if not self.loaded_mod:
            return

        # Populate Current
        for file_path, change_data in self.loaded_mod.changes.items():
            self.tree_current.insert("", "end", iid=f"current|{file_path}", values=(file_path, change_data[0]))

        # Populate Staged
        for file_path, change_data in self.new_changes.items():
            self.tree_staged.insert("", "end", iid=f"staged|{file_path}", values=(file_path, change_data[0]))

    # --- Action Implementations ---

    def _on_add_files(self):
        """ Stages existing files as changed. """
        mod_path = f"{core.state.library}/{self.loaded_mod.name}".replace('\\', '/')
        paths = askopenfilenames(title=f"{PROGRAM_NAME}: Select File(s) to track", initialdir=mod_path)

        for path in paths:
            clean_path = path.replace('\\', '/')
            hash_value = hash_file(clean_path)

            # Make path relative to mod directory if it's inside it
            if mod_path in clean_path:
                clean_path = clean_path[len(mod_path) + 1:]

            self.new_changes[clean_path] = [Change.CHANGED, hash_value]

        self._refresh_trees()

    def _on_copy_files(self):
        """ Copies external files into the mod and stages them. """
        mod_path = f"{core.state.library}/{self.loaded_mod.name}".replace('\\', '/')
        install_path = core.state.install_path.replace('\\', '/')

        paths = askopenfilenames(title=f"{PROGRAM_NAME}: Copy File(s) to Mod", initialdir=install_path)

        for path in paths:
            clean_path = path.replace('\\', '/')

            if install_path in clean_path and mod_path not in clean_path:
                # Calculate relative path
                rel_path = clean_path[len(install_path):].strip('/')
                target_dir = f"{mod_path}/{os.path.dirname(rel_path)}"

                # Copy the file
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(src=clean_path, dst=f"{mod_path}/{rel_path}")

                # Stage the change
                hash_value = hash_file(f"{mod_path}/{rel_path}")
                self.new_changes[rel_path] = [Change.CHANGED, hash_value]
            else:
                if hasattr(self.controller, 'set_log_update'):
                    self.controller.set_log_update(f"File {clean_path} skipped (must be inside game directory).")

        self._refresh_trees()

    def _on_delete(self):
        """ Removes selected files from their respective dictionaries. """
        # Handle Current Selection
        current_selection = self.tree_current.selection()
        if current_selection:
            for item in current_selection:
                file_path = self.tree_current.item(item, "values")[0]
                if file_path in self.loaded_mod.changes:
                    del self.loaded_mod.changes[file_path]
            # Save the underlying mod
            self.loaded_mod.edit(changes=self.loaded_mod.changes)

        # Handle Staged Selection
        staged_selection = self.tree_staged.selection()
        if staged_selection:
            for item in staged_selection:
                file_path = self.tree_staged.item(item, "values")[0]
                if file_path in self.new_changes:
                    del self.new_changes[file_path]

        self._refresh_trees()

    def _on_apply_changes(self):
        """ Merges staged changes into the mod and saves. """
        if not self.new_changes:
            return

        self.loaded_mod.changes.update(self.new_changes)
        self.loaded_mod.edit(changes=self.loaded_mod.changes)

        self.new_changes = {}  # Clear staging area
        self._refresh_trees()

        if hasattr(self.controller, 'set_log_update'):
            self.controller.set_log_update(f"Applied changes to {self.loaded_mod.name}")

    def _on_open_file(self):
        """ Routes the selected file to the File Editor View. """
        selection = self._get_active_selection()
        if not selection:
            return

        file_path = selection[0]
        # Calculate full path based on whether mod is active
        if self.loaded_mod.active:
            full_path = f"{core.state.install_path}/{file_path}"
        else:
            full_path = f"{core.state.library}/{self.loaded_mod.name}/{file_path}"

        if hasattr(self.controller, 'open_file_editor'):
            self.controller.open_file_editor(full_path)

    # --- Type Changing (Context Menu) Logic ---

    def _get_active_selection(self) -> tuple:
        """ Helper to find which tree has a selection and return the file path and tree identifier. """
        if self.tree_current.selection():
            item = self.tree_current.selection()[0]
            return self.tree_current.item(item, "values")[0], "current"
        if self.tree_staged.selection():
            item = self.tree_staged.selection()[0]
            return self.tree_staged.item(item, "values")[0], "staged"
        return None

    def _on_change_type_btn(self):
        """ Triggered by the button. Spawns menu near the mouse. """
        x = self.winfo_pointerx()
        self.type_menu.post(x, self.winfo_pointery())

    def _on_right_click(self, event):
        """ Spawns menu exactly where the user right-clicked. """
        self.type_menu.post(event.x_root, event.y_root)

    def _on_double_click(self, event):
        """ A fallback in case user double clicks to change type. """
        self._on_right_click(event)

    def _apply_type_change(self, new_type: str):
        """ Modifies the dictionary data based on the dropdown selection. """
        selection = self._get_active_selection()
        if not selection:
            return

        file_path, source_tree = selection

        if source_tree == "current":
            self.loaded_mod.changes[file_path][0] = new_type
            # We don't automatically save to disk here; user must decide when to save if we wanted to be cautious.
            # But in the old logic, updating 'current' implied an immediate underlying update, so we'll save it:
            self.loaded_mod.edit(changes=self.loaded_mod.changes)
        elif source_tree == "staged":
            self.new_changes[file_path][0] = new_type

        self._refresh_trees()

    # --- Navigation ---

    def _on_back(self):
        """ Returns to the Mod Editor. """
        if self.new_changes:
            answer = shared.invoke_choice(
                title='Unsaved Changes',
                text='You have staged changes that are not applied.\nDo you want to apply them now?',
                buttons=({shared.KEY_LABEL: 'Yes', shared.KEY_RETURN: True, shared.KEY_INFO: ''},
                         {shared.KEY_LABEL: 'No', shared.KEY_RETURN: False, shared.KEY_INFO: ''},
                         {shared.KEY_LABEL: 'Cancel', shared.KEY_RETURN: None, shared.KEY_INFO: ''})
            )
            if answer is True:
                self._on_apply_changes()
            elif answer is None:
                return  # Abort navigation

        if hasattr(self.controller, 'open_mod_editor'):
            self.controller.open_mod_editor(self.loaded_mod)
