import os
import tkinter as tk

from source.messaging import InternalError
import source.core as core
import source.shared as s
from models.mod import Mod


class NewModView(tk.Frame):
    """ The View responsible for creating a brand new Mod definition. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=s.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.source_var = tk.StringVar(value="nothing")
        self._build_ui()

    def _build_ui(self):
        # --- Navigation ---
        frame_top = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_top.pack(fill="x", pady=(0, 10))

        btn_back = s.ReactiveButton(frame_top, text="🡄 CANCEL", small=True, command=self._on_cancel)
        btn_back.pack(side="left", padx=(0, 10))

        tk.Label(frame_top, text="Create New Mod", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                 font=s.FONT_TEXT).pack(side="left")

        # --- The Form ---
        frame_form = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_form.pack(pady=30)

        # Mod Name
        tk.Label(frame_form, text="New Mod Name:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                 font=s.FONT_TEXT).pack(anchor="w")
        self.entry_name = tk.Entry(frame_form, width=40, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                   font=s.FONT_TEXT)
        self.entry_name.pack(pady=(0, 15))

        # Mod Source Options
        tk.Label(frame_form, text="It will be based on:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                 font=s.FONT_TEXT).pack(anchor="w")

        options = [
            ("Nothing (Empty Mod)", "nothing"),
            ("A present directory", "directory"),
            ("A comparison file", "comparison"),
            ("A snapshot file", "snapshot")
        ]

        for text, value in options:
            rb = tk.Radiobutton(
                frame_form,
                text=text,
                variable=self.source_var,
                value=value,
                bg=s.APP_BACKGROUND_COLOR,
                fg=s.TEXT_COLORS[0],
                selectcolor=s.ENTRY_BACKGROUND_COLOR,
                activebackground=s.APP_BACKGROUND_COLOR,
                activeforeground=s.TEXT_COLORS[0]
            )
            rb.pack(anchor="w", padx=10, pady=2)

        # --- Action ---
        btn_create = s.ReactiveButton(self, text="CREATE MOD", command=self._on_create)
        btn_create.pack(pady=20)

    def load_preset_name(self, name: str = ""):
        """ Sometimes the system prompts to create a mod from a detected folder. """
        self.entry_name.delete(0, tk.END)
        if name:
            self.entry_name.insert(0, name)
            self.source_var.set("directory")
        else:
            self.source_var.set("nothing")

    def _on_create(self):
        mod_name = self.entry_name.get().strip()
        source_type = self.source_var.get()

        if not mod_name:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update("Error: Mod name cannot be empty.")
            return

        # Check for forbidden names
        forbidden_names = [f for f in os.listdir(core.state.library) if
                           f in core.state.exceptions or os.path.isfile(f"{core.state.library}/{f}/_mod.json")]
        if mod_name in forbidden_names:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Error: Name '{mod_name}' is already in use.")
            return

        try:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Creating mod {mod_name}. Please wait...")
                self.update()  # Force UI to update before heavy processing

            # Create the Mod using your core logic!
            new_mod = Mod.create(name=mod_name, changes_source=source_type)

            # Send the user straight to the Mod Editor to finish filling out description/transfer type
            if hasattr(self.controller, 'open_mod_editor'):
                self.controller.open_mod_editor(new_mod)

        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)

    def _on_cancel(self):
        if hasattr(self.controller, 'show_frame'):
            self.controller.show_frame("ModManagerView")
