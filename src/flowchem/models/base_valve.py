"""Represent a generic valve."""
from __future__ import annotations

from abc import abstractmethod

from fastapi import APIRouter

from .base_device import BaseDevice


class BaseValve(BaseDevice):
    """A generic valve."""

    def __init__(self, **kwargs):
        """BaseValve constructor, sets positions as an empty set."""
        super().__init__(**kwargs)
        self.positions = set()

    @classmethod
    @property
    @abstractmethod
    def _DEFAULT_POSITION(cls):
        raise NotImplementedError

    async def initialize(self):
        """Initialize valve."""
        assert len(self.positions) > 0, "Valve must have at least one position!"
        await self.set_position(self._DEFAULT_POSITION)

    async def set_position(self, position: str) -> None:
        """Set the valve to the specified position."""
        raise NotImplementedError("This should be overridden by the subclass")

    async def get_position(self) -> str:
        """Get the current position of the valve."""
        raise NotImplementedError("This should be overridden by the subclass")

    def position_names(self) -> list[str]:
        """
        Get the list of available positions for this valve.

        Returns: list of strings
        """
        return list(self.positions)

    def get_router(self) -> APIRouter:
        """Get the API router for this device."""
        router = super().get_router()
        router.add_api_route("/position", self.get_position, methods=["GET"])
        router.add_api_route("/position", self.set_position, methods=["PUT"])
        router.add_api_route("/position_names", self.position_names, methods=["GET"])
        return router
