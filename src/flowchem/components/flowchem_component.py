from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from fastapi import APIRouter
from pydantic import BaseModel

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice

from flowchem.devices.flowchem_device import DeviceInfo


class ComponentInfo(BaseModel):
    """Metadata associated with flowchem components."""

    type = ""
    name = ""
    hw_device: DeviceInfo


class FlowchemComponent(ABC):
    def __init__(self, name: str, hw_device: FlowchemDevice):
        """Initialize component."""
        self.name = name
        self.hw_device = hw_device
        self.router = APIRouter(prefix=f"/{name}", tags=[hw_device.name, name])
        self.router.add_api_route(
            "/",
            self.get_metadata,
            methods=["GET"],
            response_model=ComponentInfo,
        )
        self.metadata = ComponentInfo(
            hw_device=self.hw_device.get_metadata(), name=name
        )

    def get_metadata(self) -> ComponentInfo:
        """Return metadata."""
        return self.metadata
