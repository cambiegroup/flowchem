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
        Move the needle to one of the predefined positions.

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


    #ToDo
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

    async def withdraw(self, rate: str = None, volume: str = None) -> bool:  # type: ignore
        """
        Aspirate with built in syringe.
        Args:
            volume: volume to aspirate in mL

        Returns: None
        """
        if volume is None:
            volume = self.hw_device.syringe_volume
            logger.warning(f"the volume to withdraw is not provided. set to {self.hw_device.syringe_volume}")
        parsed_volume = ureg.Quantity(volume)
        success = await self.hw_device.aspirate(volume=parsed_volume.m_as("mL"))
        if success:
            logger.info(f"Syringe pump successfully withdrew {volume} ml")

    #ToDo
    async def stop(self):  # type: ignore
        """Stop pumping."""
        ...

    # ToDo
    async def is_pumping(self) -> bool:  # type: ignore
        """Is pump running?"""
        ...

    @staticmethod
    def is_withdrawing_capable() -> bool:  # type: ignore
        """Can the pump reverse its normal flow direction?"""
        return True


class AutosamplerSyringeValve(FourPortDistributionValve):
    """
    Control a Knauer Autosampler 4-Port Distribution syringe Valve.

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the 4-Port Distribution syringe Valve.
    """

    hw_device: KnauerAutosampler  # for typing's sake
    identifier = "syringe_valve"

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            int: The mapped position.
        """
        position_mapping = {0: "NEEDLE", 1: "WASH", 2: "WASH_PORT2", 3: "WASTE"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            return position_mapping[raw_position]

    async def get_monitor_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str): The current position:
            NEEDLE (position 0).
            WASH (position 1).
            WASH_PORT2 (position 2).
            WASTE (position 3).
        """
        position = await self.hw_device.syringe_valve_position(port=None)
        if position:
            logger.info(f"Syringe valve is in position: {position}")
        return position

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position:
            NEEDLE (position 0).
            WASH (position 1).
            WASH_PORT2 (position 2).
            WASTE (position 3).
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
    identifier = "injection_valve"

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (str | int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            str | int: The mapped position.
        """
        position_mapping = {0: "LOAD", 1: "INJECT"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            return position_mapping[raw_position]

    async def get_monitor_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str):
                LOAD (position 0)
                INJECT (position 1)
        """
        position = await self.hw_device.injector_valve_position(port=None)
        if position:
            logger.info(f"Injection valve is in position: {position}")
        return position

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str):
            LOAD (position 0)
            INJECT (position 1)
        """
        try:
            success = await self.hw_device.injector_valve_position(port=position)
            if success:
                logger.info(f"Injection valve moved successfully to position: {position}")
        except KeyError as e:
            raise Exception(f"Please give allowed positions {[pos.name for pos in InjectorValvePositions]}") from e