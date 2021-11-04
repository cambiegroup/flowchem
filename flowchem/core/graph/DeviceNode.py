""" For each device node described in the configuration [graph] instantiated it and create endpoints """
import inspect
import logging

from flowchem import Spinsolve
from flowchem.core.server.routers import spinsolve_get_router


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
        self._router = None

        # DEVICE INSTANTIATION
        try:
            # Special class method for initialization required for some devices
            if hasattr(obj_type, "from_config"):
                self.device = obj_type.from_config(device_config)
            else:
                self.device = obj_type(**device_config)
            self.logger.debug(f"Created {self.title} instance: {self.device}")
        except TypeError as e:
            raise ConnectionError(
                f"Wrong configuration provided for device: {self.title}!\n"
                f"Configuration: {device_config}\n"
                f"Accepted parameters: {inspect.getfullargspec(obj_type).args}"
            ) from e

        # self.service_info = None

    @property
    def router(self):
        """ Returns an APIRouter associated with the device """
        if self._router:
            return self._router

        if hasattr(self.device, "get_router"):
            router = self.device.get_router()
        else:
            router = DeviceNode.router_generator[type(self.device)](self.device)

        router.prefix = f"/{self.safe_title}"
        router.tags = self.safe_title
        self._router = router
        return self._router

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