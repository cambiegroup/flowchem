from flowchem import ureg
from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.valves.distribution_valves import FourPortDistributionValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve

class AutosamplerCNC():
    ...
class AutosamplerPump(SyringePump):
    ...
class AutosamplerSyringeValve(FourPortDistributionValve):
    """
    Control a Knauer Autosampler 4-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """
        Initialize the FourPortDistributionValve component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerValve): The hardware device instance for controlling the Knauer valve.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            int: The mapped position.
        """
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        """
        Get the current valve position.

        Returns:
            str: The current position.
        """
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position.

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.set_raw_position(position)
class AutosamplerInjectionValve(SixPortTwoPositionValve):
    ...