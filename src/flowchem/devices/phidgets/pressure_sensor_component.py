from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .pressure_sensor import PhidgetPressureSensor
from flowchem.components.sensors.pressure import PressureSensor


class PhidgetPressureSensorComponent(PressureSensor):
    hw_device: PhidgetPressureSensor  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """A generic Syringe pump."""
        super().__init__(name, hw_device)

    async def read_pressure(self, units: str = "bar"):
        """Read from sensor, result to be expressed in units (optional)."""
        return self.hw_device.read_pressure().m_as(units)
