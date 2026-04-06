import os
import tkinter as tk
from tklinenums import TkLineNumbers

from source.messaging import InternalError
import source.shared as shared
from source.constants import INI_COMMENTS, INI_ENDS, LEVEL_INDENT
from source.constructor import load_file


class FileEditorView(tk.Frame):
    """ The View responsible for displaying, editing, and highlighting file content. """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=shared.APP_BACKGROUND_COLOR)
        self.controller = controller

        self.current_path = ""
        self.current_levels = []
        self.content_backup = ""

        self._build_ui()
        self._setup_bindings()

    def _build_ui(self):
        """ Constructs the editor layout. """
        # --- Top Section: Navigation & Save ---
        frame_top = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_top.pack(fill="x", pady=(0, 5))

        btn_back = shared.ReactiveButton(frame_top, text="🡄 BACK", small=True, command=self._on_back)
        btn_back.pack(side="left", padx=(0, 10))

        self.lbl_path = tk.Label(frame_top, text="No file loaded", bg=shared.APP_BACKGROUND_COLOR,
                                 fg=shared.TEXT_COLORS[0], font=shared.FONT_TEXT)
        self.lbl_path.pack(side="left", fill="x", expand=True, anchor="w")

        self.btn_save = shared.ReactiveButton(frame_top, text="SAVE FILE", command=self._on_save)
        self.btn_save.pack(side="right")

        # --- Middle Section: The Text Editor ---
        frame_editor = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_editor.pack(fill="both", expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(frame_editor)
        scrollbar.pack(side="right", fill="y")

        # Text Widget
        self.text_widget = tk.Text(
            frame_editor,
            bg=shared.ENTRY_BACKGROUND_COLOR,
            fg=shared.TEXT_COLORS[0],
            font=shared.FONT_TEXT,
            selectbackground=shared.TEXT_COLORS[0],
            selectforeground=shared.TEXT_COLORS[-1],
            undo=True,
            yscrollcommand=scrollbar.set
        )
        self.text_widget.pack(side="right", fill="both", expand=True)
        scrollbar.config(command=self.text_widget.yview)

        # Line Numbers (tklinenums package)
        self.linenums = TkLineNumbers(frame_editor, self.text_widget, justify='right')
        self.linenums.pack(side="left", fill="y")

        # --- Bottom Section: Editor Tools ---
        frame_tools = tk.Frame(self, bg=shared.APP_BACKGROUND_COLOR)
        frame_tools.pack(fill="x", pady=5)

        btn_comment = shared.ReactiveButton(frame_tools, text="COMMENT (Ctrl+/)", command=self._on_comment)
        btn_comment.pack(side="left", padx=5)

        btn_uncomment = shared.ReactiveButton(frame_tools, text="UNCOMMENT (Ctrl+\\)", command=self._on_uncomment)
        btn_uncomment.pack(side="left", padx=5)

        btn_find = shared.ReactiveButton(frame_tools, text="FIND (Ctrl+F)", command=self._on_find)
        btn_find.pack(side="left", padx=5)

        btn_replace = shared.ReactiveButton(frame_tools, text="REPLACE (Ctrl+R)", command=self._on_replace)
        btn_replace.pack(side="left", padx=5)

    def _setup_bindings(self):
        """ Attaches keyboard shortcuts and event listeners. """
        self.text_widget.bind("<<Modified>>", self._on_modified)

        # Keyboard shortcuts
        self.bind_all('<Control-Key-f>', lambda e: self._on_find())
        self.bind_all('<Control-Key-r>', lambda e: self._on_replace())
        self.text_widget.bind('<Control-Key-/>', lambda e: self._on_comment() or "break")
        self.text_widget.bind('<Control-Key-\\>', lambda e: self._on_uncomment() or "break")

    def load_file_path(self, filepath: str):
        """ Called by the controller to load a new file into the editor. """
        self.current_path = filepath.replace('\\', '/')
        self.lbl_path.configure(text=f"Editing: {os.path.abspath(self.current_path)}")

        # Clean the editor
        self.text_widget.delete('1.0', tk.END)

        try:
            # Using your decoupled logic layer!
            content, levels = load_file(self.current_path)
            self.content_backup = content
            self.current_levels = levels

            self.text_widget.insert('end', content)

            # Reset the modified flag so we don't accidentally trigger a save warning immediately
            self.text_widget.edit_modified(False)

            # Apply highlighting
            self._apply_syntax_highlighting()

            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Loaded {self.current_path}")

        except InternalError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(e.message)
            self._on_back()

    def _on_modified(self, event=None):
        """ Triggered whenever the text changes. Refreshes line numbers and highlights. """
        # Only process if the flag is actually set to True
        if self.text_widget.edit_modified():
            self.linenums.redraw()
            self._apply_syntax_highlighting()

            # We must reset the flag so it can be triggered again!
            self.text_widget.edit_modified(False)

    def _apply_syntax_highlighting(self):
        """ Evaluates the text and applies color tags based on INI structure. """
        # Clear existing tags
        for tag_name in self.text_widget.tag_names():
            if tag_name != "sel":  # Don't clear user selection
                self.text_widget.tag_remove(tag_name, "1.0", "end")

        text_lines = self.text_widget.get('1.0', 'end').split('\n')

        for line_index, line in enumerate(text_lines, start=1):
            if not line.strip():
                continue

            rest_of_line = line

            # 1. Identify Comments
            comment_tag = f"comment_{line_index}"
            if line.strip()[0] in INI_COMMENTS:
                self.text_widget.tag_add(comment_tag, f'{line_index}.0', f'{line_index}.end')
                rest_of_line = ''
            elif INI_COMMENTS[0] in line:
                idx = line.index(INI_COMMENTS[0])
                self.text_widget.tag_add(comment_tag, f'{line_index}.{idx}', f'{line_index}.end')
                rest_of_line = line[:idx]
            elif len(INI_COMMENTS) > 1 and INI_COMMENTS[1] * 2 in line:
                idx = line.index(INI_COMMENTS[1] * 2)
                self.text_widget.tag_add(comment_tag, f'{line_index}.{idx}', f'{line_index}.end')
                rest_of_line = line[:idx]

            self.text_widget.tag_config(comment_tag, foreground='grey')

            # 2. Identify Block Levels (Object, Armor, etc.)
            if rest_of_line and self.current_levels:
                level = rest_of_line.rstrip().count(LEVEL_INDENT)

                # Protect against files deeper than our defined delimiter levels
                if level < len(self.current_levels) and level < len(shared.INI_LEVEL_COLORS):
                    level_tag = f'level{level}_{line_index}'
                    self.text_widget.tag_config(level_tag, foreground=shared.INI_LEVEL_COLORS[level])

                    first_word = rest_of_line.split()[0].strip()

                    if first_word in self.current_levels[level] or rest_of_line.strip() in INI_ENDS:
                        self.text_widget.tag_add(level_tag, f'{line_index}.0', f'{line_index}.{len(rest_of_line)}')

    def _on_save(self):
        """ Writes the editor content back to disk. """
        if not self.current_path:
            return

        content = self.text_widget.get('1.0', 'end-1c')  # -1c prevents adding a blank newline at the end

        try:
            with open(self.current_path, 'w') as f:
                f.write(content)
            self.content_backup = content

            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Saved {self.current_path}")
        except OSError as e:
            if hasattr(self.controller, 'set_log_update'):
                self.controller.set_log_update(f"Error saving file: {e}")

    def check_unsaved_changes(self) -> bool:
        """ Compares current text to backup. Returns True if changes exist. """
        current_content = self.text_widget.get('1.0', 'end-1c')
        return current_content != self.content_backup

    def _on_comment(self):
        """ Wraps the interface.py commenting logic. """
        self._toggle_comment_block(is_commenting=True)

    def _on_uncomment(self):
        """ Wraps the interface.py uncommenting logic. """
        self._toggle_comment_block(is_commenting=False)

    def _toggle_comment_block(self, is_commenting: bool):
        """ Consolidates the commenting/uncommenting logic. """
        try:
            target_text = self.text_widget.get('sel.first linestart', 'sel.last lineend')
            replace_start = 'sel.first linestart'
            replace_end = 'sel.last lineend + 1 chars'
        except tk.TclError:
            # No selection, operate on current line
            target_text = self.text_widget.get('insert linestart', 'insert lineend')
            replace_start = 'insert linestart'
            replace_end = 'insert lineend + 1 chars'

        lines = target_text.split('\n')
        new_text = ""

        for line in lines:
            # Find the indentation level
            for level in range(7):
                indent = LEVEL_INDENT * (6 - level)
                if line.startswith(indent):
                    if is_commenting:
                        new_text += f'{indent}; {line.strip()}\n'
                    else:
                        if '; ' in line:
                            new_text += f"{indent}{line.strip()[len('; '):]}\n"
                        elif '//' in line:
                            new_text += f"{indent}{line.strip()[len('//'):]}\n"
                        else:
                            new_text += f"{line}\n"  # Wasn't commented
                    break
            else:
                new_text += f"{line}\n"  # Fallback if no indent matched

        # Apply the changes
        self.text_widget.replace(replace_start, replace_end, new_text)
        self._apply_syntax_highlighting()

    def _on_find(self):
        """ Gathers selected text and routes to the Find tool. """
        selection = ""
        try:
            selection = self.text_widget.get("sel.first", "sel.last")
        except tk.TclError:
            pass

        if hasattr(self.controller, 'open_find_tool'):
            self.controller.open_find_tool(selection, self.current_path)

    def _on_replace(self):
        """ Gathers selected text and routes to the Replace tool. """
        selection = ""
        try:
            selection = self.text_widget.get("sel.first", "sel.last")
        except tk.TclError:
            pass

        if hasattr(self.controller, 'open_replace_tool'):
            self.controller.open_replace_tool(selection, self.current_path)

    def _on_back(self):
        """ Handles safely leaving the editor. """
        if self.check_unsaved_changes():
            answer = shared.invoke_choice(
                title='Closing Editor',
                text='Do you want to save your changes?',
                buttons=({shared.KEY_LABEL: 'Yes', shared.KEY_RETURN: True, shared.KEY_INFO: ''},
                         {shared.KEY_LABEL: 'No', shared.KEY_RETURN: False, shared.KEY_INFO: ''},
                         {shared.KEY_LABEL: 'Cancel', shared.KEY_RETURN: None, shared.KEY_INFO: ''})
            )
            if answer is True:
                self._on_save()
            elif answer is None:
                return  # Abort leaving

        if hasattr(self.controller, 'show_frame'):
            self.controller.show_frame("FileBrowserView")
