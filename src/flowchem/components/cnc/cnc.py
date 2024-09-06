"""Base CNC component."""
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class CNC(FlowchemComponent):
    """
    A generic CNC device that controls movement in 3 dimensions (X, Y, Z).
    """

    def __init__(self, name: str, hw_device: FlowchemDevice,  tray_layout) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/set_xy_position", self.set_xy_position, methods=["PUT"])
        self.add_api_route("/set_z_position", self.set_z_position, methods=["PUT"])
        self.add_api_route("/get_position", self.get_position, methods=["GET"])
        self.component_info.type = "cnc"
        self.tray_layout = tray_layout  # Dictionary to hold tray configurations
        self.current_tray = 0  # The default tray is Tray 0
        self.current_position = (0, 0)  # Start at the origin of Tray 0 (0, 0)

    async def set_xy_position(self, tray: int = 0, row: int = 0, column: int = 0) -> None:
        """
        Move the CNC device to the specified (x, y) coordinate.
        """
        ...

    async def set_z_position(self, position: str = "") -> None:
        """
        Connect to a specific sample along the Z axis.
        """
        ...

    async def get_position(self) -> tuple:
        """
        Get the current position of the CNC device.
        A tuple (x, y, z) representing the current position.
        """
        ...


