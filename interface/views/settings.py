import tkinter as tk
from tkinter.filedialog import askdirectory

import source.core as core
import source.shared as shared
from source.constants import Setting


class SettingsView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=shared.APP_BACKGROUND_COLOR)
        self.controller = controller  # Reference to main window to swap views if needed

        # We store references to our entry fields to extract text later
        self.entries = {}

        title = tk.Label(self, text="Application Settings", bg=shared.APP_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0],
                         font=shared.FONT_TEXT)
        title.pack(anchor="w", pady=(0, 10))

        # We loop through the state to build the rows dynamically
        for setting_key in core.state.raw_settings:
            row = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
            row.pack(fill="x", pady=2)

            lbl = tk.Label(row, text=setting_key, width=20, anchor="w", bg=shared.APP_BACKGROUND_COLOR,
                           fg=shared.TEXT_COLORS[0])
            lbl.pack(side="left")

            entry = tk.Entry(row, bg=shared.ENTRY_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0])
            entry.pack(side="left", fill="x", expand=True, padx=5)
            self.entries[setting_key] = entry

            if setting_key in (Setting.LIBRARY, Setting.ARCHIVE):
                button_browse = shared.ReactiveButton(row, text="BROWSE TO CHANGE", small=True,
                                                      command=lambda k=setting_key: self._browse_path_replace(k))
                button_browse.pack(side="left")
            elif setting_key in (Setting.EXCEPTIONS, Setting.GAMES):
                button_browse = shared.ReactiveButton(row, text="BROWSE TO ADD", small=True,
                                                      command=lambda k=setting_key: self._browse_path_add(k))
                button_browse.pack(side="left")
            # TODO: allow changing the install path - cascading changes in other fields

        # Save Button
        btn_save = shared.ReactiveButton(self, text="SAVE SETTINGS", command=self._save_settings)
        btn_save.pack(pady=20)

    def on_show(self):
        """ Called by the Main Window automatically when this view is displayed. """
        self._populate_fields()

    def _populate_fields(self):
        """ Reads from core logic and fills the UI. """
        for key, entry in self.entries.items():
            entry.config(state="normal")
            entry.delete(0, tk.END)
            val = core.state.raw_settings.get(key, "")

            if isinstance(val, list):
                entry.insert(0, ", ".join(val))
            else:
                entry.insert(0, str(val))

    def _browse_path_replace(self, key):
        """ Pure UI Interaction """
        path = askdirectory(title="Select Folder")
        if path:
            formatted_path = core.state.make_path_relative(path)
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, formatted_path)

    def _browse_path_add(self, key):
        """ Pure UI Interaction """
        path = askdirectory(title="Select Folder")
        if path:
            formatted_path = core.state.make_path_relative(path)
            self.entries[key].insert(tk.END, f", {formatted_path}")

    def _save_settings(self):
        """ Collects UI data and hands it to the core logic. """
        new_settings = {}
        for key, entry in self.entries.items():
            entry_value = entry.get()
            if ', ' in entry_value:
                new_settings[key] = entry_value.split(', ')
            else:
                new_settings[key] = entry_value

        # Hand off to the core logic!
        core.state.save(new_settings)
        print("Settings Saved Successfully")

    def _has_unsaved_changes(self) -> bool:
        """ Compares current UI values against the saved core state. """
        for key, entry in self.entries.items():
            current_ui_val = entry.get().strip()
            saved_val = core.state.raw_settings.get(key, "")

            # Format the saved value exactly how it appears in the UI
            if isinstance(saved_val, list):
                saved_val_str = ", ".join(saved_val)
            else:
                saved_val_str = str(saved_val)

            if current_ui_val != saved_val_str:
                return True
        return False

    def confirm_leave(self) -> bool:
        """ Called by the main controller before navigating away. """
        if self._has_unsaved_changes():
            answer = shared.invoke_choice(
                title='Unsaved Settings',
                text='You have unsaved changes in your settings.\nDo you want to save them before leaving?',
                buttons=({shared.KEY_LABEL: 'Yes', shared.KEY_RETURN: 'yes', shared.KEY_INFO: ''},
                         {shared.KEY_LABEL: 'No', shared.KEY_RETURN: 'no', shared.KEY_INFO: ''},
                         {shared.KEY_LABEL: 'Cancel', shared.KEY_RETURN: 'cancel', shared.KEY_INFO: ''})
            )

            if answer == 'yes':
                self._save_settings()
                return True  # Saved successfully, safe to leave
            elif answer == 'no':
                # Revert UI to saved state so they aren't lingering if we return
                self._populate_fields()
                return True  # User doesn't care, safe to leave
            else:
                return False  # User cancelled, DO NOT LEAVE

        return True  # No changes, safe to leave
