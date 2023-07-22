import tkinter
from tkinter.ttk import Notebook

from src.server.data.resource import Resource
from src.server.ui.gui.frame.frame_about import FrameAbout
from src.server.ui.gui.frame.frame_get_key import FrameGetKey
from src.server.ui.gui.frame.frame_log import FrameLog
from src.server.ui.gui.frame.frame_run_server import FrameRunServer
from src.server.util.logging.logger_gui import LoggerGui


class GuiMain:
    def __init__(self):
        """
        Main Gui Entrance
        """
        tkinter.Tk.report_callback_exception = self.throw
        # Main window
        self.destroyed = False
        LoggerGui.info("Initializing GUI")
        self.main_window = tkinter.Tk()
        self.main_window.wm_title("DRC Sim Server")
        icon = tkinter.PhotoImage(data=Resource("image/icon.gif").resource)
        self.main_window.tk.call("wm", "iconphoto", self.main_window, icon)
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.main_window.resizable(False, False)
        # Notebook
        self.tab_id = None
        self.notebook = Notebook(self.main_window, width=600, height=300)
        self.notebook.grid(column=0, row=0)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        # Run Server Frame
        self.frame_run_server = FrameRunServer(self.notebook)
        self.notebook.add(self.frame_run_server, text="Run Server")
        # Get Key Frame
        self.frame_get_key = FrameGetKey(self.notebook)
        self.notebook.add(self.frame_get_key, text="Get Key")
        # Log Frame
        self.frame_log = FrameLog(self.notebook)
        self.notebook.add(self.frame_log, text="Log")
        # About Frame
        self.frame_about = FrameAbout(self.notebook)
        self.notebook.add(self.frame_about, text="About")

    @staticmethod
    def throw(*args):
        """
        Throw exceptions from Tkinter
        :param args: arguments
        :return: None
        """
        for arg in args:
            if isinstance(arg, Exception):
                LoggerGui.throw(arg)

    def after(self):
        """
        Empty loop to catch KeyboardInterrupt
        :return: None
        """
        self.main_window.after(1000, self.after)

    def start(self):
        """
        Start the main window loop
        :return:
        """
        LoggerGui.info("Opening GUI")
        self.after()
        self.main_window.mainloop()
        LoggerGui.info("GUI Closed")

    def stop(self):
        """
        Convenience function to call on_closing()
        :return: None
        """
        self.on_closing()

    def on_closing(self):
        """
        Close the main window and current tab
        :return: None
        """
        if self.destroyed:
            return
        self.destroyed = True
        LoggerGui.info("Closing GUI")
        if self.tab_id in self.notebook.children:
            self.notebook.children[self.tab_id].deactivate()
        try:
            self.main_window.destroy()
        except Exception as e:
            LoggerGui.exception(e)

    # noinspection PyUnusedLocal
    def on_tab_changed(self, event):
        """
        Close the previous tab and initialize a new one
        :param event: tab event
        :return: None
        """
        tab_id = self.notebook.select()
        tab_index = self.notebook.index(tab_id)
        tab_name = self.notebook.tab(tab_index, "text")
        LoggerGui.debug("Notebook tab changed to \"%s\" with id %d", tab_name, tab_index)
        self.tab_id = tab_id.split(".")[len(tab_id.split(".")) - 1]  # Parse notebook/tab id to only tab id
        if self.notebook.children[self.tab_id].kill_other_tabs():
            for tab in self.notebook.children:
                if tab != self.tab_id:
                    self.notebook.children[tab].deactivate()
        self.notebook.children[self.tab_id].activate()
