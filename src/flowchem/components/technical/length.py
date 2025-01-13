"""LengthControl Component"""
from loguru import logger
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class LengthControl(FlowchemComponent):
    """
    A generic LengthControl component to represent a linear axis system.
    This serves as a base class for components like CNC that deal with positions.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice, mode: str = "discrete", _available_positions: list = []) -> None:
        """
        Initialize the LengthControl component.

        Args:
        name (str): Name of the LengthControl component.
        hw_device (FlowchemDevice): Hardware device interface.
        mode (str): The mode of movement, either "discrete" or "continuous". Default is "discrete".
        _available_positions (list):
            - If mode is "discrete": List of valid positions (float, or str).
            - If mode is "continuous": List containing [min, max] bounds (float or int).
        """
        super().__init__(name, hw_device)
        self.mode = mode.lower()  # discrete or continuous
        if self.mode not in ["discrete", "continuous"]:
            logger.error(f"Invalid mode: {self.mode}. Must be 'discrete' or 'continuous'.")
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'discrete' or 'continuous'.")
        self._available_positions = self.set_available_positions(_available_positions)  # List of available positions if discrete, min and max if continuous.

        self.add_api_route("/get_position", self.get_position, methods=["GET"])
        self.add_api_route("/set_position", self.set_position, methods=["PUT"])
        self.add_api_route("/get_available_positions", self.get_available_positions, methods=["GET"])
        self.add_api_route("/set_available_positions", self.set_available_positions, methods=["PUT"])

    async def get_position(self):
        """
        Get the current position of the LengthControl component.

        Returns:
            Union[int, str]: The current position.
        """
        ...

    async def set_position(self, position: Union[float, str]) -> None:
        """
        Move the LengthControl component to a specific position.

        Args:
            position (Union[float, str]): The desired position to move to.

        """
        ...

    async def validate_set_position(self, position: Union[float, str]) -> None:
        """
        Validate the provided position based on the mode (discrete or continuous).

        Args:
            position (Union[float, str]): The position to validate.
        """
        if self.mode == "discrete":
            if position not in self._available_positions:
                logger.warning(
                    f"Invalid position '{position}' in discrete mode. "
                    f"Available positions: {self._available_positions}."
                )
                raise ValueError(
                    f"Position '{position}' is not valid in discrete mode. "
                    f"Available positions: {self._available_positions}."
                )
        elif self.mode == "continuous":
            if not (self._available_positions[0] <= position <= self._available_positions[1]):
                logger.warning(
                    f"Position {position} is out of bounds for continuous mode. "
                    f"Bounds: {self._available_positions[0]} to {self._available_positions[1]}."
                )
                raise RuntimeError(
                    f"Position {position} is out of bounds for continuous mode. "
                    f"Bounds: {self._available_positions[0]} to {self._available_positions[1]}."
                )
        return True

    async def get_available_positions(self) -> list:
        """
        Get the available positions.

        Returns:
            list:
                - For discrete mode: List of valid positions (float or str).
                - For continuous mode: [min, max] bounds.
        """
        return self._available_positions

    async def set_available_positions(self, positions: list[Union[float, str]]) -> None:
        """
        Set the available positions or bounds for the LengthControl component.

        Args:
            positions (list[Union[float, str]]):
                - For discrete mode: List of valid positions (float or str).
                - For continuous mode: [min, max] bounds.
        """
        if self.mode == "discrete":
            if not all(isinstance(pos, (float, float, str)) for pos in positions):
                logger.error("All positions must be numbers or strings in discrete mode.")
                raise ValueError("All positions must be numbers or strings in discrete mode.")
            self._available_positions = positions
        elif self.mode == "continuous":
            if len(positions) != 2 or positions[0] >= positions[1]:
                logger.error(
                    "In continuous mode, positions must be a list of two values [min, max] "
                    "with min < max."
                )
                raise ValueError(
                    "In continuous mode, positions must be a list of two values [min, max] "
                    "with min < max."
                )
            self._available_positions = positions

