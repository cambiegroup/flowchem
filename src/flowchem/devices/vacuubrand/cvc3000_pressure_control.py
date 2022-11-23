"""Huber TemperatureControl component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.pressure_control import PressureControl
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from flowchem.devices.vacuubrand.cvc3000 import CVC3000, PumpState, ProcessStatus


class CVC3000PressureControl(PressureControl):
    hw_device: CVC3000  # for typing's sake

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device)

        self.add_api_route(
            "/status",
            self.hw_device.status,
            response_model=ProcessStatus,
            methods=["PUT"],
        )

    async def set_pressure(self, pressure: str):
        """Set the target pressure to the given string in natural language."""
        set_p = await super().set_pressure(pressure)
        return await self.hw_device.set_pressure(set_p)

    async def get_pressure(self) -> float:
        """Return pressure in mbar."""
        return await self.hw_device.get_pressure()

    async def is_target_reached(self) -> bool:
        """Return True if the set temperature target has been reached."""
        status = await self.hw_device.status()
        return status.state == PumpState.VACUUM_REACHED

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device._send_command_and_read_reply("START")

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device._send_command_and_read_reply("STOP")
