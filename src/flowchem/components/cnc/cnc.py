"""Base CNC component."""
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class CNC(FlowchemComponent):
    """
    A generic CNC device that controls movement in 3 dimensions (X, Y, Z).
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/set_xy_position", self.set_xy_position, methods=["PUT"])
        self.add_api_route("/set_z_position", self.set_z_position, methods=["PUT"])
        self.add_api_route("/get_position", self.get_position, methods=["GET"])
        self.component_info.type = "cnc"

    async def set_xy_position(self, plate: str = "", row: int = 0, column: int = 0) -> None:
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
