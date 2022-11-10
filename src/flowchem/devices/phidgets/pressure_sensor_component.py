from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pressure_sensor import PhidgetPressureSensor
from flowchem.components.sensors.pressure_sensor import PressureSensor


class PhidgetPressureSensorComponent(PressureSensor):
    hw_device: PhidgetPressureSensor  # just for typing

    async def read_pressure(self, units: str = "bar"):
        """Read from sensor, result to be expressed in units (optional)."""
        return self.hw_device.read_pressure().m_as(units)
