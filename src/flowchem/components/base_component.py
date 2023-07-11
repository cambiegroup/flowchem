from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import APIRouter
from loguru import logger

from flowchem.components.component_info import ComponentInfo

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class FlowchemComponent:
    def __init__(self, name: str, hw_device: FlowchemDevice):
        """Initialize component."""
        self.name = name
        self.hw_device = hw_device
        self.metadata = ComponentInfo(parent_device=self.hw_device.name, name=name)

        # Initialize router
        self._router = APIRouter(
            prefix=f"/{hw_device.name}/{name}", tags=[hw_device.name]
        )
        self.add_api_route(
            "/",
            self.get_metadata,
            methods=["GET"],
            response_model=ComponentInfo,
        )

    @property
    def router(self):
        """Return the API Router. Serves as hook for subclass to add routes."""
        return self._router

    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        """Hook for subclasses to add routes to router."""
        logger.debug(f"Adding route {path} for router of {self.name}")
        self._router.add_api_route(path, endpoint, **kwargs)

    def get_metadata(self) -> ComponentInfo:
        """Return metadata."""
        return self.metadata
