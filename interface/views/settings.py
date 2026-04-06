import tkinter as tk
from tkinter.filedialog import askdirectory
import source.core as core
import source.shared as shared


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

            # Add a "Browse" button for path settings
            btn_browse = shared.ReactiveButton(row, text="BROWSE", small=True,
                                               command=lambda k=setting_key: self._browse_path(k))
            btn_browse.pack(side="left")

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

    def _browse_path(self, key):
        """ Pure UI Interaction """
        path = askdirectory(title="Select Folder")
        if path:
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, path)

    def _save_settings(self):
        """ Collects UI data and hands it to the core logic. """
        new_settings = {}
        for key, entry in self.entries.items():
            new_settings[key] = entry.get()

        # Hand off to the core logic!
        core.state.raw_settings.save(new_settings)
        print("Settings Saved Successfully")
