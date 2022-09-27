""" Represent a generic injection valve. """
from abc import ABC
from asyncio import sleep

from fastapi import APIRouter

from .base_valve import BaseValve
from flowchem.units import flowchem_ureg


class InjectionValve(BaseValve, ABC):
    """An abstract class for devices of type injection valve."""

    def __init__(self, loop_volume: str, default_position="LOAD", name=None):
        """

        Args:
            loop_volume: string with volume and units of the injection loop, e.g. "10 ul"
            default_position: the position to be set upon initialization.
            name (str): device name, passed to BaseDevice.
        """

        self.loop_volume = flowchem_ureg(loop_volume)

        # Default position is set upon initialization
        self._default_position = "LOAD"
        super().__init__(
            positions=("LOAD", "INJECT"), default_position=default_position, name=name
        )

    async def _toggle_position(self) -> None:
        """Toggle position."""
        current_position = await self.get_position()
        if current_position == "LOAD":
            await self.set_position("INJECT")
        else:
            await self.set_position("LOAD")

    async def timed_toggle(self, injection_time: str) -> None:
        """
        Switch the valve to the specified position for the specified time.

        Args:
            injection_time: time to switch to the specified position (string with units).
        """
        time_to_wait = flowchem_ureg(injection_time)
        initial_position = await self.get_position()

        await self._toggle_position()
        await sleep(time_to_wait.to("s").magnitude)
        await self.set_position(initial_position)

    def get_router(self, prefix: str | None = None) -> APIRouter:
        router = super().get_router()
        router.add_api_route("/timed_toggle", self.timed_toggle, methods=["PUT"])
        return router
