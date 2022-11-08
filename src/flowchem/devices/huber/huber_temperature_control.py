"""Huber TemperatureControl component."""
from loguru import logger

from .chiller import HuberChiller
from flowchem import ureg
from flowchem.components.technical.temperature_control import TemperatureControl


class HuberTemperatureControl(TemperatureControl):
    hw_device: HuberChiller  # for typing's sake

    async def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        set_t = ureg(temp)

        if set_t < self._limits[0]:
            set_t = self._limits[0]
            logger.warning(
                f"Temperature requested {set_t} is out of range [{self._limits}] for {self.name}!"
                f"Setting to {self._limits[0]} instead."
            )

        if set_t > self._limits[1]:
            set_t = self._limits[1]
            logger.warning(
                f"Temperature requested {set_t} is out of range [{self._limits}] for {self.name}!"
                f"Setting to {self._limits[1]} instead."
            )

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
