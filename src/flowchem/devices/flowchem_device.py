"""Base object for all hardware-control device classes."""
from abc import ABC
from collections import namedtuple
from collections.abc import Iterable
from typing import TYPE_CHECKING

from flowchem.components.device_info import DeviceInfo

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
        self.device_info = DeviceInfo()

    async def initialize(self):
        """Use for setting up async connection to the device."""
        pass

    def repeated_task(self) -> RepeatedTaskInfo | None:
        """Use for repeated background task, e.g. session keepalive."""
        return None

    def get_device_info(self) -> DeviceInfo:
        return self.device_info

    def components(self) -> Iterable["FlowchemComponent"]:
        return ()
