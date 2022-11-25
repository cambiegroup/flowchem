"""Pressure control"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.base_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class PressureControl(FlowchemComponent):
    """A generic pressure controller."""

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/pressure", self.set_pressure, methods=["PUT"])
        self.add_api_route("/pressure", self.get_pressure, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

        self.add_api_route("/target-reached", self.is_target_reached, methods=["GET"])

    async def set_pressure(self, pressure: str) -> pint.Quantity:
        """Set the target temperature to the given string in natural language."""
        # Add units (mbar) if none
        try:
            float(pressure)
        except ValueError:
            pass
        else:
            logger.warning("No units provided to set_pressure, assuming mbar.")
            pressure = pressure + "mbar"
        return ureg.Quantity(pressure)

    async def get_pressure(self) -> float:  # type: ignore
        """Return pressure in mbar."""
        ...

    async def is_target_reached(self) -> bool:  # type: ignore
        """Return True if the set temperature target has been reached."""
        ...

    async def power_on(self):
        """Turn on pressure control."""
        ...

    async def power_off(self):
        """Turn off pressure control."""
        ...
