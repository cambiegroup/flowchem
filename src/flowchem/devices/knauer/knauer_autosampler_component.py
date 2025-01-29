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
        "tray_config": {
            "rows": [1, 2, 3, 4, 5, 6, 7, 8],
            "columns": ["a", "b", "c", "d", "e", "f"]
        },
        "needle_positions": ["WASH", "WASTE", "EXCHANGE", "TRANSPORT"],
        "syringe_valve": {"mapping": {0: "NEEDLE", 1: "WASH", 2: "WASH_PORT2", 3: "WASTE"},
        }
    }

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        """Initialize component."""
        super().__init__(name, hw_device, self._config)
        self.add_api_route("/reset_errors", self.reset_errors, methods=["PUT"])

    async def set_needle_position(self, position: str = "") -> bool:
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
        await self.set_z_position("UP")
        await self.hw_device._move_needle_horizontal(needle_position=position)
        logger.info(f"Needle moved succesfully to position: {position}")
        return True

    async def connect_to_position(self, tray: str = "", row: int = None, column: str = None) -> bool:
        """
        Move the 3D gantry to the specified (x, y) coordinate of a specific plate and connects to it.

        plate (str):
                    LEFT_PLATE
                    RIGHT_PLATE

        column: ["a", "b", "c", "d", "e", "f"].
        row: [1, 2, 3, 4, 5, 6, 7, 8]
        """
        await self.set_z_position("UP")
        await self.set_xy_position(tray=tray,row=row,column=column)
        await self.set_z_position("DOWN")
        logger.info(f"Needle connected successfully to row: {row}, column: {column} on tray: {tray}")
        return True

    async def set_xy_position(self, tray: str = "", row: int = None, column: str = None) -> bool:
        """
        Move the 3D gantry to the specified (x, y) coordinate of a specific plate.

        plate (str):
                    LEFT_PLATE
                    RIGHT_PLATE

        column: ["a", "b", "c", "d", "e", "f"].
        row: [1, 2, 3, 4, 5, 6, 7, 8]
        """

        await super().set_xy_position(x=row,y=column)
        column_num = ord(column.upper()) - 64 # change column to int

        if await self.is_needle_running():
            logger.warning("Needle already moving!")

        #traytype = self.hw_device.tray_type.upper()
        await self.hw_device._move_needle_vertical("UP")
        await self.hw_device._move_tray(plate, row)
        success = await self.hw_device._move_needle_horizontal("PLATE", plate=plate, well=column)
        await self.hw_device._move_tray(tray, row)
        success = await self.hw_device._move_needle_horizontal("PLATE", plate=tray, well=column_num)
        if success:
            logger.info(f"Needle moved successfully to row: {row}, column: {column} on tray: {tray}")
            return True

    async def is_needle_running(self) -> bool:
        """"Checks if Autosampler is running"""
        if await self.hw_device.get_status() == "NEEDLE_RUNNING":
            return True
        else:
            return False

    async def set_z_position(self, direction: str = "") -> bool:
        """
        Move the 3D gantry along the Z axis.

        direction (str):
            DOWN
            UP
        """
        await super().set_z_position(z=direction)
        if await self.is_needle_running():
            logger.warning("Needle already moving!")
        success = await self.hw_device._move_needle_vertical(move_to=direction)
        if success:
            logger.info(f"Needle moved successfully to {direction} direction.")
            return True

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

    async def is_pumping(self) -> bool:
        """"Checks if Syringe or syringe valve is running"""
        if self.hw_device.get_status() == "SYRINGE_OR_SYRINGE_VALVE_RUNNING":
            return True
        else:
            return False

    async def reset_errors(self) -> bool:
        """Resets AS erors"""
        errors = await self.hw_device.get_errors()
        if errors:
            logger.info(f"Error: {errors} was present")
            await self.hw_device.reset_errors()
            logger.info(f"Errors reset")
            return True
