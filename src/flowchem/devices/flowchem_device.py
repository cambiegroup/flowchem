"""Base object for all hardware-control device classes."""
from __future__ import annotations

from abc import ABC
from collections.abc import Iterable
from typing import TYPE_CHECKING

from pydantic import BaseModel

from flowchem import __version__

if TYPE_CHECKING:
    from flowchem.components.base_component import FlowchemComponent


class Person(BaseModel):
    name: str
    email: str


class DeviceInfo(BaseModel):
    """Metadata associated with hardware devices."""

    backend = f"flowchem v. {__version__}"
    authors = list[Person]
    maintainers = list[Person]
    manufacturer: str
    model: str
    serial_number = "unknown"
    version = ""


class FlowchemDevice(ABC):
    """
    Base flowchem device.

    All hardware-control classes must subclass this to signal they are flowchem-device and be enabled for initializaiton
    during config parsing.
    """

    def __init__(self, name=""):
        """Ensure the device name validity."""
        self.name = name

    async def initialize(self):
        pass

    def get_metadata(self) -> DeviceInfo:
        return self.metadata  # type: ignore

    def components(self) -> Iterable[FlowchemComponent]:
        return ()
