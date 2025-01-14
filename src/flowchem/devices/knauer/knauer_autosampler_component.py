from __future__ import annotations
from flowchem import ureg
from typing import TYPE_CHECKING
from loguru import logger


if TYPE_CHECKING:
    from .knauer_autosampler import KnauerAutosampler

from flowchem.components.meta_components.autosampler import Autosampler

try:
    from NDA_knauer_AS.knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False


class KnauerAS(Autosampler):
    """
    Control a Knauer Autosampler component .

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the Knauer CNC component.
    """

    _config = {
        "axes_config": {
            "x": {"mode": "discrete", "positions": [1, 2, 3, 4, 5, 6, 7, 8]},
            "y": {"mode": "discrete", "positions": ["a", "b", "c", "d", "e", "f"]},
            "z": {"mode": "discrete", "positions": ["UP", "DOWN"]}
        },
        "needle_positions": ["WASH", "WASTE", "EXCHANGE", "TRANSPORT"],
        "syringe_valve": {"type": "FourPortDistributionValve", "mapping": {0: "NEEDLE", 1: "WASH", 2: "WASH_PORT2", 3: "WASTE"}},
        "injection_valve": {"type": "SixPortTwoPositionValve",
                          "mapping": {0: "LOAD", 1: "INJECT"}}
    }

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        """Initialize component."""
        super().__init__(name, hw_device, self._config)

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
        await super().set_needle_position(position=position)
        await self.hw_device._move_needle_vertical(NeedleVerticalPositions.UP.name)
        await self.hw_device._move_needle_horizontal(needle_position=position)

    async def set_xy_position(self, plate: str = "", row: int = 0, column: str = "a") -> None:
        """
        Move the 3D gantry to the specified (x, y) coordinate of a specific plate.

        plate (str):
                    LEFT_PLATE
                    RIGHT_PLATE

        column: ["a", "b", "c", "d", "e", "f"].
        row: [1, 2, 3, 4, 5, 6, 7, 8]
        """

        await super().set_xy_position(x=row,y=column)
        column = ord(column.upper()) - 64 #change to int
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

        direction (str):
            DOWN
            UP
        """
        await super().set_z_position(z=direction)
        if await self.hw_device.get_status() == "NEEDLE_RUNNING":
            logger.warning("Needle already moving!")

        success = await self.hw_device._move_needle_vertical(move_to=direction)
        if success:
            logger.info(f"Needle moved successfully to {direction} direction.")

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

    @staticmethod
    def is_withdrawing_capable() -> bool:  # type: ignore
        """Can the pump reverse its normal flow direction?"""
        return True

