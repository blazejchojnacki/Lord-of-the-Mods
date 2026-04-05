import tkinter as tk
import source.shared as s

from interface.views.mod_manager import ModManagerView
from interface.views.settings import SettingsView


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        # Setup aesthetic defaults
        s.load_aesthetic()
        self.title("Modificator App")
        self.geometry("1250x650")
        self.configure(bg=s.APP_BACKGROUND_COLOR)

        # Build the Navigation Header
        self._build_header()

        # This is the master container where screens will be loaded
        self.main_container = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Dictionary to cache our views so we don't rebuild them every click
        self.frames = {}

        # Load the default view
        self.show_frame("ModManagerView")

    def _build_header(self):
        """ Builds a permanent navigation bar at the top of the window. """
        header = tk.Frame(self, bg=s.APP_BACKGROUND_COLOR)
        header.pack(fill="x", padx=10, pady=(10, 0))

        btn_mods = s.ReactiveButton(header, text="MODS", command=lambda: self.show_frame("ModManagerView"))
        btn_mods.pack(side="left", padx=(0, 5))

        btn_settings = s.ReactiveButton(header, text="SETTINGS", command=lambda: self.show_frame("SettingsView"))
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


if __name__ == "__main__":
    app = Application()
    app.mainloop()
