""" For each device node described in the configuration [graph] instantiated it and create endpoints """
import inspect
import warnings

from loguru import logger
from fastapi import APIRouter

from flowchem.components.properties import ActiveComponent
from flowchem import Spinsolve
from flowchem.core.server.routers import spinsolve_get_router


class DeviceNode:
    """Represent a node in the device graph, holds the HW object and its metadata/config."""

    # Router generators for device class that do not implement self.get_router()
    # All callable take the device obj and return an APIRouter
    router_generator = {Spinsolve: spinsolve_get_router}

    def __init__(self, device_config, obj_type):
        self._router = None

        # No configuration for t-mixer et al.
        if device_config is None:
            device_config = {}

        # Ensure the name is set
        if "name" not in device_config:
            warnings.warn("Device name not set, using class name")
            device_config["name"] = obj_type.__name__

        # DEVICE INSTANTIATION
        try:
            # Special class method for initialization required for some devices
            if hasattr(obj_type, "from_config"):
                self.device = obj_type.from_config(**device_config)
            else:
                self.device = obj_type(**device_config)
            logger.debug(f"Created {self.device.name} instance: {self.device}")
        except TypeError as e:
            raise ConnectionError(
                f"Wrong configuration provided for device: {device_config.get('name')} of type {obj_type}!\n"
                f"Configuration: {device_config}\n"
                f"Accepted parameters: {inspect.getfullargspec(obj_type).args}"
            ) from e

    @property
    def router(self):
        """Returns an APIRouter associated with the device"""
        if self._router:
            return self._router

        if hasattr(self.device, "get_router"):
            router = self.device.get_router()
        else:
            try:
                router = DeviceNode.router_generator[type(self.device)](self.device)
            except KeyError:
                # Only warn no router for active components
                if isinstance(self.device, ActiveComponent):
                    logger.warning(
                        f"No router available for device '{self.device.name}'"
                        f"[Class: {type(self.device).__name__}]"
                    )
                router = APIRouter()

        """ Router name is lowercase with no whitespace """
        router_name = self.device.name.replace(" ", "").lower()

        router.prefix = f"/{router_name}"
        router.tags = [router_name]
        self._router = router
        return self._router
