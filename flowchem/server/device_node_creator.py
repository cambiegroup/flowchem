import inspect
import logging

from flowchem import Spinsolve, HuberChiller
from flowchem.server.routers import *

"""
 NOTE:
 - parse config
 - create obj instance
 - inject into router creator
 - make zeroconf
"""


class DeviceNode:
    """ Represent a node in the device graph, holds the HW object and its metadata/config. """

    # Router generators for device class that do not implement self.get_router()
    # All callable take the device obj and return an APIRouter
    router_generator = {
        Spinsolve: spinsolve_get_router,
    }

    def __init__(self, device_name, device_config, obj_type):
        self.logger = logging.getLogger(__name__)
        self._title = device_name

        # DEVICE INSTANTIATION
        try:
            # Special classmethod for initialization required for some devices
            if hasattr(obj_type, "from_config"):
                self.device = obj_type.from_config(device_config["parameters"])
            else:
                self.device = obj_type(**device_config["parameters"])
            self.logger.debug(f"Created {self.title} instance: {self.device}")
        except TypeError as e:
            raise ConnectionError(f"Wrong configuration provided for device: {self.title}!\n"
                                  f"Configuration: {device_config['parameters']}\n"
                                  f"Accepted parameters: {inspect.getfullargspec(obj_type).args}") from e

        # ROUTER CREATION
        if hasattr(obj_type, "get_router"):
            self.router = self.device.get_router()
        else:
            self.router = DeviceNode.router_generator[obj_type](self.device)
        # Config router
        self.router.prefix = f"/{self.safe_title}"
        self.router.tags = self.safe_title

        self.service_info = None  # TODO: populate

    # @property
    # def description(self) -> str:
    #     """ Human-readable description of the Node """
    #     return self._description
    #
    # @description.setter
    # def description(self, description: str):
    #     """
    #     Human-readable description of the Node
    #     :param description: str:
    #     """
    #     self._description = description

    @property
    def title(self) -> str:
        """ Human-readable title of the Node """
        return self._title

    @title.setter
    def title(self, title: str):
        """
        Human-readable title of the Node
        :param title: str:
        """
        self._title = title

    @property
    def safe_title(self) -> str:
        """ Lowercase title with no whitespace """
        title = self.title
        if not title:
            title = "unknown"
        title = title.replace(" ", "")
        title = title.lower()
        return title
