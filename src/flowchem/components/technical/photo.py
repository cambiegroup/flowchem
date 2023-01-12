"""Temperature control, either for heating or cooling."""
from __future__ import annotations

from typing import NamedTuple
from typing import TYPE_CHECKING

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.base_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class TempRange(NamedTuple):
    min: pint.Quantity = ureg.Quantity("-100 °C")
    max: pint.Quantity = ureg.Quantity("+250 °C")


class PhotoControl(FlowchemComponent):
    """A generic temperature controller."""

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/UV", self.set_UV, methods=["PUT"])
        self.add_api_route("/temperature", self.set_temperature, methods=["PUT"])
        self.add_api_route("/temperature", self.get_temperature, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

        self.add_api_route("/temp-reached", self.is_target_reached, methods=["GET"])


    async def set_UV(self, power: str):
        """Set UV light intensity"""
        ...
    async def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        ...

    async def get_temperature(self) -> float:  # type: ignore
        """Return temperature in Celsius."""
        ...

    async def is_target_reached(self) -> bool:  # type: ignore
        """Return True if the set temperature target has been reached."""
        ...

    async def temperature_limits(self) -> TempRange:
        """Return a dict with `min` and `max` temperature in Celsius."""
        return self._limits

    async def power_on(self):
        """Turn on temperature control."""
        ...

    async def power_off(self):
        """Turn off temperature control."""
        ...
