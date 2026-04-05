import os
import tkinter as tk
from tkinter import ttk

from source.messaging import InternalError
import source.core as core
import source.shared as s
from source.constants import Property, DEFINITION_TEMPLATE, DEFINITION_CLASSES, Change
from models.mod import Mod, LibraryManager


def count_files_recursive(path: str) -> int:
    """ Helper: Recursively counts files in a directory to display mod statistics. """
    if not os.path.isdir(path):
        return 0
    counter = 0
    for item in os.listdir(path):
        item_path = f'{path}/{item}'
        if os.path.isdir(item_path) and item != '.git':
            counter += count_files_recursive(item_path)
        elif os.path.isfile(item_path):
            counter += 1
    return counter


class ModEditorView(tk.Frame):
    """ The View responsible for editing a Mod's definition properties. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=s.APP_BACKGROUND_COLOR)
        self.controller = controller
        self.loaded_mod = None

        # Dictionary to store references to our input widgets
        self.inputs = {}

        self._build_ui()

    def _build_ui(self):
        """ Constructs the form layout. """
        # --- Top Section: Title & Actions ---
        frame_top = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_top.pack(fill="x", pady=(0, 10))

        self.lbl_title = tk.Label(frame_top, text="Mod Editor", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                  font=s.FONT_TEXT)
        self.lbl_title.pack(side="left")

        btn_back = s.ReactiveButton(frame_top, text="BACK TO MODS", command=self._on_back)
        btn_back.pack(side="right", padx=5)

        # --- Middle Section: The Form ---
        # We use a container Frame with a grid layout for perfect label/entry alignment
        self.frame_form = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        self.frame_form.pack(fill="both", expand=True)

        # Configure the grid to expand the input column
        self.frame_form.columnconfigure(1, weight=1)

        # Build the form dynamically based on DEFINITION_TEMPLATE
        for row_index, param_key in enumerate(DEFINITION_TEMPLATE):
            # Label
            lbl = tk.Label(self.frame_form, text=param_key, bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0], anchor="e")
            lbl.grid(row=row_index, column=0, sticky="e", padx=(0, 10), pady=5)

            # Changes and Description need larger Text boxes; everything else is a single-line Entry
            if param_key == Property.CHANGES:
                # Changes are read-only statistics in this view
                widget = tk.Text(self.frame_form, height=3, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                 font=s.FONT_TEXT)
                widget.grid(row=row_index, column=1, sticky="we", pady=5)
                self.inputs[param_key] = widget

            elif param_key == Property.DESCRIPTION:
                widget = tk.Text(self.frame_form, height=4, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                 font=s.FONT_TEXT)
                widget.grid(row=row_index, column=1, sticky="we", pady=5)
                self.inputs[param_key] = widget

            else:
                widget = tk.Entry(self.frame_form, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0], font=s.FONT_TEXT)
                widget.grid(row=row_index, column=1, sticky="we", pady=5)
                self.inputs[param_key] = widget

        # --- Bottom Section: Save & Advanced Actions ---
        frame_bottom = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_bottom.pack(fill="x", pady=15)

        btn_save = s.ReactiveButton(frame_bottom, text="SAVE PARAMETERS", command=self._on_save)
        btn_save.pack(side="left", padx=5)

        btn_changes = s.ReactiveButton(frame_bottom, text="SEE CHANGED FILES", command=self._on_see_changes)
        btn_changes.pack(side="left", padx=5)

    def load_mod_data(self, mod: Mod):
        """ Called by the controller BEFORE showing the frame to inject the target mod. """
        self.loaded_mod = mod
        self.lbl_title.configure(text=f"Editing: {mod.name}")
        self._populate_fields()

    def _populate_fields(self):
        """ Fills the form with the loaded mod's current data. """
        if not self.loaded_mod:
            return

        for param_key, widget in self.inputs.items():
            widget.configure(state="normal")

            # Clear existing text
            if isinstance(widget, tk.Entry):
                widget.delete(0, tk.END)
            else:
                widget.delete("1.0", tk.END)

            # Insert new text
            if param_key == Property.CHANGES:
                stats = self._generate_change_statistics()
                widget.insert("1.0", stats)
                widget.configure(state="disabled")  # Changes stats are read-only!

            else:
                value = getattr(self.loaded_mod, param_key, "")
                if isinstance(widget, tk.Entry):
                    widget.insert(0, str(value))
                else:
                    widget.insert("1.0", str(value))

                # Name and Active status cannot be edited via simple text fields
                if param_key in (Property.NAME, Property.ACTIVE):
                    widget.configure(state="disabled")

    def _generate_change_statistics(self) -> str:
        """ Generates the string summarizing file counts (migrated from old interface.py). """
        mod_path = f"{core.state.library}/{self.loaded_mod.name}"
        num_changes = len(self.loaded_mod.changes)
        num_removed = len([c for c in self.loaded_mod.changes.values() if c[0] == Change.REMOVED])
        files_present = count_files_recursive(mod_path)

        return f"mentioned: {num_changes} (removed: {num_removed}) | present in mod: {files_present}"

    def _on_save(self):
        """ Gathers the data from the form and updates the Mod object. """
        if not self.loaded_mod:
            return

        edited_parameters = {}

        for param_key, widget in self.inputs.items():
            # Skip read-only properties
            if param_key in (Property.CHANGES, Property.NAME, Property.ACTIVE):
                continue

            # Extract text safely depending on widget type
            if isinstance(widget, tk.Entry):
                value = widget.get().strip()
            else:
                value = widget.get("1.0", "end-1c").strip()

            # If the value changed, queue it for editing
            current_val = str(getattr(self.loaded_mod, param_key, ""))
            if value != current_val:
                edited_parameters[param_key] = value

        if not edited_parameters:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update("No changes detected.")
            return

        # Validate specific constraints (like transfer_type)
        if Property.TRANSFER_TYPE in edited_parameters:
            if edited_parameters[Property.TRANSFER_TYPE] not in DEFINITION_CLASSES:
                if hasattr(self.controller, 'set_log_update'):
                    self.controller.set_log_update(f"Error: Invalid Transfer Type. Must be one of {DEFINITION_CLASSES}")
                return

        try:
            # Delegate to the core logic!
            self.loaded_mod.edit(**edited_parameters)

            # Special case from old interface: reloading after transfer_type changes
            if Property.TRANSFER_TYPE in edited_parameters and self.loaded_mod.active:
                if hasattr(self.loaded_mod, 'reload_after_class_change'):
                    self.loaded_mod.reload_after_class_change()

            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Definition saved for {self.loaded_mod.name}.")

        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)

    def _on_see_changes(self):
        """ Routes the user to the ChangesView. """
        if hasattr(self.controller, 'show_changes_for_mod'):
            self.controller.show_changes_for_mod(self.loaded_mod)

    def _on_back(self):
        """ Routes the user back to the main Mod Manager. """
        if hasattr(self.controller, 'show_frame'):
            self.controller.show_frame("ModManagerView")
