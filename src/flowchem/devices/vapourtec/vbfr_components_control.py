from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.technical.pressure import PressureControl
from flowchem.components.sensors.body_position_seneor import BodySensor

if TYPE_CHECKING:
    from .vbfr_compression_controller import VBFRController


class VbfrPressureControl(PressureControl):
    hw_device: VBFRController

    def __init__(self, name: str, hw_device: VBFRController) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/deadband", self.set_deadband, methods=["PUT"])
        self.add_api_route("/deadband", self.get_deadband, methods=["GET"])

    async def set_pressure(self, pressure: str) -> bool:
        """Set pressure differnence (in bar)"""
        # fixme: add pint
        await self.hw_device.set_pressure_difference(pressure)
        return True

    async def get_pressure(self) -> float:
        """Get current pressure difference (in mbar)"""
        return await self.hw_device.get_target_pressure_difference()

    # async def get_target_pressure(self) -> float:
        # return await self.hw_device.get_target_pressure_difference()

    async def set_deadband(self, up: int = None, down: int = None) -> bool:
        """Set up & down acceptable offset (in mbar) from required pressure difference."""
        await self.hw_device.set_deadband(up, down)
        return True

    async def get_deadband(self):
        """Get set pressure deadband (in mbar)"""
        return await self.hw_device.get_deadband()


class VbfrBodySensor(BodySensor):
    hw_device: VBFRController

    def __init__(self, name: str, hw_device: VBFRController) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/position", self.get_position, methods=["GET"])
        self.add_api_route("/position_limits", self.get_position_limit, methods=["GET"])
        self.add_api_route("/position_limits", self.set_position_limit, methods=["POST"])
        self.add_api_route("/calibration", self.calibration, methods=["POST"])

    async def get_position(self) -> float:
        """Read body position ((in mm)."""
        return await self.hw_device.get_position()

    async def get_position_limit(self):
        """Get working range (in mm)"""
        return await self.hw_device.get_position_limit()

    async def set_position_limit(self, upper: float = None, lower: float = None) -> bool:
        """set working range (in mm)"""
        await self.hw_device.set_position_limit(upper, lower)
        return True

    async def calibration(self) -> bool:
        """Set current position to zero"""
        return await self.hw_device.calibrate_position()