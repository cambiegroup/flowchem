from __future__ import annotations
from flowchem import ureg
from typing import TYPE_CHECKING
from enum import Enum
from typing import TYPE_CHECKING
from loguru import logger


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
        self.add_api_route("/set_needle_position", self.set_needle_position, methods=["PUT"])


    async def set_needle_position(self, position: str = "") -> None:
        """
        Move the needle to one of the predefined positions. If Position is "PLATE" a plate,
        row and column have to be specified.

        Argument:
            position (str):
                        WASH
                        WASTE
                        EXCHANGE
                        TRANSPORT
        """
        if position != "PLATE":
            await self.hw_device._move_needle_vertical(NeedleVerticalPositions.UP.name)
            await self.hw_device._move_needle_horizontal(needle_position=position)
        else:
            raise NotImplementedError

    async def set_xy_position(self, plate: str = "", row: int = 0, column: int = 0) -> None:
        """
        Move the 3D gantry to the specified (x, y) coordinate of a specific plate.

        plate (str):
                    NO_PLATE
                    LEFT_PLATE
                    RIGHT_PLATE
                    SINGLE_PLATE 

        column (int): starting from 1.
        row (int) starting from 1.
        """
        if await self.hw_device.get_status() == "NEEDLE_RUNNING":
            logger.warning("Needle already moving!")

        traytype = self.hw_device.tray_type.upper()
        await self.hw_device._move_needle_vertical(NeedleVerticalPositions.UP.name)
        if traytype in PlateTypes.__dict__.keys():
            try:
                if PlateTypes[traytype] == PlateTypes.SINGLE_TRAY_87:
                    raise NotImplementedError
            except KeyError as e:
                raise Exception(
                    f"Please provide one of following plate types: {[i.name for i in PlateTypes]}") from e
            # now check if that works for selected tray:
            assert PlateTypes[traytype].value[0] >= column and PlateTypes[traytype].value[1] >= row
            await self.hw_device._move_tray(plate, row)
            success = await self.hw_device._move_needle_horizontal(NeedleHorizontalPosition.PLATE.name, plate=plate, well=column)
            if success:
                logger.info("Needle moved successfully to row: {row}, column: {column} on plate: {plate}")
            return
        else:
            raise NotImplementedError


    async def set_z_position(self, direction: str = "") -> None:
        """
        Move the 3D gantry along the Z axis.

        Argument:
            direction (str):
            DOWN
            UP
        """
        if await self.hw_device.get_status() == "NEEDLE_RUNNING":
            logger.warning("Needle already moving!")

        success = await self.hw_device._move_needle_vertical(move_to=direction)
        if success:
            logger.info("Needle moved successfully to {direction} direction.")


    async def get_position(self) -> tuple:
        """
        Get the current position of the 3D gantry.
        If needle is above the plates:
            Returns a tuple (row, column, UP/DOWN).
        Else:
            Returns a string representing one of the predefined positions:
            position (str):
                        WASH
                        WASTE
                        EXCHANGE
                        TRANSPORT
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

    async def infuse(self, rate: str = None, volume: str = None) -> bool:  # type: ignore
        """
        Dispense with built in syringe.
        Args:
            volume: volume to dispense in mL

        Returns: None
        """
        if volume is None:
            volume = "0 mL"
            logger.warning(f"the volume to infuse is not provided. set to 0 ml")
        parsed_volume = ureg.Quantity(volume)
        success = await self.hw_device.dispense(volume=parsed_volume.m_as("mL"))
        if success:
            logger.info(f"Syringe pump successfully infused {volume} ml")

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

    async def get_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str): The current position:
            WASH
            NEEDLE
            WASTE
            WASH_PORT2.
        """
        position = await self.hw_device.syringe_valve_position(port=None)
        if position:
            logger.info(f"Syringe valve is in position: {position}")
        return position

    async def set_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position:
            WASH
            NEEDLE
            WASTE
            WASH_PORT2.
        """
        success = await self.hw_device.syringe_valve_position(port=position)
        if success:
            logger.info(f"Syringe valve moved successfully to position: {position}")

class AutosamplerInjectionValve(SixPortTwoPositionValve):
    """
    Control a Knauer Autosampler 6-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """
    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)

    async def get_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str):
                LOAD
                INJECT
        """
        position = await self.hw_device.injector_valve_position(port=None)
        if position:
            logger.info(f"Injection valve is in position: {position}")
        return position

    async def set_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str):
            LOAD
            INJECT
        """
        success = await self.hw_device.injector_valve_position(port=position)
        if success:
            logger.info(f"Injection valve moved successfully to position: {position}")