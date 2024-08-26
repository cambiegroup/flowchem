"""cnc that moves only to certain positions in a tray."""

from flowchem.components.cnc.cnc import CNC
from flowchem.devices.flowchem_device import FlowchemDevice


class TrayCNC(CNC):
    """
        A CNC device that can only move to predefined positions in a tray.
        The tray is defined by a grid of rows and columns.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice,  rows: int, columns: int) -> None:
        """
        Initialize the TrayCNC with the given number of rows and columns. Only 1 tray as default.
        rows: Number of rows in the tray.
        columns: Number of columns in the tray.
        """
        super().__init__(name, hw_device)
        self.component_info.type = "Tray CNC"
        self.trays = {}  # Dictionary to hold tray configurations
        self.current_tray = 0  # The default tray is Tray 0
        self.trays[self.current_tray] = (rows, columns)
        self.position = (0, 0)  # Start at the origin of Tray 0 (0, 0)

    def add_tray(self, rows: int, columns: int) -> None:
        """
        Add a new tray to the CNC device.
        rows: Number of rows in the tray.
        columns: Number of columns in the tray.
        """
        new_tray_id = len(self.trays)
        self.trays[new_tray_id] = (rows, columns)

    def select_tray(self, tray_id: int) -> None:
        """
        Select the tray to operate on.
        tray: Identifier for the tray to select.
        """
        if tray_id not in self.trays:
            raise ValueError(f"Tray {tray_id} not found")
        self.current_tray = tray_id


