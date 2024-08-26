"""Base CNC component."""
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class CNC(FlowchemComponent):
    """
    A generic CNC device that controls movement in 3 dimensions (X, Y, Z).
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/move_to", self.move_to, methods=["PUT"])
        self.add_api_route("/move_x", self.stop, methods=["PUT"])
        self.add_api_route("/move_y", self.is_pumping, methods=["PUT"])
        self.add_api_route("/move_z", self.is_pumping, methods=["PUT"])
        self.add_api_route("/home", self.is_pumping, methods=["PUT"])
        self.add_api_route("/get_position", self.is_pumping, methods=["GET"])
        self.component_info.type = "cnc"

    async def move_to(self, x: float, y: float, z: float) -> None:
        """
        Move the CNC device to the specified (x, y, z) coordinates.
        :param x: X-coordinate to move to.
        :param y: Y-coordinate to move to.
        :param z: Z-coordinate to move to.
        """
        ...

    async def move_x(self, distance: float) -> None:
        """
        Move the CNC device along the X axis by a specified distance.
        distance: Distance to move along the X axis.
        """
        ...

    async def move_y(self, distance: float) -> None:
        """
        Move the CNC device along the Y axis by a specified distance.
        distance: Distance to move along the Y axis.
        """
        ...

    async def move_z(self, distance: float) -> None:
        """
        Move the CNC device along the Z axis by a specified distance.
        distance: Distance to move along the Z axis.
        """
        ...

    async def home(self) -> None:
        """
        Return the CNC device to the home position
        """
        ...

    async def get_position(self) -> tuple:
        """
        Get the current position of the CNC device.
        A tuple (x, y, z) representing the current position.
        """
        ...
