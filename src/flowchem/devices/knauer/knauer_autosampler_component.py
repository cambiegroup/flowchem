from __future__ import annotations
from flowchem import ureg
from typing import TYPE_CHECKING
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .knauer_autosampler import KnauerAutosampler

from flowchem.components.cnc.cnc import CNC
from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.valves.distribution_valves import FourPortDistributionValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve
if TYPE_CHECKING:
    from .knauer_valve import KnauerValve
class AutosamplerCNC(CNC):
    """
    Control a Knauer CNC component .

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the Knauer CNC component.
    """

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device) -> None:
        """Initialize component."""
        super().__init__(name, hw_device)

        async def move_to(self, x: float, y: float, z: float) -> None:
            """
            Move the CNC device to the specified (x, y, z) coordinates.
            """
            ...

        async def move_x(self, distance: float) -> None:
            """
            Move the CNC device along the X axis
            """
            ...

        async def move_y(self, distance: float) -> None:
            """
            Move the CNC device along the Y axis
            """
            ...

        async def move_z(self, distance: float) -> None:
            """
            Move the CNC device along the Z axis
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
            """
            ...

class AutosamplerPump(SyringePump):
    """
    Control a Knauer Autosampler syringe pump.

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the Knauer Autosampler syringe pump..
    """

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        """Initialize component."""
        super().__init__(name, hw_device)

    async def infuse(self, rate: str = "", volume: str = "") -> bool:  # type: ignore
        """Start infusion."""
        await self.hw_device.dispense(volume = volume, flow_rate = rate)

    async def stop(self):  # type: ignore
        """Stop pumping."""
        ...

    async def is_pumping(self) -> bool:  # type: ignore
        """Is pump running?"""
        ...

    @staticmethod
    def is_withdrawing_capable() -> bool:  # type: ignore
        """Can the pump reverse its normal flow direction?"""
        return True

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:  # type: ignore
        """Pump in the opposite direction of infuse."""
        await self.hw_device.aspirate(volume=volume, flow_rate=rate)

class AutosamplerSyringeValve(FourPortDistributionValve):
    """
    Control a Knauer Autosampler 4-Port Distribution syringe Valve.

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the 4-Port Distribution syringe Valve.
    """

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """Initialize component."""
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])


    async def get_monitor_position(self) -> str:
        """Get the current valve position."""
        ...

    async def set_monitor_position(self, position: str):
        """Set the valve to a specified position."""
        await self.hw_device.syringe_valve_position(self, port = position)

class AutosamplerInjectionValve(SixPortTwoPositionValve):
    """
    Control a Knauer Autosampler 6-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """
    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """
        Initialize the Knauer6PortDistributionValve component.

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