"""Base object for all hardware-control device classes."""
from abc import ABC
from collections import namedtuple
from collections.abc import Iterable
from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.utils.exceptions import DeviceError

if TYPE_CHECKING:
    from flowchem.components.base_component import FlowchemComponent

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
