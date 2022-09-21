from abc import ABC

from fastapi import APIRouter

from .sensor import Sensor


class PressureSensor(Sensor, ABC):
    """A pressure sensor."""

    def __init__(self, name: str | None = None):
        super().__init__(name=name)

    async def read_pressure(self, units: str | None = "bar"):
        """Read from sensor, result to be expressed in units (optional)."""
        raise NotImplementedError("To be implemented in subclass")

    def get_router(self, prefix: str | None = None) -> APIRouter:
        """Get the API router for this device."""
        router = super().get_router(prefix)
        router.add_api_route("/read-pressure", self.read_pressure, methods=["GET"])
        return router
