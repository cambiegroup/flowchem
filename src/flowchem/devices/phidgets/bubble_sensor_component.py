from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .bublle_sensor import PhidgetBubbleSensor
from flowchem.components.sensors.base_sensor import Sensor


class PhidgetPressureSensorComponent(Sensor):
    hw_device: PhidgetBubbleSensor  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)

    async def read_intensity(self) -> float:
        """Read from sensor, result to be expressed in percentage(%)"""
        return self.hw_device.read_intensity()
