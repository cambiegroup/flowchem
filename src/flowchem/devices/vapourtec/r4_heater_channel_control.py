""" Control module for the Vapourtec R4 heater """
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.temperature import TemperatureControl
from flowchem.components.technical.temperature import TempRange

if TYPE_CHECKING:
    from .r4_heater import R4Heater


class R4HeaterChannelControl(TemperatureControl):
    """R4 reactor heater channel control class."""

    hw_device: R4Heater  # for typing's sake

    def __init__(
        self, name: str, hw_device: R4Heater, channel: int, temp_limits: TempRange
    ):
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device, temp_limits)
        self.channel = channel

    async def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        set_t = await super().set_temperature(temp)
        return await self.hw_device.set_temperature(self.channel, set_t)

    async def get_temperature(self) -> float:  # type: ignore
        """Return temperature in Celsius."""
        return float(await self.hw_device.get_temperature(self.channel))

    async def is_target_reached(self) -> bool:  # type: ignore
        """Return True if the set temperature target has been reached."""
        status = await self.hw_device.get_status(self.channel)
        return status.state == "S"

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device.power_on(self.channel)

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device.power_off(self.channel)
