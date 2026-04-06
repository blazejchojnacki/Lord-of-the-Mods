import os
import tkinter as tk
from tkinter.filedialog import askdirectory

from source.messaging import InternalError
import source.shared as shared
from source.constants import PROGRAM_NAME
from source.editor import move_file


class MoveFileView(tk.Frame):
    """ The View responsible for safely moving a file and updating its references. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=shared.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.source_file_path = ""

        self._build_ui()

    def on_show(self):
        if hasattr(self.controller, 'set_log_update'):
            self.controller.set_log_update("File mover loaded")

    def _build_ui(self):
        # --- Navigation ---
        frame_top = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_top.pack(fill="x", pady=(0, 10))

        btn_back = shared.ReactiveButton(frame_top, text="🡄 BACK TO BROWSER", small=True, command=self._on_back)
        btn_back.pack(side="left", padx=(0, 10))

        tk.Label(frame_top, text="Move File Tool", bg=shared.APP_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0],
                 font=shared.FONT_TEXT).pack(side="left")

        # --- The Form ---
        frame_form = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_form.pack(fill="x", padx=10, pady=20)
        frame_form.columnconfigure(1, weight=1)

        # File to Move
        tk.Label(frame_form, text="File to move:", bg=shared.APP_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0], anchor="e"
                 ).grid(row=0, column=0, sticky="e", pady=5, padx=5)
        self.lbl_source = tk.Label(frame_form, text="", bg=shared.ENTRY_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0],
                                   anchor="w", relief="sunken")
        self.lbl_source.grid(row=0, column=1, sticky="we", pady=5, padx=5)

        # Destination Folder
        tk.Label(frame_form, text="To Folder:", bg=shared.APP_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0], anchor="e"
                 ).grid(row=1, column=0, sticky="e", pady=5, padx=5)
        self.entry_dest = tk.Entry(frame_form, bg=shared.ENTRY_BACKGROUND_COLOR, fg=shared.TEXT_COLORS[0],
                                   font=shared.FONT_TEXT)
        self.entry_dest.grid(row=1, column=1, sticky="we", pady=5, padx=5)

        shared.ReactiveButton(frame_form, text="BROWSE", small=True, command=self._browse_dest
                              ).grid(row=1, column=2, padx=5)

        # --- Action ---
        btn_move = shared.ReactiveButton(self, text="MOVE FILE", command=self._on_move)
        btn_move.pack(pady=10)

    def load_file_to_move(self, filepath: str):
        """ Called by the controller when routing from the File Browser. """
        self.source_file_path = filepath.replace('\\', '/')
        self.lbl_source.configure(text=self.source_file_path)

        # Default destination to the current folder
        self.entry_dest.delete(0, tk.END)
        self.entry_dest.insert(0, os.path.dirname(self.source_file_path))

    def _browse_dest(self):
        initial = self.entry_dest.get() or "../"
        path = askdirectory(title=f"{PROGRAM_NAME}: Select Destination Folder", initialdir=initial)
        if path:
            self.entry_dest.delete(0, tk.END)
            self.entry_dest.insert(0, path.replace('\\', '/'))

    def _on_move(self):
        dest_folder = self.entry_dest.get().strip()
        if not dest_folder or not self.source_file_path:
            return

        try:
            # Call the pure logic!
            output = move_file(self.source_file_path, dest_folder)

            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(output)

            # Automatically send the user back to the browser looking at the new folder
            if hasattr(self.controller, 'open_browser_at_path'):
                self.controller.open_browser_at_path(dest_folder)

        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)

    def _on_back(self):
        if hasattr(self.controller, 'navigate_back'):
            self.controller.navigate_back()
