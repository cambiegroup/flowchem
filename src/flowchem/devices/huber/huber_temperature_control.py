"""Huber TemperatureControl component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chiller import HuberChiller


from flowchem.components.technical.temperature import TemperatureControl


class HuberTemperatureControl(TemperatureControl):
    hw_device: HuberChiller  # for typing's sake

    async def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        set_t = await super().set_temperature(temp)
        return await self.hw_device.set_temperature(set_t)

    async def get_temperature(self) -> float:
        """Return temperature in Celsius."""
        return await self.hw_device.get_temperature()

    async def is_target_reached(self) -> bool:
        """Return True if the set temperature target has been reached."""
        return await self.hw_device.target_reached()

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device._send_command_and_read_reply("{M140001")

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device._send_command_and_read_reply("{M140000")
