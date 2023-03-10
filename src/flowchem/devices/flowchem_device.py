"""Base object for all hardware-control device classes."""
from abc import ABC
from collections import namedtuple
from collections.abc import Iterable
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel

from flowchem import __version__
from flowchem.utils.exceptions import DeviceError

if TYPE_CHECKING:
    from flowchem.components.base_component import FlowchemComponent


class Person(BaseModel):
    name: str
    email: str


class DeviceInfo(BaseModel):
    """Metadata associated with hardware devices."""

    backend = f"flowchem v. {__version__}"
    authors: "list[Person]"
    maintainers: "list[Person]"
    manufacturer: str
    model: str
    serial_number: str | int = "unknown"
    version: str = ""
    additional_info: dict = {}


DeviceInfo.update_forward_refs()


RepeatedTaskInfo = namedtuple("RepeatedTaskInfo", ["seconds_every", "task"])


class FlowchemDevice(ABC):
    """
    Base flowchem device.

    All hardware-control classes must subclass this to signal they are flowchem-device and be enabled for initializaiton
    during config parsing.
    """

    def __init__(self, name):
        """All device have a name, which is the key in the config dict thus unique."""
        self.name = name

    async def initialize(self):
        """Use for setting up async connection to the device."""
        pass

    def repeated_task(self) -> RepeatedTaskInfo | None:
        """Use for repeated background task, e.g. session keepalive."""
        return None

    def get_metadata(self) -> DeviceInfo:
        try:
            return self.metadata  # type: ignore
        except AttributeError as ae:
            logger.error(f"Invalid device type for {self.name}!")
            raise DeviceError(
                f"Invalid device {self.name}!"
                f"The attribute `metadata` is missing, should be a DeviceInfo variable!"
            ) from ae

    def components(self) -> Iterable["FlowchemComponent"]:
        return ()
