import os
import tkinter as tk
from tkinter.filedialog import askdirectory, askopenfilenames

from source.messaging import InternalError
import source.shared as s
from source.constants import PROGRAM_NAME
from source.editor import text_find_replace, reformat_string


class FindReplaceView(tk.Frame):
    """ The View responsible for searching and replacing text across files and folders. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=s.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.current_context_path = ""

        self._build_ui()

    def _build_ui(self):
        """ Constructs the unified Find & Replace layout. """
        # --- Top Section: Navigation ---
        frame_top = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_top.pack(fill="x", pady=(0, 10))

        btn_back = s.ReactiveButton(frame_top, text="🡄 BACK", small=True, command=self._on_back)
        btn_back.pack(side="left", padx=(0, 10))

        lbl_title = tk.Label(frame_top, text="Find and Replace Tool", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                             font=s.FONT_TEXT)
        lbl_title.pack(side="left", fill="x", expand=True, anchor="w")

        # --- Middle Section: The Input Form ---
        frame_form = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_form.pack(fill="x", padx=10)
        frame_form.columnconfigure(1, weight=1)  # Makes the text boxes expand

        # 1. Find Text
        tk.Label(frame_form, text="Find Text:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0], anchor="e").grid(row=0,
                                                                                                                 column=0,
                                                                                                                 sticky="e",
                                                                                                                 pady=5,
                                                                                                                 padx=5)
        self.text_find = tk.Text(frame_form, height=3, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                 font=s.FONT_TEXT)
        self.text_find.grid(row=0, column=1, sticky="we", pady=5, padx=5)

        btn_copy_down = s.ReactiveButton(frame_form, text="🡇 COPY", small=True,
                                         info_content="Copy text to replace field", command=self._on_copy_down)
        btn_copy_down.grid(row=0, column=2, padx=5)

        # 2. Replace Text
        tk.Label(frame_form, text="Replace With:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0], anchor="e").grid(
            row=1, column=0, sticky="e", pady=5, padx=5)
        self.text_replace = tk.Text(frame_form, height=3, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                    font=s.FONT_TEXT)
        self.text_replace.grid(row=1, column=1, sticky="we", pady=5, padx=5)

        # 3. Scope Select
        tk.Label(frame_form, text="In File/Folder:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0], anchor="e").grid(
            row=2, column=0, sticky="e", pady=5, padx=5)
        self.text_scope = tk.Text(frame_form, height=2, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                  font=s.FONT_TEXT)
        self.text_scope.grid(row=2, column=1, sticky="we", pady=5, padx=5)

        frame_scope_btns = tk.Frame(frame_form, bg=s.APP_BACKGROUND_COLOR)
        frame_scope_btns.grid(row=2, column=2, sticky="w")
        s.ReactiveButton(frame_scope_btns, text="FILE", small=True,
                         command=lambda: self._browse_file(self.text_scope)).pack(side="left", padx=2)
        s.ReactiveButton(frame_scope_btns, text="FOLDER", small=True,
                         command=lambda: self._browse_folder(self.text_scope)).pack(side="left", padx=2)

        # 4. Exceptions Select
        tk.Label(frame_form, text="Except:", bg=s.APP_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0], anchor="e").grid(row=3,
                                                                                                              column=0,
                                                                                                              sticky="e",
                                                                                                              pady=5,
                                                                                                              padx=5)
        self.text_except = tk.Text(frame_form, height=2, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[0],
                                   font=s.FONT_TEXT)
        self.text_except.grid(row=3, column=1, sticky="we", pady=5, padx=5)

        frame_except_btns = tk.Frame(frame_form, bg=s.APP_BACKGROUND_COLOR)
        frame_except_btns.grid(row=3, column=2, sticky="w")
        s.ReactiveButton(frame_except_btns, text="FILE", small=True,
                         command=lambda: self._browse_file(self.text_except)).pack(side="left", padx=2)
        s.ReactiveButton(frame_except_btns, text="FOLDER", small=True,
                         command=lambda: self._browse_folder(self.text_except)).pack(side="left", padx=2)

        # --- Actions Section ---
        frame_actions = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        frame_actions.pack(fill="x", pady=10)

        s.ReactiveButton(frame_actions, text="FIND TEXT", command=self._on_find).pack(side="left", padx=5)
        s.ReactiveButton(frame_actions, text="REPLACE TEXT", command=self._on_replace).pack(side="left", padx=5)
        s.ReactiveButton(frame_actions, text="CLEAR LOGS", command=self._clear_logs).pack(side="right", padx=5)

        # --- Bottom Section: Results Log ---
        self.text_result = tk.Text(self, height=10, bg=s.ENTRY_BACKGROUND_COLOR, fg=s.TEXT_COLORS[1], font=s.FONT_TEXT,
                                   state="disabled")
        self.text_result.pack(fill="both", expand=True, pady=5)

    def load_context(self, selection: str = "", scope_path: str = ""):
        """ Pre-fills the tool based on what the user was doing before they opened it. """
        self.current_context_path = scope_path

        # Populate Find Box
        if selection:
            formatted_selection = reformat_string(selection, direction='display')
            self.text_find.delete("1.0", tk.END)
            self.text_find.insert("1.0", formatted_selection)

        # Populate Scope Box
        if scope_path:
            self.text_scope.delete("1.0", tk.END)
            self.text_scope.insert("1.0", scope_path)

        self._clear_logs()

    def _browse_folder(self, target_widget: tk.Text):
        """ Wraps askdirectory. """
        initial = os.path.dirname(self.current_context_path) if self.current_context_path else "../"
        path = askdirectory(title=f"{PROGRAM_NAME}: Select a folder", initialdir=initial)
        if path:
            self._append_to_widget(target_widget, path)

    def _browse_file(self, target_widget: tk.Text):
        """ Wraps askopenfilenames. """
        initial = os.path.dirname(self.current_context_path) if self.current_context_path else "../"
        paths = askopenfilenames(title=f"{PROGRAM_NAME}: Select file(s)", initialdir=initial)
        if paths:
            # Clean up the tuple formatting for the UI
            cleaned_paths = str(paths).strip("(),'")
            self._append_to_widget(target_widget, cleaned_paths)

    def _append_to_widget(self, widget: tk.Text, text: str):
        """ Safely appends text to a widget, adding a comma if it already has content. """
        current_content = widget.get("1.0", tk.END).strip()
        if current_content:
            widget.insert(tk.END, f", {text}")
        else:
            widget.insert(tk.END, text)

    def _on_copy_down(self):
        """ Copies the Find text into the Replace text. """
        find_text = self.text_find.get("1.0", tk.END).strip()
        self.text_replace.delete("1.0", tk.END)
        self.text_replace.insert("1.0", find_text)

    def _on_find(self):
        """ Extracts arguments and routes to the editor's find logic. """
        find_str = reformat_string(self.text_find.get("1.0", tk.END).strip(), direction='display')
        scope = self.text_scope.get("1.0", tk.END).replace('/', '\\').strip()
        exceptions_raw = self.text_except.get("1.0", tk.END).replace('/', '\\').strip()

        if not find_str or not scope:
            self._log_result("Error: Please provide both 'Find Text' and an 'In File/Folder' scope.")
            return

        exceptions = exceptions_raw.split(', ') if exceptions_raw else []

        try:
            output = text_find_replace(find=find_str, scope=scope, exceptions=exceptions, mode='initiate')
            self._log_result(output)
        except InternalError as e:
            self._log_result(e.message)

    def _on_replace(self):
        """ Extracts arguments and routes to the editor's replace logic. """
        find_str = reformat_string(self.text_find.get("1.0", tk.END).strip(), direction='display')
        replace_str = reformat_string(self.text_replace.get("1.0", tk.END).strip(), direction='display')
        scope = self.text_scope.get("1.0", tk.END).replace('/', '\\').strip()
        exceptions_raw = self.text_except.get("1.0", tk.END).replace('/', '\\').strip()

        if not find_str or not scope:
            self._log_result("Error: Please provide 'Find Text' and a 'Scope' to replace.")
            return

        exceptions = exceptions_raw.split(', ') if exceptions_raw else []

        try:
            output = text_find_replace(find=find_str, replace_with=replace_str, scope=scope, exceptions=exceptions)
            self._log_result(output)

            # If the user opened this from the File Editor, we should notify the main app
            # to reload the file editor so it shows the new changes!
            if hasattr(self.controller, 'reload_file_editor'):
                self.controller.reload_file_editor(scope)

        except InternalError as e:
            self._log_result(e.message)

    def _log_result(self, text: str):
        """ Updates the dedicated result box. """
        self.text_result.configure(state="normal")
        self.text_result.delete("1.0", tk.END)
        self.text_result.insert(tk.END, text)
        self.text_result.configure(state="disabled")

    def _clear_logs(self):
        """ Clears the result box. """
        self._log_result("")

    def _on_back(self):
        """ Returns to the previous view (usually the File Editor). """
        # Let the controller decide where to go back to based on navigation history
        if hasattr(self.controller, 'navigate_back'):
            self.controller.navigate_back()
