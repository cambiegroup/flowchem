"""Represent a generic valve."""
from __future__ import annotations

from abc import ABC

from fastapi import APIRouter
from loguru import logger

from ..base_device import BaseDevice


class BaseValve(BaseDevice, ABC):
    """An abstract class for devices of type valve.

    .. warning::
        Device objects should not directly subclass this object but rather a more specific valve type,
        such as `InjectionValve` or `MultiPositionValve`.

    All valves are characterized by:

    - a `positions` attribute, which is a set of strings representing the valve positions.
    - a `set_position()` method
    - a `get_position()` method

    """

    def __init__(self, positions, default_position=None, name=None):
        """

        Args:
            positions: list/tuple/set of string representing the valve ports.
            default_position: the position to be set upon initialization.
            name: device name, passed to BaseDevice.
        """
        super().__init__(name=name)
        self.positions = set(positions)

        # Set default position if provided
        if default_position is None:
            self._default_position = None
        else:
            if default_position in self.positions:
                self._default_position = default_position
            else:
                logger.warning(
                    f"The default valve position specified for {__name__} {self.name} is not valid!"
                    f"Default position: {default_position}. Known positions: {self.positions}"
                )

    async def initialize(self):
        """Initialize the valve."""
        assert len(self.positions) > 0, "Valve must have at least one position!"
        await self.set_position(self._default_position)

    async def get_position(self) -> str:
        """Get the current position of the valve."""
        raise NotImplementedError("This should be overridden by the subclass")

    async def set_position(self, position: str) -> None:
        """Set the valve to the specified position."""
        raise NotImplementedError("This should be overridden by the subclass")

    def position_names(self) -> list[str]:
        """
        Get the list of all available positions for this valve.

        These are the human-friendly port names, and they do not necessarily match the port names used in the
        communication with the device. E.g. positions "load" and "inject" could translate to positions "1" and "2".
        """
        return list(self.positions)

    def get_router(self) -> APIRouter:
        """Get the API router for this device."""
        router = super().get_router()
        router.add_api_route("/position", self.get_position, methods=["GET"])
        router.add_api_route("/position", self.set_position, methods=["PUT"])
        router.add_api_route("/position_names", self.position_names, methods=["GET"])
        return router
