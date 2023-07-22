import os
from tkinter import messagebox
from tkinter.ttk import Label, Button, Combobox

from src.server.data import constants
from src.server.ui.gui.frame.frame_tab import FrameTab
from src.server.util.drc_sim_c import DrcSimC
from src.server.util.interface_util import InterfaceUtil
from src.server.util.logging.logger_gui import LoggerGui
from src.server.util.wpa_supplicant import WpaSupplicant
from src.server.util.os_util import OsUtil
from src.server.util.process_util import ProcessUtil


class FrameRunServer(FrameTab):
    def __init__(self, master=None, **kw):
        """
        GUI tab that handles interface and region selection and starting the server.
        :param master: root window
        :param kw: args
        """
        FrameTab.__init__(self, master, **kw)
        self.wii_u_interface = None
        self.normal_interface = None
        self.drc_sim_c = None
        self.wpa_supplicant = None
        LoggerGui.extra("Initializing FrameRunServer")
        # Create Widgets
        self.label_wpa = Label(self, text="Wii U Connection:")
        self.label_backend = Label(self, text="Server Status:")
        self.label_wpa_status = Label(self)
        self.label_backend_status = Label(self)
        self.button_start = Button(self, text="Start")
        self.button_stop = Button(self, text="Stop")
        self.label_wiiu_interface = Label(self, text="Wii U Interface")
        self.label_normal_interface = Label(self, text="Normal Interface")
        self.dropdown_wiiu_interface = Combobox(self, state="readonly")
        self.dropdown_normal_interface = Combobox(self, state="readonly")
        self.label_interface_info = Label(self)
        self.label_region = Label(self, text="Region")
        self.dropdown_region = Combobox(self, state="readonly")
        # Events
        self.button_start.bind("<Button-1>", self.start_server)
        self.button_stop.bind("<Button-1>", self.stop_server)
        # Position widgets
        self.label_wpa.grid(column=0, row=0, sticky="e")
        self.label_backend.grid(column=0, row=1, sticky="e")
        self.label_wpa_status.grid(column=1, row=0, sticky="w")
        self.label_backend_status.grid(column=1, row=1, sticky="w")
        self.label_wiiu_interface.grid(column=0, row=2)
        self.label_normal_interface.grid(column=0, row=3)
        self.dropdown_wiiu_interface.grid(column=1, row=2, columnspan=2)
        self.dropdown_normal_interface.grid(column=1, row=3, columnspan=2)
        self.label_region.grid(column=0, row=4)
        self.dropdown_region.grid(column=1, row=4, columnspan=2)
        self.button_start.grid(column=1, row=5)
        self.button_stop.grid(column=2, row=5)
        self.label_interface_info.grid(column=0, row=6, columnspan=3)
        LoggerGui.extra("Initialized FrameRunServer")

    def start_server(self, event=None):
        """
        Try to start wpa_supplicant and connect to a Wii U.
        :param event: Determines if this was a user initiated start.
        :return: None
        """
        if event:
            LoggerGui.debug("User clicked start server button")
        LoggerGui.debug("Start server called")
        if self.label_backend_status["text"] != DrcSimC.STOPPED and \
                (self.label_wpa_status["text"] not in (WpaSupplicant.DISCONNECTED, WpaSupplicant.TERMINATED)):
            messagebox.showerror("Running", "Server is already running")
            return
        if not os.path.exists(constants.PATH_CONF_CONNECT):
            messagebox.showerror("Auth Error",
                                 "No auth details found. Use the \"Get Key\" tab to pair with a Wii U.")
            self.activate()
            return
        self.normal_interface = self.dropdown_normal_interface.get()
        self.wii_u_interface = self.dropdown_wiiu_interface.get()
        if not self.normal_interface or not self.wii_u_interface:
            messagebox.showerror("Interface Error", "Two interfaces need to be selected.")
            self.activate()
            return
        if self.normal_interface == self.wii_u_interface:
            messagebox.showerror("Interface Error", "The selected normal and Wii U interfaces must be different.")
            self.activate()
            return
        try:
            InterfaceUtil.get_mac(self.normal_interface)
            InterfaceUtil.get_mac(self.wii_u_interface)
        except ValueError:
            messagebox.showerror("Interface Error", "The selected Interface is no longer available.")
            self.activate()
            return
        if InterfaceUtil.is_managed_by_network_manager(self.wii_u_interface):
            set_unmanaged = messagebox.askokcancel(
                "Managed Interface", "This interface is managed by Network Manager. To use it with DRC Sim it needs "
                                     "to be set to unmanaged. Network Manager will not be able to control the interface"
                                     " after this.\nSet %s to unmanaged?" % self.wii_u_interface)
            if set_unmanaged:
                InterfaceUtil.set_unmanaged_by_network_manager(self.wii_u_interface)
                    
            else:
                messagebox.showerror("Managed Interface", "Selected Wii U interface is managed by Network Manager.")
                self.activate()
                return

            #reboot_now = messagebox.askokcancel(
            #    "Applying Changes", "For the changes to fully take effect you need to restart your PC "
            #    "Do it now?")
            #if reboot_now:
            #    ProcessUtil.call(["reboot", "-h", "now"])
            #else: 
            #    self.activate()
            #    return

        LoggerGui.debug("Starting wpa supplicant")
        self.wpa_supplicant = WpaSupplicant()
        self.wpa_supplicant.add_status_change_listener(self.wpa_status_changed)
        self.wpa_supplicant.connect(constants.PATH_CONF_CONNECT, self.wii_u_interface)
        self.label_backend_status.config(text="WAITING")

    def wpa_status_changed(self, status):
        """
        Handles wpa status changes. Initializes backend server if a connection is made.
        :param status: status message
        :return: None
        """
        LoggerGui.debug("Wpa changed status to %s", status)
        self.label_wpa_status.config(text=status)
        if status == WpaSupplicant.CONNECTED:
            LoggerGui.debug("Routing")
            InterfaceUtil.dhclient(self.wii_u_interface)
            InterfaceUtil.set_metric(self.wii_u_interface, 1)
            InterfaceUtil.set_metric(self.normal_interface, 0)
            LoggerGui.debug("Starting backend")
            self.drc_sim_c = DrcSimC()
            self.drc_sim_c.add_status_change_listener(self.backend_status_changed)
            self.drc_sim_c.set_region(self.dropdown_region.get())
            self.drc_sim_c.start()
            self.label_interface_info.config(text="Server IP: " + InterfaceUtil.get_ip(self.normal_interface)
                                                  + "\n" + os.uname()[1])
        elif status in (WpaSupplicant.DISCONNECTED, WpaSupplicant.TERMINATED):
            InterfaceUtil.set_metric(self.wii_u_interface, 0)
            self.stop_server()
        elif status == WpaSupplicant.NOT_FOUND:
            self.stop_server()
            messagebox.showerror("Scan Error", "No Wii U found.")
        elif status == WpaSupplicant.FAILED_START:
            InterfaceUtil.set_metric(self.wii_u_interface, 0)
            self.stop_server()
            messagebox.showerror("Cannot Connect", "Failed to start wpa_supplicant_drc. This could mean there is a "
                                                   "configuration error or wpa_supplicant_drc is not installed. "
                                                   "Check %s for details." % constants.PATH_LOG_WPA)

    def backend_status_changed(self, status):
        """
        Handles backend status changes.
        :param status: status message
        :return: None
        """
        LoggerGui.debug("Backend status changed to %s", status)
        self.label_backend_status.config(text=status)
        if status == DrcSimC.STOPPED:
            self.stop_server()

    def stop_server(self, event=None):
        """
        Stops active threads.
        :param event: Determines if this is a user initiated stop
        :return: None
        """
        if event:
            LoggerGui.debug("User clicked stop server button")
        LoggerGui.debug("Stop server called")
        if event and (self.label_wpa_status["text"] in (WpaSupplicant.DISCONNECTED, WpaSupplicant.TERMINATED)
                      and self.label_backend_status["text"] == DrcSimC.STOPPED):
            messagebox.showerror("Stop", "Server is not running.")
            return
        if self.drc_sim_c:
            self.drc_sim_c.stop()
            self.drc_sim_c = None
        if self.wpa_supplicant:
            self.wpa_supplicant.stop()
            self.wpa_supplicant = None
        self.activate()

    def activate(self):
        """
        Initializes the frame.
        :return: None
        """
        LoggerGui.debug("FrameRunServer activated")
        self.dropdown_wiiu_interface["values"] = InterfaceUtil.get_wiiu_compatible_interfaces()
        self.dropdown_normal_interface["values"] = InterfaceUtil.get_all_interfaces()
        self.dropdown_region["values"] = ["NONE", "NA"]
        self.label_wpa_status["text"] = self.wpa_supplicant.get_status() \
            if self.wpa_supplicant and self.wpa_supplicant.get_status() else WpaSupplicant.DISCONNECTED
        self.label_backend_status["text"] = self.drc_sim_c.get_status() \
            if self.drc_sim_c and self.drc_sim_c.get_status() else DrcSimC.STOPPED
        self.button_start.config(state="normal")
        self.button_stop.config(state="normal")
        self.label_interface_info.config(text="")

    def deactivate(self):
        """
        De-initializes the frame.
        :return: None
        """
        LoggerGui.debug("FrameRunServer deactivated")
        self.stop_server()

    def kill_other_tabs(self):
        return True
