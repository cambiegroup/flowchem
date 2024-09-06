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

from flowchem.utils.exceptions import DeviceError
try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS.knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False

class AutosamplerCNC(CNC):
    """
    Control a Knauer CNC component .

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the Knauer CNC component.
    """

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        """Initialize component."""
        super().__init__(name, hw_device)
        self.add_api_route("/needle_position", self.needle_position, methods=["PUT"])


    async def needle_position(self, position: str = "",
                              plate: str = None,
                              column: int = None,
                              row: int = None) -> None:
        """
        Move the needle to one of the predefined positions. If Position is "PLATE" a plate,
        row and column have to be specified.

        Argument:
            position (str):
                        WASH
                        WASTE
                        EXCHANGE
                        TRANSPORT
            if position = PLATE:
            plate (str):
                        NO_PLATE = 0
                        LEFT_PLATE = 1
                        RIGHT_PLATE = 2
                        SINGLE_PLATE = 3

            column (int): starting from 1.
            row (int) starting from 1.
        """
        if position != "PLATE":
            await self.hw_device._move_needle_horizontal(needle_position=position, plate=None, well=None)
        else:
            traytype = self.hw_device.tray_type.upper()
            if traytype in PlateTypes.__dict__.keys():
                try:
                    if PlateTypes[traytype] == PlateTypes.SINGLE_TRAY_87:
                        raise NotImplementedError
                except KeyError as e:
                    raise Exception(
                        f"Please provide one of following plate types: {[i.name for i in PlateTypes]}") from e
                # now check if that works for selected tray:
                assert PlateTypes[traytype].value[0] >= column and PlateTypes[traytype].value[1] >= row
                self.hw_device._move_tray(plate, row)
                self.hw_device._move_needle_horizontal(NeedleHorizontalPosition.PLATE.name, plate=plate, well=column)
            elif traytype in NeedleHorizontalPosition.__dict__.keys():
                self.hw_device._move_needle_horizontal(NeedleHorizontalPosition[traytype].name)
            else:
                raise NotImplementedError

    async def set_z_position(self, direction: str = "") -> None:
        """
        Move the CNC device along the Z axis.

        Argument:
            direction (str):
            DOWN
            UP
        """
        await self.hw_device._move_needle_vertical(move_to=direction)


    async def get_position(self) -> tuple:
        """
        Get the current position of the CNC device.
        A tuple (x, y, z) representing the current position.
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
        parsed_rate = ureg.Quantity(rate)
        parsed_volume = ureg.Quantity(volume)

        await self.hw_device.dispense(volume=parsed_volume.m_as("mL"), flow_rate=parsed_rate.m_as("mL/min"))

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

        parsed_rate = ureg.Quantity(rate)
        parsed_volume = ureg.Quantity(volume)
        await self.hw_device.aspirate(volume=parsed_volume.m_as("mL"), flow_rate=parsed_rate.m_as("mL/min"))

class AutosamplerSyringeValve(FourPortDistributionValve):
    """
    Control a Knauer Autosampler 4-Port Distribution syringe Valve.

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the 4-Port Distribution syringe Valve.
    """

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)

        self.add_api_route("/syringe_valve_position", self.get_syringe_valve_position, methods=["GET"])
        self.add_api_route("/syringe_valve_position", self.set_syringe_valve_position, methods=["PUT"])

    async def get_syringe_valve_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str): The current position:
            WASH
            NEEDLE
            WASTE
            WASH_PORT2.
        """
        await self.hw_device.syringe_valve_position(port=None)

    async def set_syringe_valve_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position:
            WASH
            NEEDLE
            WASTE
            WASH_PORT2.
        """
        await self.hw_device.syringe_valve_position(port=position)

class AutosamplerInjectionValve(SixPortTwoPositionValve):
    """
    Control a Knauer Autosampler 6-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """
    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)

        self.add_api_route("/injection_valve_position", self.get_injection_valve_position, methods=["GET"])
        self.add_api_route("/injection_valve_position", self.set_injection_valve_position, methods=["PUT"])

    async def get_injection_valve_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str): The current position:

        """
        await self.hw_device.injector_valve_position(port=None)

    async def set_injection_valve_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            port (str): The desired position:
            LOAD
            INJECT
        """
        await self.hw_device.injector_valve_position(port=position)