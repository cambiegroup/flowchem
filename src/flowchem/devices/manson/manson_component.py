from __future__ import annotations

from flowchem.components.technical.temperature_control import TemperatureControl
from flowchem.devices import MansonPowerSupply


class MansonTemperatureControl(TemperatureControl):
    hw_device: MansonPowerSupply  # for typing's sake

    async def set_current(self, current: str):
        """Set the target current to the given string in natural language."""
        return await self.hw_device.set_current(current)

    async def get_current(self) -> float:
        """Return current in Ampere."""
        return await self.hw_device.get_output_current()

    async def set_voltage(self, voltage: str):
        """Set the target voltage to the given string in natural language."""
        return await self.hw_device.set_voltage(voltage)

    async def get_voltage(self) -> float:
        """Return current in Volt."""
        return await self.hw_device.get_output_voltage()

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device.output_on()

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device.output_off()
